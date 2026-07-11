# Deploying to Streamlit Community Cloud

The app (`app.py`) only **queries** the already-hosted Pinecone index — it does
not run ingestion — so deployment is lightweight. These are the steps **you**
perform (I can't create accounts or paste secrets on your behalf).

## Before you start — one required decision

⚠️ **Python version.** `pyproject.toml` declares `requires-python = ">=3.14"`, but
Streamlit Community Cloud does **not** offer Python 3.14 yet (it currently tops out
around 3.13). Nothing in the app actually needs 3.14. To deploy, on the Streamlit
Cloud app-creation screen set **Python version = 3.13** (the highest offered).
`requirements.txt` is used for dependency install, so the local `requires-python`
constraint doesn't block the Cloud build — but if you ever switch the Cloud build
to read `pyproject.toml`, relax that constraint to `>=3.11` first.

## What's already prepared in the repo

- **`requirements.txt`** — lean runtime deps for the deployed app (Streamlit,
  the LangChain Groq/Pinecone/HuggingFace pieces, sentence-transformers). The
  heavy ingestion/OCR libraries are intentionally excluded.
- **`.streamlit/secrets.toml.example`** — the secret keys the app expects.
- **`app.py`** bridges `st.secrets` into environment variables at startup, so the
  same `src/config.py` that reads `.env` locally works from Cloud secrets too.
- **`.gitignore`** excludes `.env` and `.streamlit/secrets.toml`.

## Steps

1. **Push the repo to GitHub** (the app must live in a GitHub repo Streamlit can read).
   The `pm-course` Pinecone index is already hosted, so no data needs to ship.
2. Go to **share.streamlit.io** and sign in with GitHub.
3. **Create app** → pick this repo/branch, set **Main file path** = `app.py`, and set
   **Python version = 3.13** under *Advanced settings*.
4. Open **Advanced settings → Secrets** and paste the contents of
   `.streamlit/secrets.toml.example` with your **real** key values filled in.
5. **Deploy.** First build takes a few minutes (sentence-transformers pulls in
   PyTorch). After it boots, the app downloads the `all-MiniLM-L6-v2` embedding
   model on first query — the first question will be slow, then it's cached.

## Notes & gotchas

- **Resource limits.** Community Cloud gives ~1 GB RAM. sentence-transformers +
  PyTorch + the model fit, but it's not spacious — if you hit OOM, that's the
  usual culprit.
- **Keys stay server-side.** Secrets are never exposed to the browser; the app
  reads them at runtime. Don't hard-code them anywhere.
- **Keeping content fresh.** To update the knowledge base, re-run ingestion
  **locally** (`uv run python -m src.ingest --reset`) — it writes to the same
  hosted Pinecone index the deployed app reads, so no redeploy is needed for
  content changes (only for code changes).
