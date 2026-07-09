"""
markdown_loader.py
-------------------
Loads .md files from data/raw/markdown/ AND data/raw/web_cache/
(web_cache holds markdown auto-generated from URLs).
"""

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from src import config


def _load_md_folder(folder_path, source_type_label):
    loader = DirectoryLoader(
        folder_path,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    documents = loader.load()
    for doc in documents:
        doc.metadata["source_type"] = source_type_label
    return documents


def load_markdown_files():
    manual_md = _load_md_folder(config.MARKDOWN_DIR, "markdown")
    web_md = _load_md_folder(config.WEB_CACHE_DIR, "web")

    documents = manual_md + web_md
    print("[markdown_loader] Loaded", len(manual_md), "manual .md +", len(web_md), "web-cached .md files")
    return documents


if __name__ == "__main__":
    docs = load_markdown_files()
    if docs:
        print(docs[0].metadata)
