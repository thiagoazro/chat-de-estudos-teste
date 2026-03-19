"""
main.py — API REST do Agente de Estudos em Engenharia de Dados & IA.

FastAPI foi escolhido porque:
  1. Async nativo (performance pra I/O-bound como chamadas a APIs)
  2. Documentação automática via OpenAPI/Swagger (/docs)
  3. Validação automática com Pydantic (type safety)
  4. É o framework padrão de mercado pra ML/AI APIs em Python

Endpoints:
  POST /ingest     → recebe PDF e ingere no Qdrant
  POST /query      → recebe pergunta e retorna resposta do RAG
  GET  /health     → healthcheck (Render usa pra saber se o serviço tá vivo)
  GET  /stats      → métricas da collection no Qdrant
"""

import io
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl

from config import COLLECTION_NAME
from ingest import ingest_document, ingest_from_url, qdrant, ensure_collection_exists
from query import query_rag
from seed import seed_documents


# ── Lifecycle: seed dos docs base ao subir ──────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Roda ao iniciar a aplicação:
      1. Garante que a collection existe no Qdrant
      2. Ingere todos os PDFs da pasta docs/ (idempotente — não duplica)

    Isso é o equivalente a um "backfill" em engenharia de dados:
    popular a base com dados históricos antes de aceitar dados novos.
    """
    ensure_collection_exists()
    seed_documents()  # idempotente: IDs determinísticos evitam duplicatas
    yield


# ── App FastAPI ─────────────────────────────────────────────────────
app = FastAPI(
    title="📚 Study Agent RAG API",
    description=(
        "API de um agente de estudos com RAG (Retrieval-Augmented Generation) "
        "para Engenharia de Dados e IA. Ingere documentos PDF, armazena embeddings "
        "no Qdrant Cloud e responde perguntas com base no conteúdo."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS — necessário para o frontend (Lovable) chamar a API ───────
# Em produção, restrinja 'origins' ao domínio do seu frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restringir ao domínio do Lovable em produção
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schemas Pydantic (validação + documentação automática) ──────────
class QueryRequest(BaseModel):
    """Schema do request de consulta."""
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="Pergunta do estudante sobre Engenharia de Dados ou IA.",
        json_schema_extra={"example": "O que é um pipeline de ETL?"},
    )


class QueryResponse(BaseModel):
    """Schema do response de consulta."""
    answer: str
    sources: list[str]
    chunks_used: int
    retrieved_chunks: list[dict] = []


class IngestResponse(BaseModel):
    """Schema do response de ingestão."""
    status: str
    filename: str = ""
    total_chunks: int = 0
    total_characters: int = 0
    collection: str = ""
    detail: str = ""


class IngestUrlRequest(BaseModel):
    """Schema do request de ingestão por URL."""
    url: str = Field(
        ...,
        description="URL pública de um arquivo PDF para ingestão.",
        json_schema_extra={"example": "https://arxiv.org/pdf/2005.11401v4"},
    )


class HealthResponse(BaseModel):
    """Schema do healthcheck."""
    status: str
    service: str
    qdrant_connected: bool


class StatsResponse(BaseModel):
    """Schema das estatísticas da collection."""
    collection: str
    total_points: int
    status: str


# ── Endpoints ───────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Infraestrutura"])
async def health_check():
    """
    Healthcheck — Render usa este endpoint pra monitorar se a API tá viva.

    Em engenharia de dados, healthchecks são essenciais em qualquer
    serviço distribuído. O orquestrador (Render, K8s, etc.) mata e
    reinicia o container se esse endpoint parar de responder.
    """
    try:
        qdrant.get_collections()
        qdrant_ok = True
    except Exception:
        qdrant_ok = False

    return {
        "status": "healthy" if qdrant_ok else "degraded",
        "service": "study-agent-rag",
        "qdrant_connected": qdrant_ok,
    }


@app.get("/stats", response_model=StatsResponse, tags=["Infraestrutura"])
async def collection_stats():
    """
    Retorna quantidade de vetores armazenados na collection.
    Útil pra saber quantos chunks já foram ingeridos.
    """
    try:
        info = qdrant.get_collection(COLLECTION_NAME)
        return {
            "collection": COLLECTION_NAME,
            "total_points": info.points_count,
            "status": str(info.status),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest", response_model=IngestResponse, tags=["Ingestão"])
async def ingest_pdf(file: UploadFile = File(...)):
    """
    Recebe um PDF, extrai texto, fatia em chunks, gera embeddings
    e armazena no Qdrant.

    Fluxo:
      1. Valida que o arquivo é PDF
      2. Lê bytes do upload
      3. Chama o pipeline de ingestão
      4. Retorna métricas

    Curl de teste:
      curl -X POST http://localhost:8000/ingest -F "file=@documento.pdf"
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Apenas arquivos PDF são aceitos. Envie um arquivo .pdf.",
        )

    contents = await file.read()
    file_like = io.BytesIO(contents)

    try:
        result = ingest_document(
            file_bytes=file_like,
            filename=file.filename,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na ingestão: {str(e)}")

    if result.get("status") == "error":
        raise HTTPException(status_code=422, detail=result.get("detail", "Erro desconhecido"))

    return result


@app.post("/ingest/url", response_model=IngestResponse, tags=["Ingestão"])
async def ingest_from_url_endpoint(request: IngestUrlRequest):
    """
    Recebe uma URL de PDF público, baixa e ingere no Qdrant.

    Use cases:
      - Papers do arXiv: https://arxiv.org/pdf/2005.11401v4
      - PDFs públicos de qualquer servidor
      - Material compartilhado via Google Drive (link público)

    Curl de teste:
      curl -X POST http://localhost:8000/ingest/url \\
        -H "Content-Type: application/json" \\
        -d '{"url": "https://arxiv.org/pdf/2005.11401v4"}'
    """
    try:
        result = ingest_from_url(request.url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na ingestão por URL: {str(e)}")

    if result.get("status") == "error":
        raise HTTPException(status_code=422, detail=result.get("detail", "Erro desconhecido"))

    return result


@app.post("/seed", tags=["Ingestão"])
async def run_seed():
    """
    Re-executa o seed da pasta docs/ manualmente.

    Útil quando você adicionou novos PDFs à pasta docs/ e quer
    ingerir sem reiniciar a aplicação. Idempotente — não duplica.

    Curl de teste:
      curl -X POST http://localhost:8000/seed
    """
    try:
        results = seed_documents()
        ok = sum(1 for r in results if r.get("status") == "ok")
        total_chunks = sum(r.get("total_chunks", 0) for r in results)
        return {
            "status": "ok",
            "files_processed": len(results),
            "files_ok": ok,
            "total_chunks": total_chunks,
            "details": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no seed: {str(e)}")


@app.post("/query", response_model=QueryResponse, tags=["Consulta RAG"])
async def query_documents(request: QueryRequest):
    """
    Recebe uma pergunta e retorna a resposta gerada pelo RAG.

    Fluxo interno:
      1. Gera embedding da pergunta (mesma dimensão dos chunks)
      2. Busca top-K chunks mais similares no Qdrant (cosine similarity)
      3. Monta prompt aumentado com contexto + pergunta
      4. Envia ao LLM e retorna resposta + fontes

    Curl de teste:
      curl -X POST http://localhost:8000/query \\
        -H "Content-Type: application/json" \\
        -d '{"question": "O que é um data lake?"}'
    """
    try:
        result = query_rag(request.question)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na consulta: {str(e)}")

    return result


# ── Entrypoint local ────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
