"""
faithfulness_eval.py
--------------------
Faithfulness = does the generated answer stick to what the retrieved documents
actually said, or does it drift / hallucinate? It's the metric the deterministic
retrieval harness can't see, because it depends on what the LLM writes, not just
what the retriever pulls.

How it works (RAGAS-style, one extra LLM call per question):
  1. Run the *real* chatbot chain (same retriever, prompt, and Groq model as the
     app) to get an answer and the exact context chunks it was given.
  2. Ask the model, acting as a judge, to break the answer into standalone
     factual claims and mark each one "supported" or "not supported" by that
     context only.
  3. faithfulness = supported claims / total claims.

An "I don't know" answer makes no claims, so it's scored N/A (neither faithful
nor unfaithful) and excluded from the average -- refusing when the context is
thin is correct behaviour, not a faithfulness failure.

This costs Groq API calls (generation + one judge call per question), so unlike
retrieval_eval it is not free to run. It reuses eval/eval_questions.json.

Run:
    uv run python -m eval.faithfulness_eval
    uv run python -m eval.faithfulness_eval --n 3     # only the first 3 questions
"""

import argparse
import json
import re

from langchain_core.output_parsers import StrOutputParser

from src import config
from src.chatbot import format_docs, load_llm, set_custom_prompt
from src.vectorstore import get_vectorstore
from eval.retrieval_eval import load_questions

JUDGE_PROMPT = """You are a strict evaluator checking whether an answer is grounded in a context.

Given the CONTEXT and the ANSWER below, break the ANSWER into standalone factual
claims. For each claim, decide whether it is directly supported by the CONTEXT.
Judge support using ONLY the CONTEXT -- ignore whether the claim is true in the
real world. General filler or hedging ("I don't know", "based on the context")
is not a factual claim; skip it.

Return ONLY a JSON object of this exact shape, nothing else:
{{"claims": [{{"claim": "<text>", "supported": true|false}}]}}

CONTEXT:
{context}

ANSWER:
{answer}
"""


def build_answer_chain(k):
    """A non-cached mirror of the app's chain that also exposes the raw context.

    We don't reuse chatbot.get_chain() because it's wrapped in @st.cache_resource,
    which warns and misbehaves outside `streamlit run`. Same retriever/prompt/LLM,
    so the answer being judged is the one the app would produce.
    """
    retriever = get_vectorstore().as_retriever(search_kwargs={"k": k})
    prompt = set_custom_prompt()
    llm = load_llm()
    answer_chain = prompt | llm | StrOutputParser()
    return retriever, answer_chain


def parse_judge_json(text):
    """Pull the JSON object out of the judge's reply, tolerating stray prose/fences."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def score_answer(judge, context, answer):
    """Return (faithfulness in [0,1] or None, list_of_claim_dicts)."""
    reply = judge.invoke(JUDGE_PROMPT.format(context=context, answer=answer))
    reply_text = getattr(reply, "content", reply)
    parsed = parse_judge_json(reply_text)
    if not parsed or not parsed.get("claims"):
        return None, []  # no checkable claims (e.g. "I don't know")
    claims = parsed["claims"]
    supported = sum(1 for c in claims if c.get("supported") is True)
    return supported / len(claims), claims


def run(k=None, n=None):
    data = load_questions()
    k = k or data.get("k", 8)
    questions = data["questions"]
    if n:
        questions = questions[:n]

    retriever, answer_chain = build_answer_chain(k)
    judge = load_llm()  # same model, temperature already low; used as evaluator

    scores = []
    print(f"\nFaithfulness eval  |  k={k}  |  model={config.GROQ_MODEL}  |  {len(questions)} questions\n" + "=" * 70)

    for item in questions:
        q = item["question"]
        docs = retriever.invoke(q)
        context = format_docs(docs)
        answer = answer_chain.invoke({"context": context, "question": q})
        faith, claims = score_answer(judge, context, answer)

        if faith is None:
            print(f"[ N/A  ] {q}")
            print("          (no factual claims to check -- likely an 'I don't know')")
            continue

        scores.append(faith)
        supported = sum(1 for c in claims if c.get("supported") is True)
        print(f"[{faith:6.0%}] {q}   ({supported}/{len(claims)} claims supported)")
        if faith < 1.0:
            unsupported = "; ".join(
                c.get("claim", "") for c in claims if c.get("supported") is not True
            )
            if unsupported:
                print("          unsupported:", unsupported[:200])

    print("=" * 70)
    if scores:
        mean = sum(scores) / len(scores)
        print(f"faithfulness: {mean:.0%}  (mean over {len(scores)} scored questions)")
        return mean
    print("faithfulness: n/a  (no questions produced checkable claims)")
    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score answer faithfulness with an LLM judge.")
    parser.add_argument("--k", type=int, default=None, help="Override top-k (default: value in eval_questions.json).")
    parser.add_argument("--n", type=int, default=None, help="Only evaluate the first N questions (to save API calls).")
    args = parser.parse_args()
    run(k=args.k, n=args.n)
