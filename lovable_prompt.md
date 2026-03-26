# 🎨 Prompt para o Lovable — Frontend do Agente de Estudos

Cole o bloco abaixo diretamente no Lovable para gerar a interface completa.

---

```
Crie uma aplicação web React + TypeScript + Tailwind CSS + Vite para um Agente de Estudos RAG em Engenharia de Dados & IA.

## API Backend (já existente)

Base URL: https://chat-de-estudos-teste.onrender.com

Endpoints:

| Método | Rota          | Body                                  | Resposta                                                                                          |
|--------|---------------|---------------------------------------|---------------------------------------------------------------------------------------------------|
| GET    | /health       | —                                     | { status, service, qdrant_connected }                                                             |
| GET    | /stats        | —                                     | { collection, total_points, status }                                                              |
| POST   | /ingest       | FormData { file: PDF }                | { status, filename, total_chunks, total_characters, collection }                                  |
| POST   | /ingest/url   | { url: string }                       | mesmo schema do /ingest                                                                           |
| POST   | /query        | { question: string } (3-1000 chars)   | { answer, sources[], chunks_used, retrieved_chunks[{ text, source, score, chunk_index }] }        |

Crie um módulo `src/lib/api.ts` centralizando todas as chamadas com tipagem completa (interfaces para cada response). Use fetch nativo sem Axios.

## Layout & Estrutura

**Header fixo:**
- Logo da marca (importada de `src/assets/logo.jpeg`) centralizada acima do conteúdo principal
- Título "Agente de Estudos — Engenharia de Dados & IA" com gradiente de texto
- Badge de status da API (chama GET /health ao montar): verde = online, vermelho = offline
- Toggle de tema claro/escuro (usar next-themes)

**Corpo principal** com duas abas (usar componente Tabs do shadcn):
- 💬 Perguntar (aba padrão)
- 📄 Enviar Material

**Sidebar esquerda** (colapsável no mobile):
- Histórico de perguntas anteriores com timestamp
- Ao clicar numa entrada, recarrega a pergunta e resposta

**Footer:**
- "Powered by FastAPI + Qdrant + OpenAI"

## Aba "Perguntar"

**Chips de sugestões no topo:**
- "O que é ETL?", "Explique Data Lake vs Data Warehouse", "Como funciona Apache Airflow?", "O que é RAG?", "Pra que serve um banco vetorial?"
- Ao clicar, preenche o textarea e dispara a query automaticamente

**Área de input:**
- textarea dentro de um card glassmorphism
- Enter envia (Shift+Enter para nova linha)
- Botão "Perguntar ao Agente" com ícone Send, desabilitado se < 3 chars ou loading

**Exibição da resposta** — 3 cards separados em sequência vertical:

1. **Card da Resposta** — apenas o texto da resposta renderizado com react-markdown
   - IMPORTANTE: A API pode incluir "Trechos-fonte utilizados: Trecho 1, Trecho 2..." no final do campo answer. Remover essa parte com regex antes de renderizar: `.replace(/Trechos-fonte utilizados:[\s\S]*/i, '').trim()`

2. **Card de Fontes** — card separado abaixo com:
   - Título "FONTES" em uppercase
   - Badge com número de chunks usados
   - Badges com nomes dos arquivos fonte

3. **Card de Trechos Recuperados** — card separado abaixo com:
   - Botão colapsável "Ver trechos recuperados (N)"
   - Ao expandir, mostra cada chunk com: source, chunk_index, score em % com barra de progresso, e texto truncado (line-clamp-4)

**Loading state:** skeleton pulse com 4 linhas de tamanhos variados

**Animações:** usar framer-motion com AnimatePresence para entrada dos cards (fade + slide up), com delay escalonado entre os 3 cards.

## Aba "Enviar Material"

Duas sub-seções lado a lado (empilhadas no mobile):

1. **Upload de PDF:**
   - Área de drag-and-drop estilizada (ícone Upload, texto instrucional)
   - Aceita apenas .pdf
   - Ao soltar/selecionar, faz POST /ingest com FormData
   - Mostra estado de loading durante upload

2. **Ingerir por URL:**
   - Input com placeholder `https://arxiv.org/pdf/2005.11401v4`
   - Botão "Ingerir URL" que faz POST /ingest/url

**Após sucesso em qualquer via:**
- Card de resultado com: nome do arquivo, total de chunks, total de caracteres
- Animação de entrada

**Botão "Ver Estatísticas da Base":**
- Chama GET /stats
- Mostra total de documentos vetorizados em card

## Design System

**Tema escuro como padrão.** Definir tokens semânticos em CSS variables HSL no index.css:

`:root` (light) e `.dark`:
- `--background`, `--foreground`, `--card`, `--primary`, `--secondary`, `--muted`, `--accent`, `--border`, `--ring`

**Paleta:**
- Primary: azul `217 91% 60%`
- Accent: âmbar/dourado `45 96% 53%` (combinar com a logo)
- Background dark: `220 20% 6%`
- Cards: glassmorphism com `backdrop-blur-2xl`, `bg-card/60`, `border-border/20`
- Background: radial gradients sutis de primary e accent com opacidade baixa

**Tipografia:** system font stack, sem fontes externas. Títulos com gradient-text (gradiente de primary para accent).

**Classe utilitária `.glass-card`:**
```css
.glass-card {
  @apply bg-card/60 backdrop-blur-2xl border border-border/20 rounded-2xl shadow-2xl;
}
```

**Responsividade:** mobile-first. Sidebar vira drawer no mobile. Grid de 2 colunas no desktop para a aba de ingestão.

## Tratamento de Erros

- Toast (shadcn) para erros da API com mensagem descritiva
- Se /health retornar offline, mostrar banner e desabilitar botões
- Validação client-side: pergunta ≥ 3 chars, arquivo deve ser .pdf, URL deve ser válida

## Dependências necessárias

- `react-markdown` para renderizar respostas
- `framer-motion` para animações
- `next-themes` para toggle de tema
- `lucide-react` para ícones
- shadcn/ui components: Tabs, Progress, Toast, Sheet (sidebar mobile)

## Estrutura de arquivos

```
src/
  lib/api.ts          — tipos e funções de chamada à API
  components/
    AppHeader.tsx      — header com logo, título, badge status, theme toggle
    QueryTab.tsx       — aba de perguntas com input, sugestões, resultado
    IngestTab.tsx      — aba de upload/ingestão
    HistorySidebar.tsx — sidebar com histórico
  pages/
    Index.tsx          — página principal compondo tudo
  assets/
    logo.jpeg          — logo da marca
```
```
