"""
app.py
-------
Streamlit chat UI for your Product Manager knowledge base.

Run with:
    streamlit run app.py
"""

import os

import streamlit as st

# On Streamlit Community Cloud there is no .env file — secrets are provided via
# st.secrets. Bridge them into the environment BEFORE importing src.config, which
# captures env vars at import time. setdefault means a real .env still wins locally.
try:
    for _key, _val in st.secrets.items():
        os.environ.setdefault(_key, str(_val))
except Exception:
    pass  # No secrets.toml (e.g. local dev with .env) — that's fine.

from src.chatbot import get_answer

st.set_page_config(page_title="PM knowledge base", page_icon=":material/menu_book:")

# Example questions shown as clickable chips before the first message.
SUGGESTIONS = {
    ":material/compare_arrows: PM vs product owner": "What is the difference between a product manager and a product owner?",
    ":material/science: What is an MVP?": "What is a minimum viable product and why does it matter?",
    ":material/low_priority: Prioritizing features": "How should a product manager prioritize features?",
    ":material/analytics: AARRR metrics": "What is the AARRR pirate metrics framework?",
}


def source_label(src):
    """Turn a raw source (file path or URL) into an (icon, label, is_link) tuple for display."""
    if src.startswith("http"):
        icon = ":material/smart_display:" if "youtu" in src else ":material/link:"
        return icon, src, True
    name = os.path.basename(src)
    lower = src.replace("\\", "/").lower()
    if lower.endswith(".pdf"):
        icon = ":material/picture_as_pdf:"
    elif "/web_cache/" in lower:
        icon = ":material/language:"
    elif "/markdown/" in lower or lower.endswith(".md"):
        icon = ":material/description:"
    else:
        icon = ":material/article:"
    return icon, name, False


def render_sources(sources):
    """Show the source chunks an answer was grounded in, as a tidy expandable list."""
    if not sources:
        return
    with st.expander(f"Sources ({len(sources)})", icon=":material/folder_open:"):
        for src in sources:
            icon, label, is_link = source_label(src)
            if is_link:
                st.markdown(f"{icon} [{label}]({label})")
            else:
                st.markdown(f"{icon} {label}")


st.title("Product Manager knowledge base")
st.caption("Ask about your PM course PDFs, articles, and videos. Answers are grounded only in that material.")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.markdown("#### About")
    st.caption(
        "A retrieval-augmented chatbot over a personal Product Manager course "
        "knowledge base (PDFs, web articles, and YouTube transcripts)."
    )
    if st.button("Clear chat", icon=":material/delete:", width="stretch"):
        st.session_state.messages = []
        st.session_state.pop("suggestion", None)
        st.rerun()

# Replay the conversation, including the sources each answer used.
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant":
            render_sources(msg.get("sources", []))

# Capture a new question from either the suggestion chips (empty chat only) or the input box.
prompt = None
if not st.session_state.messages:
    picked = st.pills(
        "Try asking", list(SUGGESTIONS.keys()), key="suggestion", label_visibility="collapsed"
    )
    if picked:
        prompt = SUGGESTIONS[picked]

typed = st.chat_input("Ask a question...", submit_mode="disable")
if typed:
    prompt = typed

# Record the question and rerun so the chips vanish and the message shows immediately;
# the answer is then generated below for whatever user turn is still unanswered.
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        with st.spinner("Searching the knowledge base..."):
            answer, sources = get_answer(st.session_state.messages[-1]["content"])
        st.markdown(answer)
        render_sources(sources)
    st.session_state.messages.append({"role": "assistant", "content": answer, "sources": sources})
