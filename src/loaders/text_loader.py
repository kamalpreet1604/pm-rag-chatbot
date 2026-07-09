"""
text_loader.py
---------------
Loads every .txt file in data/raw/text/.
"""

from langchain_community.document_loaders import DirectoryLoader, TextLoader
from src import config


def load_text_files():
    loader = DirectoryLoader(
        config.TEXT_DIR,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    documents = loader.load()
    for doc in documents:
        doc.metadata["source_type"] = "text"

    print(f"[text_loader] Loaded {len(documents)} text files from {config.TEXT_DIR}")
    return documents


if __name__ == "__main__":
    docs = load_text_files()
    if docs:
        print(docs[0].metadata)
