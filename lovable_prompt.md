# 🎨 Prompt para o Lovable — Frontend do Agente de Estudos

Cole o bloco abaixo diretamente no Lovable para gerar a interface completa.

> **Antes de colar:** substitua a URL base da API pela URL real do seu deploy no Render.

---

```
Crie uma aplicação web React moderna e responsiva para um "Agente de Estudos em Engenharia de Dados & IA".

A aplicação consome uma API REST já existente. A URL base da API é uma variável de ambiente configurável (VITE_API_URL), com fallback para "https://study-agent-rag.onrender.com".

Aqui está a documentação completa dos endpoints da API que o frontend deve consumir:

## Endpoints disponíveis

### GET /health
- Retorna: {"status": "healthy"|"degraded", "service": "study-agent-rag", "qdrant_connected": true|false}
- Usar para mostrar badge de status da API no header

### GET /stats
- Retorna: {"collection": "study_agent", "total_points": 1234, "status": "green"}
- Usar para mostrar total de documentos vetorizados

### POST /ingest (multipart/form-data)
- Body: FormData com campo "file" contendo um PDF
- Retorna: {"status": "ok", "filename": "doc.pdf", "total_chunks": 15, "total_characters": 8200, "collection": "study_agent"}
- Aceita apenas arquivos .pdf

### POST /ingest/url (JSON)
- Body: {"url": "https://arxiv.org/pdf/2005.11401v4"}
- Retorna: mesmo schema do /ingest
- Baixa PDF de URL pública e ingere

### POST /query (JSON)
- Body: {"question": "O que é um pipeline de ETL?"} (min 3 chars, max 1000)
- Retorna:
  {
    "answer": "Um pipeline de ETL consiste em...",
    "sources": ["engenharia_dados_estudo.pdf"],
    "chunks_used": 5,
    "retrieved_chunks": [
      {
        "text": "ETL significa Extract, Transform...",
        "source": "engenharia_dados_estudo.pdf",
        "score": 0.9234,
        "chunk_index": 0
      }
    ]
  }

## Layout da aplicação

- Header fixo com título "📚 Agente de Estudos — Engenharia de Dados & IA" e um badge mostrando o status da API (verde=online, vermelho=offline). Faça um GET em /health ao carregar para verificar.
- Duas abas/seções: "💬 Perguntar" e "📄 Enviar Material"

## Aba "Perguntar" (principal)
- Campo de texto (textarea) para o aluno digitar a pergunta
- Botão "Perguntar ao Agente" que faz POST em /query com body {"question": "texto"}
- Área de resposta estilizada como card com:
  - A resposta do agente (renderizar markdown se houver)
  - Lista de fontes usadas (campo "sources" do response)
  - Badge com número de chunks usados
  - Seção expansível/colapsável "Ver trechos recuperados" mostrando os retrieved_chunks com score de relevância em formato de barra de progresso
- Skeleton/loading state enquanto a API processa
- Histórico de perguntas anteriores na lateral esquerda (sidebar colapsável no mobile)

## Aba "Enviar Material"
- Duas sub-seções lado a lado (ou empilhadas no mobile):

  1. "Upload de PDF":
     - Área de drag-and-drop para upload de PDF
     - Ao soltar o arquivo, faz POST em /ingest com FormData contendo o campo "file"
     - Mostra progresso do upload

  2. "Ingerir por URL":
     - Campo de input para colar URL de PDF público (ex: arXiv, Google Drive)
     - Botão "Ingerir URL" que faz POST em /ingest/url com body {"url": "texto"}
     - Placeholder de exemplo: "https://arxiv.org/pdf/2005.11401v4"

- Após sucesso em qualquer via, mostra card com métricas: nome do arquivo, total de chunks, total de caracteres
- Botão para ver estatísticas da base (GET /stats mostrando total de documentos vetorizados)

## Design
- Tema escuro como padrão com toggle para tema claro
- Cores principais: azul (#3B82F6) e roxo (#8B5CF6) em gradientes sutis
- Cards com glassmorphism (backdrop-blur, bordas semi-transparentes)
- Tipografia moderna (Inter ou system font stack)
- Animações suaves de entrada nos cards de resposta
- Mobile-first, totalmente responsivo

## Tratamento de erros
- Se a API retornar erro, mostrar toast/notification com a mensagem
- Se a API estiver offline, desabilitar os botões e mostrar banner informativo
- Validar que a pergunta tem pelo menos 3 caracteres antes de enviar

## Extras
- Sugestões de perguntas prontas (chips clicáveis) como "O que é ETL?", "Explique Data Lake vs Data Warehouse", "Como funciona Apache Airflow?", "O que é RAG?", "Pra que serve um banco vetorial?"
- Ao clicar numa sugestão, preenche o campo e envia automaticamente
- Mostrar timestamp nas perguntas do histórico
- Footer discreto com "Powered by FastAPI + Qdrant + OpenAI"
```
