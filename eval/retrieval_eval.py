"""
retrieval_eval.py
-----------------
Scores the retriever against a fixed question -> expected-source test set, so
retrieval regressions (from changing k, chunk size, pruning URLs, re-embedding,
etc.) show up as a number instead of a vibe.

It does NOT call the LLM -- it only checks what the retriever pulls back, which
is the part most affected by ingestion/config changes and is cheap+deterministic.

For each question it retrieves the top-k chunks and checks whether any of the
`expect_any` substrings appears in a retrieved chunk's `source` metadata.

Metrics:
  - hit@k   : fraction of questions where an expected source appeared in top-k.
  - MRR     : mean reciprocal rank of the first expected source (0 if missed);
              rewards ranking the right source higher, not just including it.

Run:
    uv run python -m eval.retrieval_eval
    uv run python -m eval.retrieval_eval --k 4     # override k for a comparison
"""

import argparse
import json
import os

from src.vectorstore import get_vectorstore

HERE = os.path.dirname(os.path.abspath(__file__))
QUESTIONS_FILE = os.path.join(HERE, "eval_questions.json")


def load_questions():
    with open(QUESTIONS_FILE, encoding="utf-8") as f:
        return json.load(f)


def first_hit_rank(sources, expected):
    """1-based rank of the first retrieved source matching any expected substring, else None."""
    expected_lower = [e.lower() for e in expected]
    for rank, src in enumerate(sources, start=1):
        s = (src or "").lower()
        if any(e in s for e in expected_lower):
            return rank
    return None


def run(k=None):
    data = load_questions()
    k = k or data.get("k", 8)
    questions = data["questions"]

    retriever = get_vectorstore().as_retriever(search_kwargs={"k": k})

    hits = 0
    reciprocal_ranks = []
    print(f"\nRetrieval eval  |  k={k}  |  {len(questions)} questions\n" + "=" * 70)

    for item in questions:
        q = item["question"]
        expected = item["expect_any"]
        docs = retriever.invoke(q)
        sources = [d.metadata.get("source", "") for d in docs]
        rank = first_hit_rank(sources, expected)

        if rank is not None:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
            status = f"HIT  @{rank}"
        else:
            reciprocal_ranks.append(0.0)
            status = "MISS   "

        print(f"[{status}] {q}")
        if rank is None:
            # Show what came back so a miss is diagnosable, not mysterious.
            shown = [os.path.basename(s) if s and not s.startswith("http") else s for s in sources[:5]]
            print("          expected any of:", expected)
            print("          got:", shown)

    n = len(questions)
    hit_rate = hits / n if n else 0.0
    mrr = sum(reciprocal_ranks) / n if n else 0.0
    print("=" * 70)
    print(f"hit@{k}: {hits}/{n} = {hit_rate:.0%}    MRR: {mrr:.3f}")
    return hit_rate, mrr


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score retrieval against the eval set.")
    parser.add_argument("--k", type=int, default=None, help="Override top-k (default: value in eval_questions.json).")
    args = parser.parse_args()
    run(k=args.k)
