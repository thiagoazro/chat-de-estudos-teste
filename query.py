"""
query.py — Pipeline de consulta: pergunta → retrieval → augmented generation.

Este módulo implementa o "R" e o "G" do RAG:
  Retrieval:  converte a pergunta em embedding, busca no Qdrant os
              chunks mais similares (nearest neighbors)
  Generation: monta um prompt com os chunks recuperados + pergunta
              original e envia ao LLM para gerar a resposta

Conceitos de Engenharia de Dados:
  - Busca por similaridade vetorial (ANN — Approximate Nearest Neighbors)
  - Prompt engineering com contexto injetado
  - Separação de concerns: retrieval ≠ generation
"""

from openai import OpenAI
from qdrant_client import QdrantClient

from config import (
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
    LLM_MODEL,
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
    TOP_K,
)

# ── Clientes ────────────────────────────────────────────────────────
openai_client = OpenAI(api_key=OPENAI_API_KEY)

qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

# ── System prompt do agente de estudos ──────────────────────────────
SYSTEM_PROMPT = """Você é um agente de estudos especializado em Engenharia de Dados e Inteligência Artificial.

Seu papel:
- Responder perguntas com base EXCLUSIVAMENTE nos trechos de documentos fornecidos no contexto.
- Explicar conceitos de forma clara, com exemplos práticos quando possível.
- Se a informação não estiver no contexto, diga explicitamente que não encontrou nos materiais disponíveis.
- Sempre indique de qual fonte/documento veio a informação.
- Use linguagem técnica mas acessível — o público está em transição de carreira.

Formato da resposta:
- Resposta direta e objetiva primeiro
- Depois, se relevante, expanda com exemplos ou analogias
- Cite os trechos-fonte usados ao final

Idioma: Português brasileiro."""


# ── Funções do pipeline ─────────────────────────────────────────────
def embed_query(query: str) -> list[float]:
    """Gera embedding da pergunta do usuário."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=[query],
    )
    return response.data[0].embedding


def retrieve_chunks(query_embedding: list[float], top_k: int = TOP_K) -> list[dict]:
    """
    Busca os top_k chunks mais similares no Qdrant.

    Internamente o Qdrant usa HNSW (Hierarchical Navigable Small World)
    para busca aproximada — O(log n) ao invés de O(n) de busca exaustiva.
    Isso é o que permite escalar pra milhões de vetores.
    """
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=top_k,
    )

    chunks = []
    for hit in results:
        chunks.append({
            "text": hit.payload.get("text", ""),
            "source": hit.payload.get("source", "desconhecido"),
            "score": round(hit.score, 4),
            "chunk_index": hit.payload.get("chunk_index", -1),
        })

    return chunks


def build_augmented_prompt(query: str, chunks: list[dict]) -> str:
    """
    Monta o prompt aumentado com o contexto recuperado.

    A estrutura é:
      [CONTEXTO]      → trechos relevantes dos documentos
      [PERGUNTA]      → pergunta original do usuário
      [INSTRUÇÃO]     → como o LLM deve usar o contexto

    Isso é o coração do RAG — o "Augmented" em
    Retrieval-Augmented Generation.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Trecho {i} | Fonte: {chunk['source']} | Relevância: {chunk['score']}]\n"
            f"{chunk['text']}"
        )

    context_block = "\n\n---\n\n".join(context_parts)

    return f"""Com base nos trechos de documentos abaixo, responda à pergunta do estudante.

═══ CONTEXTO RECUPERADO ═══

{context_block}

═══ PERGUNTA ═══

{query}

═══ INSTRUÇÃO ═══

Responda usando APENAS as informações do contexto acima. Se a resposta não estiver no contexto, diga claramente."""


def generate_answer(augmented_prompt: str) -> str:
    """
    Envia o prompt aumentado ao LLM e retorna a resposta gerada.
    """
    response = openai_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": augmented_prompt},
        ],
        temperature=0.3,  # baixa temperatura = respostas mais fiéis ao contexto
        max_tokens=1500,
    )
    return response.choices[0].message.content


def query_rag(question: str) -> dict:
    """
    Pipeline completo de consulta RAG:
      1. Gera embedding da pergunta
      2. Busca chunks similares no Qdrant
      3. Monta prompt aumentado
      4. Gera resposta com LLM

    Retorna a resposta + chunks usados (para transparência).
    """
    # 1. Embedding da query
    query_embedding = embed_query(question)

    # 2. Retrieval
    chunks = retrieve_chunks(query_embedding)

    if not chunks:
        return {
            "answer": "Não encontrei informações relevantes nos materiais disponíveis. "
                      "Tente reformular a pergunta ou ingira mais documentos.",
            "sources": [],
            "chunks_used": 0,
        }

    # 3. Augmented prompt
    augmented_prompt = build_augmented_prompt(question, chunks)

    # 4. Generation
    answer = generate_answer(augmented_prompt)

    # Fontes únicas para referência
    sources = list(set(c["source"] for c in chunks))

    return {
        "answer": answer,
        "sources": sources,
        "chunks_used": len(chunks),
        "retrieved_chunks": chunks,
    }
