# Spec: Populate real course content

**Status:** ✅ Done (2026-07-11) &nbsp;·&nbsp; **Priority:** High &nbsp;·&nbsp; **Owner:** Kamalpreet

> **Completed.** Real PM course material is ingested and the chatbot answers from it.
> Live state (2026-07-11): `pm-course` Pinecone index holds a clean **2269** vectors
> (970 docs → 2269 chunks) across PDF (891 pages, 76 OCR'd), web cache (75), and YouTube (3).
> All acceptance criteria below verified — see the checked boxes. Retained as a record of the
> source-routing rules and gotchas, not as open work.

## Problem

The RAG pipeline (`src/ingest.py` → `src/vectorstore.py` → `src/chatbot.py`) is fully built,
but every source folder under `data/raw/` is empty. With nothing indexed, the retriever returns
no chunks and the chatbot has nothing to ground its answers in. This task is about getting the
actual Product Manager course material into the knowledge base so the chatbot becomes useful.

This is a **content-population** task, not a code task. No pipeline changes should be needed — if
you find yourself editing a loader to make a file load, that's a separate bug/spec.

## Goal

Load real PM course material into the vector store so that launching
`uv run streamlit run app.py` and asking a real course question returns a grounded, sourced answer.

## Source types & where each file goes

Each loader reads a fixed folder and tags its docs with a `source_type`. Put files in the right
place or they won't be picked up. All paths are defined in [`src/config.py`](../src/config.py).

| Source | Drop files in | Accepted by | `source_type` tag |
|---|---|---|---|
| Course PDFs, slide exports, scanned handouts | `data/raw/pdf/` | `PyPDFDirectoryLoader` (recursive), auto-OCR fallback | `pdf` |
| Cheat sheets / notes written in Markdown | `data/raw/markdown/` | `**/*.md` glob | `markdown` |
| Plain-text notes, transcripts you pasted by hand | `data/raw/text/` | `**/*.txt` glob | `text` |
| Public web articles | list URLs in `data/urls.txt` | fetched → cleaned → cached as `.md` in `data/raw/web_cache/` | `web` |
| Public YouTube videos | list URLs in `data/youtube_urls.txt` | caption transcript fetched via `youtube-transcript-api` | `youtube` |

Notes:
- **PDF loader is recursive** (`**`) and OCRs any page with < 20 chars of extractable text, so
  scanned handouts are fine — expect them to be slower and to log `looks scanned -- running OCR`.
- **Markdown and text loaders only match `.md` and `.txt` respectively.** A `.markdown` or `.text`
  file will be silently skipped. Rename before dropping in.
- `data/raw/` and `vectorstore/` are gitignored — this content is **not** committed. It's expected
  to be regenerated locally via ingest, so keep the original source files somewhere safe.
- Only add **public** URLs / videos. The YouTube loader's docstring explicitly warns against
  paywalled course platforms, and there's no auth for web fetches.

## Steps

1. Gather the real course material and sort it by type per the table above.
2. Copy files into the matching `data/raw/*` folders (create them if missing).
3. Add any public article URLs to `data/urls.txt` (one per line, `#` for comments).
4. Add any public video URLs to `data/youtube_urls.txt` (one per line, `#` for comments).
5. Run ingestion:
   ```
   uv run python -m src.ingest
   ```
6. Read the console output and confirm the per-loader counts are non-zero for every type you added
   (e.g. `[pdf_loader] Loaded N PDF pages`, `[markdown_loader] Loaded N manual .md ...`,
   `[youtube_loader] Loaded N YouTube transcripts`), and that the final
   `[ingest] Stored N chunks in <backend> vector store` line reports a sensible chunk count.

## Acceptance criteria

- [x] At least one real file is present and loading in **each** source type the course actually has
      (don't fabricate types you don't need — but PDFs and at least one of markdown/text should be covered).
      *PDF, markdown, web, and YouTube all load; `text` intentionally empty.*
- [x] `uv run python -m src.ingest` completes with `[SUCCESS] Ingestion complete.` and a non-zero
      stored-chunk count. *2269 chunks stored, clean.*
- [x] No loader silently reports `Loaded 0 ...` for a folder you deliberately populated.
- [x] In the Streamlit app, three representative PM questions return answers that are clearly drawn
      from the ingested material, with the source chunks shown alongside coming from the expected files.
      *Verified 2026-07-11 via `src.chatbot.get_answer` — PM vs PO, MVP, prioritization, AARRR all grounded at k=8.*
- [x] The chatbot declines / says it doesn't know when asked something outside the course material
      (confirms it's answering from context, not general knowledge). *Out-of-domain question correctly declined.*

## Dependencies & risks

- **Blocks:** *Run full ingestion end-to-end* and *Manually QA chatbot answers* — both are meaningless
  until real content exists.
- **~~Related open task:~~ RESOLVED:** *Fix Pinecone index name mismatch* — done. `PINECONE_INDEX_NAME`
  now defaults to the dedicated `pm-course` index (no longer the leftover `medibot`), and content was
  ingested into it fresh, so there's no co-mingling with the unrelated medical project. If iterating
  locally, setting `VECTORSTORE_BACKEND=chroma` still avoids touching Pinecone at all.
- **Risk — silent skips:** wrong extension or wrong folder = file ignored with no error. Always
  verify the loader counts after ingest rather than assuming a file was picked up.
- **Risk — no captions:** a YouTube video without a public transcript is skipped with a printed
  error, not a crash. Check the count if you expect a specific video to be present.
