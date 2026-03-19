# 📂 Pasta de Documentos Base

Coloque aqui os PDFs que serão ingeridos automaticamente ao iniciar a aplicação.

## Como funciona

1. Coloque seus PDFs nesta pasta (subpastas são suportadas)
2. Ao iniciar a API (`uvicorn main:app`), o seed roda automaticamente
3. Todos os PDFs são processados: texto extraído → chunks → embeddings → Qdrant
4. IDs são determinísticos — rodar o seed várias vezes NÃO duplica dados

## Sugestões de materiais para o agente de estudos

- Apostilas sobre Engenharia de Dados
- Papers sobre RAG, embeddings, vector databases
- Documentação de ferramentas (Spark, Airflow, dbt)
- Slides de aulas convertidos em PDF
- Artigos sobre MLOps e deploy de modelos

## Exemplo de estrutura

```
docs/
├── engenharia_dados_fundamentos.pdf
├── rag_overview.pdf
├── spark/
│   ├── pyspark_basics.pdf
│   └── spark_tuning.pdf
└── mlops/
    └── deploy_patterns.pdf
```
