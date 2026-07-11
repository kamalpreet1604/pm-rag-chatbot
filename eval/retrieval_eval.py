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

Metrics (all source-based, no LLM):
  - hit@k     : fraction of questions where an expected source appeared in top-k.
  - MRR       : mean reciprocal rank of the first expected source (0 if missed);
                rewards ranking the right source higher, not just including it.
  - precision@k: of the k chunks pulled, the fraction whose source is an
                expected one -- "how much of what we retrieved was on-topic".
                It's a source-level proxy (a chunk counts as relevant if its
                file is a relevant file), not a per-chunk human judgement.
  - recall    : of the sources that SHOULD all be retrieved (`expect_all` on a
                question), the fraction actually retrieved -- "did we find all
                the needed info". Only computed for questions that declare
                `expect_all`; questions with only `expect_any` are skipped for
                recall, since "any one acceptable source" gives no full target.

Faithfulness (does the answer stick to the retrieved docs?) is the one metric
that needs the LLM, so it lives in eval/faithfulness_eval.py, not here.

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


def precision_at_k(sources, expected):
    """Fraction of retrieved chunks whose source matches any expected substring."""
    if not sources:
        return 0.0
    expected_lower = [e.lower() for e in expected]
    relevant = sum(
        1 for src in sources if any(e in (src or "").lower() for e in expected_lower)
    )
    return relevant / len(sources)


def recall(sources, expect_all):
    """Fraction of the required sources (`expect_all`) that were retrieved.

    Each entry in expect_all is a substring that must appear in at least one
    retrieved source. Returns None when expect_all is empty (recall undefined).
    """
    if not expect_all:
        return None
    joined = " ".join((s or "").lower() for s in sources)
    found = sum(1 for want in expect_all if want.lower() in joined)
    return found / len(expect_all)


def run(k=None):
    data = load_questions()
    k = k or data.get("k", 8)
    questions = data["questions"]

    retriever = get_vectorstore().as_retriever(search_kwargs={"k": k})

    hits = 0
    reciprocal_ranks = []
    precisions = []
    recalls = []  # only appended for questions that declare expect_all
    print(f"\nRetrieval eval  |  k={k}  |  {len(questions)} questions\n" + "=" * 70)

    for item in questions:
        q = item["question"]
        expected = item["expect_any"]
        expect_all = item.get("expect_all", [])
        docs = retriever.invoke(q)
        sources = [d.metadata.get("source", "") for d in docs]
        rank = first_hit_rank(sources, expected)
        prec = precision_at_k(sources, expected)
        rec = recall(sources, expect_all)
        precisions.append(prec)
        if rec is not None:
            recalls.append(rec)

        if rank is not None:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
            status = f"HIT  @{rank}"
        else:
            reciprocal_ranks.append(0.0)
            status = "MISS   "

        rec_str = f"  rec={rec:.0%}" if rec is not None else ""
        print(f"[{status}] P@{k}={prec:.0%}{rec_str}  {q}")
        if rank is None:
            # Show what came back so a miss is diagnosable, not mysterious.
            shown = [os.path.basename(s) if s and not s.startswith("http") else s for s in sources[:5]]
            print("          expected any of:", expected)
            print("          got:", shown)

    n = len(questions)
    hit_rate = hits / n if n else 0.0
    mrr = sum(reciprocal_ranks) / n if n else 0.0
    mean_prec = sum(precisions) / n if n else 0.0
    mean_recall = sum(recalls) / len(recalls) if recalls else None
    print("=" * 70)
    print(f"hit@{k}: {hits}/{n} = {hit_rate:.0%}    MRR: {mrr:.3f}    precision@{k}: {mean_prec:.0%}")
    if mean_recall is not None:
        print(f"recall: {mean_recall:.0%}  (over {len(recalls)}/{n} questions with expect_all)")
    else:
        print("recall: n/a  (no questions declare expect_all -- add it to measure recall)")
    return {"hit_rate": hit_rate, "mrr": mrr, "precision": mean_prec, "recall": mean_recall}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Score retrieval against the eval set.")
    parser.add_argument("--k", type=int, default=None, help="Override top-k (default: value in eval_questions.json).")
    args = parser.parse_args()
    run(k=args.k)
