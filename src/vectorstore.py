"""
vectorstore.py
---------------
Gets your vector store, regardless of backend.
Defaults to Pinecone (the pm-course index).
"""

from langchain_huggingface import HuggingFaceEmbeddings
from src import config


def get_embeddings():
    return HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)


def get_vectorstore():
    embeddings = get_embeddings()

    if config.VECTORSTORE_BACKEND == "pinecone":
        from langchain_pinecone import PineconeVectorStore
        from pinecone import Pinecone, ServerlessSpec

        pc = Pinecone(api_key=config.PINECONE_API_KEY)

        existing_indexes = [idx["name"] for idx in pc.list_indexes()]
        if config.PINECONE_INDEX_NAME not in existing_indexes:
            pc.create_index(
                name=config.PINECONE_INDEX_NAME,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

        return PineconeVectorStore.from_existing_index(
            index_name=config.PINECONE_INDEX_NAME,
            embedding=embeddings,
        )

    elif config.VECTORSTORE_BACKEND == "chroma":
        from langchain_chroma import Chroma

        return Chroma(
            collection_name=config.CHROMA_COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=config.CHROMA_PERSIST_DIR,
        )

    else:
        raise ValueError(f"Unknown VECTORSTORE_BACKEND: {config.VECTORSTORE_BACKEND}")


def count_vectors():
    """Return the current number of vectors in the store (0 if it doesn't exist yet)."""
    if config.VECTORSTORE_BACKEND == "pinecone":
        from pinecone import Pinecone

        pc = Pinecone(api_key=config.PINECONE_API_KEY)
        if config.PINECONE_INDEX_NAME not in [i["name"] for i in pc.list_indexes()]:
            return 0
        idx = pc.Index(config.PINECONE_INDEX_NAME)
        return idx.describe_index_stats().get("total_vector_count") or 0

    elif config.VECTORSTORE_BACKEND == "chroma":
        import os

        if not os.path.exists(config.CHROMA_PERSIST_DIR):
            return 0
        try:
            return get_vectorstore()._collection.count()
        except Exception:
            return None

    return None


def clear_vectorstore():
    """
    Delete ALL vectors so the next ingest REPLACES the knowledge base instead of
    appending a second copy. Used by `python -m src.ingest --reset`.

    Pinecone serverless deletes asynchronously, so this waits until the index
    actually reports zero before returning -- writing during that window is what
    previously left duplicate/leftover vectors behind.
    """
    if config.VECTORSTORE_BACKEND == "pinecone":
        import time
        from pinecone import Pinecone

        pc = Pinecone(api_key=config.PINECONE_API_KEY)
        if config.PINECONE_INDEX_NAME not in [i["name"] for i in pc.list_indexes()]:
            print("[vectorstore] Pinecone index does not exist yet -- nothing to clear.")
            return
        idx = pc.Index(config.PINECONE_INDEX_NAME)
        try:
            idx.delete(delete_all=True)
        except Exception as exc:
            # delete_all raises if the namespace is already empty -- that's fine.
            print("[vectorstore] delete_all note:", exc.__class__.__name__)
        for _ in range(40):
            if (idx.describe_index_stats().get("total_vector_count") or 0) == 0:
                print("[vectorstore] Pinecone index confirmed empty.")
                return
            time.sleep(3)
        print("[vectorstore] WARNING: index did not reach 0 within timeout.")

    elif config.VECTORSTORE_BACKEND == "chroma":
        import os
        import shutil

        if os.path.exists(config.CHROMA_PERSIST_DIR):
            shutil.rmtree(config.CHROMA_PERSIST_DIR)
            print("[vectorstore] Deleted local Chroma store.")
        else:
            print("[vectorstore] No Chroma store to clear.")

    else:
        raise ValueError(f"Unknown VECTORSTORE_BACKEND: {config.VECTORSTORE_BACKEND}")
