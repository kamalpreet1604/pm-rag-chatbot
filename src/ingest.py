"""
ingest.py
----------
THE main script. Run this whenever you add new PDFs, markdown files,
text files, URLs, or YouTube videos to the knowledge base.

Usage:
    python -m src.ingest
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config
from src.loaders import (
    load_pdfs,
    load_markdown_files,
    load_text_files,
    ingest_urls_from_file,
)
from src.loaders.youtube_loader import load_youtube_urls_from_file
from src.vectorstore import get_vectorstore


def load_all_documents():
    print("=== Step 1: Converting URLs to markdown ===")
    ingest_urls_from_file()

    print("=== Step 2: Loading documents from every source ===")
    pdf_docs = load_pdfs()
    markdown_docs = load_markdown_files()
    text_docs = load_text_files()
    youtube_docs = load_youtube_urls_from_file()

    all_docs = pdf_docs + markdown_docs + text_docs + youtube_docs
    print("=== Step 3: Merged total documents:", len(all_docs), "===")
    return all_docs


def chunk_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print("[ingest] Split", len(documents), "documents into", len(chunks), "chunks")
    return chunks


def store_chunks(chunks):
    if not chunks:
        print("[ingest] No chunks to store -- nothing to do.")
        return

    vs = get_vectorstore()
    vs.add_documents(chunks)
    print("[ingest] Stored", len(chunks), "chunks in", config.VECTORSTORE_BACKEND, "vector store")


def run():
    documents = load_all_documents()
    if not documents:
        print("No documents found in any source folder. Add files and re-run.")
        return
    chunks = chunk_documents(documents)
    store_chunks(chunks)
    print("[SUCCESS] Ingestion complete.")


if __name__ == "__main__":
    run()