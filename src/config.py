"""
config.py
---------
Single source of truth for paths, model names, and settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data", "raw")

PDF_DIR = os.path.join(DATA_DIR, "pdf")
# Additional folders to scan for PDFs. Kept empty so ingestion only reads the
# curated data/raw/pdf/ set; add absolute paths here to pull in extra sources.
EXTRA_PDF_DIRS = []
# OCR fallback settings (pdf_loader). Results are cached per page under
# OCR_CACHE_DIR so a scanned page is only OCR'd once, not on every ingest.
# OCR_DPI trades speed for accuracy: lower = faster render + OCR, less precise.
OCR_DPI = 300
OCR_CACHE_DIR = os.path.join(DATA_DIR, "ocr_cache")
MARKDOWN_DIR = os.path.join(DATA_DIR, "markdown")
TEXT_DIR = os.path.join(DATA_DIR, "text")
WEB_CACHE_DIR = os.path.join(DATA_DIR, "web_cache")
URLS_FILE = os.path.join(BASE_DIR, "data", "urls.txt")
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HUGGINGFACEHUB_API_TOKEN = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
VECTORSTORE_BACKEND = os.environ.get("VECTORSTORE_BACKEND", "pinecone")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "pm-course")

CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "vectorstore", "chroma_db")
CHROMA_COLLECTION_NAME = "knowledge_base"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

REQUEST_TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (compatible; KBIngestBot/1.0)"
