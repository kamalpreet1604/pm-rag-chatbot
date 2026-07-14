# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

A RAG (Retrieval-Augmented Generation) chatbot over a personal Product Manager course knowledge base (PDFs, cheat sheets, cached web articles, YouTube transcripts). Ingestion is a batch pipeline (`src/ingest.py`) that loads, chunks, embeds, and stores documents; the chatbot (`src/chatbot.py`) retrieves relevant chunks and asks a Groq-hosted Llama model to answer from them only. `app.py` is a thin Streamlit UI on top of `src/chatbot.py`.

## Environment & setup

- Package manager is `uv` (see `uv.lock`); Python `>=3.14` per `pyproject.toml` / `.python-version`.
- The project venv is `.venv` (Python 3.14). Ignore `venv312/` if present — it's a stray Python 3.12 environment, not what the project targets.
- Install deps: `uv sync`
- Secrets/config live in `.env` (gitignored), loaded via `src/config.py`. Required/relevant vars:
  - `VECTORSTORE_BACKEND` — `pinecone` (default) or `chroma`
  - `PINECONE_API_KEY`, `PINECONE_INDEX_NAME` (when using Pinecone) — `.env` points at the `pm-course` index, a dedicated index built from the cleaned `data/raw/pdf/` set (created 2026-07-09). It replaced the old `medibot` index, a leftover name reused from an unrelated medical-chatbot project that co-mingled off-topic vectors; `medibot` is no longer used by this project
  - `GROQ_API_KEY`, `GROQ_MODEL` (default `llama-3.3-70b-versatile`) — required to run the chatbot. This model has a 128K-token context window and 32K max output on Groq, far more than the retrieval setup needs (`k=8` chunks at `CHUNK_SIZE=1000` chars), so context length isn't a real constraint unless `k`/chunk size grow substantially

## Common commands

Run everything with `uv run ...` (or activate `.venv` first):

```
uv run python -m src.ingest      # (re)build the knowledge base — run after adding/changing source files
uv run streamlit run app.py      # launch the chat UI
```

Individual loaders are also runnable standalone for debugging (each has a `if __name__ == "__main__"` block that prints what it loaded), e.g.:

```
uv run python -m src.loaders.pdf_loader
uv run python -m src.loaders.youtube_loader
```

There are no automated tests or lint configs in this repo currently.

## Architecture

**`src/config.py`** is the single source of truth for paths, chunk sizes, model names, and env-derived settings. Every other module reads from it rather than hardcoding paths or re-reading env vars — follow that pattern for new config.

**Ingestion pipeline (`src/ingest.py`)** runs in three steps, tying together all loaders:
1. `ingest_urls_from_file()` (web_loader) fetches URLs from `data/urls.txt`, strips boilerplate via `trafilatura`, and caches each as markdown in `data/raw/web_cache/`.
2. Each loader (`src/loaders/*.py`) independently loads its source type into LangChain `Document`s with a `source_type` metadata tag: `pdf_loader` (PDFs from `data/raw/pdf/`, with automatic OCR fallback via `pytesseract`/`pdf2image` for scanned pages with little extractable text), `markdown_loader` (`data/raw/markdown/` + `data/raw/web_cache/`), `text_loader` (`data/raw/text/`), `youtube_loader` (transcripts for public videos listed in `data/youtube_urls.txt` — not exported from `src/loaders/__init__.py`, imported directly in `ingest.py`).
3. All documents are merged, split with `RecursiveCharacterTextSplitter` (config-driven chunk size/overlap), and written to the vector store via `src/vectorstore.py`.

**`src/vectorstore.py`** branches on `config.VECTORSTORE_BACKEND`: `pinecone` (creates the serverless index if missing, dimension 384 to match the embedding model) or `chroma` (local persistent store under `vectorstore/chroma_db/`). Both share the same `HuggingFaceEmbeddings` (`all-MiniLM-L6-v2`) instance from `get_embeddings()`. Add new backends here rather than branching elsewhere.

**`src/chatbot.py`** builds an LCEL chain (a hand-rolled replacement for the removed `RetrievalQA`): retriever → format context → custom prompt → `ChatGroq` → `StrOutputParser`, wrapped in `RunnableParallel` so both the answer and the source chunks used come back from `get_answer()`. The vectorstore and chain are built once via `@st.cache_resource`.

**`0-dataparsing/`** holds an exploratory notebook used to prototype document loading/splitting; it's not part of the production pipeline in `src/`.

**Data layout**: raw source material lives under `data/raw/` (`pdf/`, `markdown/`, `text/`, `web_cache/`) plus `data/urls.txt` and `data/youtube_urls.txt` as ingestion inputs. `data/raw/` and `vectorstore/` are gitignored — regenerate with the ingest command above rather than expecting them to be checked in.
