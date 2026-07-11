# RAGUdemy

A Retrieval-Augmented Generation (RAG) chatbot over a personal **Product Manager course** knowledge base — PDFs, cheat sheets, cached web articles, and YouTube transcripts. Ask a question and a Groq-hosted Llama model answers **only** from the retrieved course material.

## How it works

1. **Ingest** (`src/ingest.py`) — a batch pipeline that loads every source, chunks it, embeds it with `all-MiniLM-L6-v2`, and writes vectors to the store.
2. **Retrieve + answer** (`src/chatbot.py`) — an LCEL chain: retriever → format context → prompt → `ChatGroq` → parser. Returns both the answer and the source chunks it used.
3. **UI** (`app.py`) — a thin Streamlit chat interface over `src/chatbot.py`.

## Setup

Package manager is [`uv`](https://docs.astral.sh/uv/); Python `>=3.14`.

```bash
uv sync
```

Create a `.env` (gitignored) with:

| Var | Purpose |
| --- | --- |
| `VECTORSTORE_BACKEND` | `pinecone` (default) or `chroma` |
| `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` | required for the Pinecone backend (index: `pm-course`) |
| `GROQ_API_KEY`, `GROQ_MODEL` | required to run the chatbot (default `llama-3.3-70b-versatile`) |

## Usage

```bash
uv run python -m src.ingest            # add current sources to the store (APPENDS)
uv run python -m src.ingest --reset    # clear the store first, then rebuild (REPLACES)
uv run streamlit run app.py            # launch the chat UI
```

Use `--reset` whenever you re-ingest existing content (e.g. after adding a source) so you get one clean copy instead of stacking duplicate vectors. It clears the store, waits for the backend to confirm it's empty, rebuilds, and verifies the final count.

Individual loaders are runnable standalone for debugging:

```bash
uv run python -m src.loaders.pdf_loader
uv run python -m src.loaders.youtube_loader
```

## Data layout

Raw source material lives under `data/raw/` (gitignored — regenerate by re-ingesting):

- `data/raw/pdf/` — course PDFs (automatic OCR fallback for scanned pages via `pytesseract` / `pdf2image`)
- `data/raw/markdown/`, `data/raw/text/` — notes and cheat sheets
- `data/raw/web_cache/` — web articles cached as markdown (fetched from `data/urls.txt`, boilerplate stripped via `trafilatura`)
- `data/urls.txt`, `data/youtube_urls.txt` — ingestion inputs

## Architecture notes

- **`src/config.py`** is the single source of truth for paths, chunk sizes, and model names. Other modules read from it rather than hardcoding.
- **`src/vectorstore.py`** branches on `VECTORSTORE_BACKEND` (Pinecone serverless, dim 384, or local Chroma under `vectorstore/chroma_db/`). Add new backends here.
- **`0-dataparsing/`** is an exploratory notebook, not part of the production pipeline.

There are currently no automated tests or lint configs in this repo.
