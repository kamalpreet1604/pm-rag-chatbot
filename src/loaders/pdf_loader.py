"""
pdf_loader.py
-------------
Loads every PDF in data/raw/pdfs/ into LangChain Document objects.
OCR fallback: pages with little/no extractable text are automatically
re-rendered as images and run through Tesseract OCR.
"""

import os
from langchain_community.document_loaders import PyPDFDirectoryLoader
from src import config

MIN_TEXT_LENGTH = 20


def _ocr_page(pdf_path, page_number):
    from pdf2image import convert_from_path
    import pytesseract

    images = convert_from_path(
        pdf_path,
        first_page=page_number + 1,
        last_page=page_number + 1,
        dpi=300,
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

    ocr_count = 0
    for doc in documents:
        doc.metadata["source_type"] = "pdf"

        if len(doc.page_content.strip()) < MIN_TEXT_LENGTH:
            pdf_path = doc.metadata.get("source")
            page_number = doc.metadata.get("page", 0)

            if pdf_path and os.path.exists(pdf_path):
                print("[pdf_loader] Page", page_number, "of", pdf_path, "looks scanned -- running OCR...")
                try:
                    ocr_text = _ocr_page(pdf_path, page_number)
                except Exception as exc:
                    # OCR needs pdf2image/pytesseract + poppler; degrade gracefully if unavailable
                    print("[pdf_loader] OCR unavailable for page", page_number, "->", exc.__class__.__name__)
                    ocr_text = ""
                if ocr_text:
                    doc.page_content = ocr_text
                    doc.metadata["ocr_applied"] = True
                    ocr_count += 1

    print("[pdf_loader] Loaded", len(documents), "PDF pages from", all_dirs, "(", ocr_count, "pages required OCR)")
    return documents


if __name__ == "__main__":
    docs = load_pdfs()
    if docs:
        print(docs[0].metadata)
