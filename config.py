"""
config.py — Configurações centralizadas via variáveis de ambiente.

Por que separar config do código?
Em engenharia de dados, credenciais e URLs de serviços NUNCA ficam
hardcoded. Usamos variáveis de ambiente para:
  1. Segurança (secrets não vão pro Git)
  2. Flexibilidade (muda entre dev/staging/prod sem alterar código)
  3. 12-Factor App compliance (https://12factor.net/config)
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── OpenAI (embeddings + LLM) ──────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dims, barato e rápido
LLM_MODEL = "gpt-4o-mini"  # bom custo-benefício pra geração

# ── Qdrant Cloud ────────────────────────────────────────────────────
QDRANT_URL = os.getenv("QDRANT_URL")          # ex: https://xxx.aws.cloud.qdrant.io:6333
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "study_agent")

# ── Parâmetros do RAG ──────────────────────────────────────────────
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
TOP_K = int(os.getenv("TOP_K", "5"))

# ── Pasta de documentos base (seed) ───────────────────────────────
DOCS_DIR = os.getenv("DOCS_DIR", "docs")
