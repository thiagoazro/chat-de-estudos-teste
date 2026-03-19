"""
ingest.py — Pipeline de ingestão: PDF → chunks → embeddings → Qdrant.

Este módulo implementa o "ETL" do RAG:
  Extract:   lê o PDF e extrai texto
  Transform: fatia o texto em chunks com overlap
  Load:      gera embeddings e grava no Qdrant

Conceitos-chave de Engenharia de Dados aqui:
  - Chunking com overlap (janela deslizante) para não perder contexto
  - Batch processing de embeddings (eficiência de API)
  - Upsert idempotente no vector store
"""

import io
import uuid
import hashlib
from typing import Optional
from urllib.parse import urlparse

import httpx
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
)
from pypdf import PdfReader

from config import (
    OPENAI_API_KEY,
    EMBEDDING_MODEL,
    QDRANT_URL,
    QDRANT_API_KEY,
    COLLECTION_NAME,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)

# ── Clientes ────────────────────────────────────────────────────────
openai_client = OpenAI(api_key=OPENAI_API_KEY)

qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)


# ── Funções do pipeline ─────────────────────────────────────────────
def extract_text_from_pdf(file_bytes: bytes) -> str:
    """
    Extrai texto bruto de um PDF.
    Em produção, considere OCR (Tesseract/Amazon Textract) para PDFs escaneados.
    """
    reader = PdfReader(file_bytes)
    pages_text = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        pages_text.append(text)
    return "\n".join(pages_text)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """
    Fatia o texto em pedaços menores com sobreposição (overlap).

    Por que chunk_size=500 e overlap=50?
    - Chunks muito grandes diluem a relevância na busca vetorial.
    - Chunks muito pequenos perdem contexto.
    - O overlap garante que frases na fronteira entre dois chunks
      não sejam "cortadas ao meio" e percam sentido.

    Retorna lista de dicts com 'text' e 'chunk_index'.
    """
    words = text.split()
    chunks = []
    start = 0
    idx = 0

    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        if chunk_text.strip():
            chunks.append({
                "text": chunk_text,
                "chunk_index": idx,
            })
            idx += 1

        start += chunk_size - overlap

    return chunks


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Gera embeddings em batch via OpenAI API.

    text-embedding-3-small:
      - 1536 dimensões
      - ~$0.02 / 1M tokens
      - Performance boa pra retrieval

    Em produção, monitore latência e custo por request.
    """
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


def ensure_collection_exists():
    """
    Cria a collection no Qdrant se não existir.
    Cosine é a métrica padrão para text embeddings — mede
    a similaridade de direção entre vetores, ignorando magnitude.
    """
    collections = [c.name for c in qdrant.get_collections().collections]
    if COLLECTION_NAME not in collections:
        qdrant.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=1536,  # dimensões do text-embedding-3-small
                distance=Distance.COSINE,
            ),
        )
        print(f"✅ Collection '{COLLECTION_NAME}' criada no Qdrant.")
    else:
        print(f"ℹ️  Collection '{COLLECTION_NAME}' já existe.")


def _deterministic_id(text: str) -> str:
    """Gera um UUID determinístico baseado no conteúdo para idempotência."""
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, hashlib.md5(text.encode()).hexdigest()))


def ingest_document(file_bytes, filename: str, source: Optional[str] = None) -> dict:
    """
    Pipeline completo de ingestão:
      1. Garante que a collection existe
      2. Extrai texto do PDF
      3. Fatia em chunks
      4. Gera embeddings
      5. Faz upsert no Qdrant

    Retorna métricas da ingestão.
    """
    ensure_collection_exists()

    # 1. Extract
    raw_text = extract_text_from_pdf(file_bytes)

    if not raw_text.strip():
        return {"status": "error", "detail": "Nenhum texto extraído do PDF."}

    # 2. Transform — chunking
    chunks = chunk_text(raw_text)

    # 3. Transform — embedding
    texts = [c["text"] for c in chunks]
    embeddings = generate_embeddings(texts)

    # 4. Load — upsert no Qdrant
    points = []
    for chunk, embedding in zip(chunks, embeddings):
        point_id = _deterministic_id(chunk["text"])
        points.append(
            PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "text": chunk["text"],
                    "chunk_index": chunk["chunk_index"],
                    "source": source or filename,
                    "filename": filename,
                },
            )
        )

    # Upsert em batches de 100 (boa prática pra não estourar payload)
    batch_size = 100
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        qdrant.upsert(collection_name=COLLECTION_NAME, points=batch)

    return {
        "status": "ok",
        "filename": filename,
        "total_chunks": len(chunks),
        "total_characters": len(raw_text),
        "collection": COLLECTION_NAME,
    }


def ingest_from_url(url: str) -> dict:
    """
    Baixa um PDF de uma URL e ingere no Qdrant.

    Útil para:
      - Ingerir papers direto do arXiv, Google Drive, etc.
      - Alimentar o agente com material público sem download manual
      - Integração com pipelines automatizados (n8n, Airflow)

    Em produção, adicione:
      - Timeout configurável
      - Validação de content-type
      - Limite de tamanho do arquivo
      - Fila assíncrona (Celery/RQ) pra arquivos grandes
    """
    # Extrai nome do arquivo da URL
    parsed = urlparse(url)
    filename = parsed.path.split("/")[-1] or "documento_url.pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    # Baixa o PDF
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        return {"status": "error", "detail": f"Erro HTTP ao baixar: {e.response.status_code}"}
    except httpx.RequestError as e:
        return {"status": "error", "detail": f"Erro de conexão: {str(e)}"}

    # Valida content-type (aceita PDF ou octet-stream)
    content_type = response.headers.get("content-type", "")
    if "pdf" not in content_type and "octet-stream" not in content_type:
        return {
            "status": "error",
            "detail": f"URL não retornou PDF. Content-Type: {content_type}",
        }

    file_bytes = io.BytesIO(response.content)

    return ingest_document(
        file_bytes=file_bytes,
        filename=filename,
        source=url,
    )
