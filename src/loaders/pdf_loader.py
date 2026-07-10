"""
pdf_loader.py
-------------
Loads every PDF in data/raw/pdfs/ into LangChain Document objects.
OCR fallback: pages with little/no extractable text are automatically
re-rendered as images and run through Tesseract OCR.

OCR is expensive, so its output is cached on disk (data/raw/ocr_cache/).
A scanned page is OCR'd once; every later ingest reuses the cached text.
The cache key includes the PDF's modification time, so editing/replacing a
PDF automatically invalidates its stale OCR text.
"""

import json
import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from src import config

MIN_TEXT_LENGTH = 20


def _cache_file():
    return os.path.join(config.OCR_CACHE_DIR, "ocr_cache.json")


def _load_cache():
    path = _cache_file()
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            print("[pdf_loader] OCR cache unreadable -- starting fresh")
    return {}


def _save_cache(cache):
    os.makedirs(config.OCR_CACHE_DIR, exist_ok=True)
    with open(_cache_file(), "w", encoding="utf-8") as f:
        json.dump(cache, f)


def _cache_key(pdf_path, page_number):
    # mtime + dpi in the key: a re-saved PDF or a DPI change invalidates the entry.
    try:
        mtime = int(os.path.getmtime(pdf_path))
    except OSError:
        mtime = 0
    return f"{os.path.abspath(pdf_path)}|{page_number}|{mtime}|{config.OCR_DPI}"


def _ocr_page(pdf_path, page_number):
    from pdf2image import convert_from_path
    import pytesseract

    images = convert_from_path(
        pdf_path,
        first_page=page_number + 1,
        last_page=page_number + 1,
        dpi=config.OCR_DPI,
    )
    if not images:
        return ""

    text = pytesseract.image_to_string(images[0])
    return text.strip()


def load_pdfs():
    all_dirs = [config.PDF_DIR] + getattr(config, "EXTRA_PDF_DIRS", [])
    documents = []

    for folder in all_dirs:
        if not os.path.exists(folder):
            print("[pdf_loader] Skipping missing folder:", folder)
            continue
        # silent_errors: skip unreadable/encrypted PDFs instead of aborting the batch
        loader = PyPDFDirectoryLoader(folder, silent_errors=True)
        documents.extend(loader.load())

    cache = _load_cache()
    cache_dirty = False
    ocr_count = 0
    cache_hits = 0

    for doc in documents:
        doc.metadata["source_type"] = "pdf"

        if len(doc.page_content.strip()) < MIN_TEXT_LENGTH:
            pdf_path = doc.metadata.get("source")
            page_number = doc.metadata.get("page", 0)

            if pdf_path and os.path.exists(pdf_path):
                key = _cache_key(pdf_path, page_number)
                if key in cache:
                    ocr_text = cache[key]
                    cache_hits += 1
                else:
                    print("[pdf_loader] Page", page_number, "of", pdf_path, "looks scanned -- running OCR...")
                    try:
                        ocr_text = _ocr_page(pdf_path, page_number)
                    except Exception as exc:
                        # OCR needs pdf2image/pytesseract + poppler; degrade gracefully if unavailable
                        print("[pdf_loader] OCR unavailable for page", page_number, "->", exc.__class__.__name__)
                        ocr_text = ""
                    # Cache every result, including "" (an empty page won't be re-OCR'd next run).
                    cache[key] = ocr_text
                    cache_dirty = True

                if ocr_text:
                    doc.page_content = ocr_text
                    doc.metadata["ocr_applied"] = True
                    ocr_count += 1

    if cache_dirty:
        _save_cache(cache)

    print(
        "[pdf_loader] Loaded", len(documents), "PDF pages from", all_dirs,
        "(", ocr_count, "OCR pages;", cache_hits, "from cache )",
    )
    return documents


if __name__ == "__main__":
    docs = load_pdfs()
    if docs:
        print(docs[0].metadata)
