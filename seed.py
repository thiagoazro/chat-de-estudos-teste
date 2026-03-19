"""
seed.py — Ingestão em batch de todos os PDFs da pasta docs/.

Este script varre a pasta docs/ e ingere cada PDF no Qdrant.
Pode ser chamado:
  - Manualmente: python seed.py
  - No boot da aplicação (via lifespan do FastAPI)
  - No Dockerfile como step de inicialização

Conceito de Engenharia de Dados:
  Isso é equivalente a um "backfill" — carregar dados históricos
  antes do sistema entrar em produção. Em pipelines de dados,
  o backfill é o primeiro passo antes de ativar ingestão incremental.
"""

import os
import glob
from pathlib import Path

from ingest import ingest_document, ensure_collection_exists

DOCS_DIR = os.getenv("DOCS_DIR", "docs")


def seed_documents(docs_dir: str = DOCS_DIR) -> list[dict]:
    """
    Varre a pasta docs_dir, encontra todos os PDFs e ingere cada um.

    Retorna lista de resultados (um dict por arquivo).
    Como usamos IDs determinísticos no ingest, rodar o seed
    várias vezes NÃO duplica dados (idempotência).
    """
    ensure_collection_exists()

    pdf_files = sorted(glob.glob(os.path.join(docs_dir, "**", "*.pdf"), recursive=True))

    if not pdf_files:
        print(f"⚠️  Nenhum PDF encontrado em '{docs_dir}/'.")
        return []

    print(f"📂 Encontrados {len(pdf_files)} PDFs em '{docs_dir}/':")
    results = []

    for pdf_path in pdf_files:
        filename = Path(pdf_path).name
        print(f"\n  📄 Ingerindo: {filename}")

        try:
            with open(pdf_path, "rb") as f:
                import io
                file_bytes = io.BytesIO(f.read())

            result = ingest_document(
                file_bytes=file_bytes,
                filename=filename,
                source=str(pdf_path),
            )
            results.append(result)

            if result.get("status") == "ok":
                print(f"     ✅ {result['total_chunks']} chunks | {result['total_characters']} chars")
            else:
                print(f"     ❌ {result.get('detail', 'erro desconhecido')}")

        except Exception as e:
            print(f"     ❌ Erro: {e}")
            results.append({"status": "error", "filename": filename, "detail": str(e)})

    # Resumo
    ok = sum(1 for r in results if r.get("status") == "ok")
    total_chunks = sum(r.get("total_chunks", 0) for r in results)
    print(f"\n{'='*50}")
    print(f"🏁 Seed completo: {ok}/{len(results)} arquivos ingeridos | {total_chunks} chunks total")

    return results


if __name__ == "__main__":
    seed_documents()
