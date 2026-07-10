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
