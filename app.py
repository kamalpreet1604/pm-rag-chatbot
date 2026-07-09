"""
app.py
-------
Simple Streamlit chat UI for your Product Manager knowledge base.

Run with:
    streamlit run app.py
"""

import streamlit as st
from src.chatbot import get_answer

st.set_page_config(page_title="PM Knowledge Base", page_icon="📘")
st.title("Product Manager Knowledge Base")
st.caption("Ask questions about your course PDFs and articles")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

question = st.chat_input("Ask a question...")

if question:
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
            answer, sources = get_answer(question)
            st.markdown(answer)
            if sources:
                with st.expander("Sources"):
                    for s in sources:
                        st.write("-", s)

    st.session_state.messages.append({"role": "assistant", "content": answer})
