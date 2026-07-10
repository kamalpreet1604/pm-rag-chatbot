"""
chatbot.py
-----------
Builds a cached retrieval + generation chain: pulls the closest chunks
from the vector store, drops them into a prompt template, and asks
Groq's Llama model to answer using only that context.

(Same shape as the classic RetrievalQA pattern -- cached vectorstore,
custom prompt, dedicated load_llm() -- rebuilt with LCEL since
langchain.chains.RetrievalQA was removed in langchain 1.x.)
"""

import streamlit as st
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_groq import ChatGroq

from src import config
from src.vectorstore import get_vectorstore

CUSTOM_PROMPT_TEMPLATE = """
Use the pieces of information provided in the context to answer the user's question.
If you don't know the answer based on the context, just say you don't know -- don't make one up.
Only use information from the given context, and don't provide anything outside of it.

Context: {context}
Question: {question}

Answer directly, in a clear and helpful way.
"""


def set_custom_prompt(template=CUSTOM_PROMPT_TEMPLATE):
    return PromptTemplate(template=template, input_variables=["context", "question"])


@st.cache_resource
def get_vectorstore_cached():
    return get_vectorstore()


def load_llm():
    if not config.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")
    return ChatGroq(model=config.GROQ_MODEL, api_key=config.GROQ_API_KEY, temperature=0.3)


def format_docs(docs):
    return "\n\n".join(
        f"[{doc.metadata.get('source', 'unknown')}]\n{doc.page_content}" for doc in docs
    )


@st.cache_resource
def get_chain():
    retriever = get_vectorstore_cached().as_retriever(search_kwargs={"k": 8})
    prompt = set_custom_prompt()
    llm = load_llm()

    return RunnableParallel(
        context=retriever, question=RunnablePassthrough()
    ).assign(
        answer=(
            {"context": lambda x: format_docs(x["context"]), "question": lambda x: x["question"]}
            | prompt
            | llm
            | StrOutputParser()
        )
    )


def get_answer(question):
    chain = get_chain()
    result = chain.invoke(question)
    sources = sorted({doc.metadata.get("source", "unknown") for doc in result["context"]})
    return result["answer"], sources
