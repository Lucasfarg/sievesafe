#!/usr/bin/env python3
"""Ask Jev about every record of SYNERGY+ reviews that has no cached answer yet (the only benchmark step that spends).

  screen.py <variant> test|train|<review>... [--cap N] [--budget USD]

Same question, state and model as `sievesafe screen` (sievesafe.jev): one call per record, the review's title and its
SYNERGY+ `eligibility_criteria` as the review, the record's title and abstract. New answers are appended to
answers/<variant>-<review>.jsonl. --budget (default 0.50) caps this variant's total spend across all its answer files,
committed ones included; it stops before a call could cross it. Reproducing f1 + c1 from scratch costs about US$ 2.20:
    screen.py f1 test --budget 1.60            screen.py c1 train --cap 1000 --budget 0.65
The committed f1/c1 answers were asked with model jev-latest in September 2026, when it resolved to jev-1.13.0
(see stability.py for the run-to-run check against the pinned id)."""
import argparse
import concurrent.futures as cf
import json
import sys
import threading
import time

import common

from sievesafe import jev

p = argparse.ArgumentParser()
p.add_argument("variant")
p.add_argument("reviews", nargs="+")
p.add_argument("--cap", type=int, default=0)
p.add_argument("--budget", type=float, default=0.50)
a = p.parse_args()
meta = common.meta()
keys = common.test_keys() if a.reviews == ["test"] else common.train_keys() if a.reviews == ["train"] else a.reviews
spent, lock = common.spent(a.variant), threading.Lock()
key = jev.api_key()
MARGIN = 6 * 3000 * common.PRICE_PER_TOKEN  # six calls in flight, each well under 3,000 tokens


def one(review: dict, r: dict) -> dict | None:
    global spent
    with lock:
        if spent + MARGIN >= a.budget:
            return None
    t = time.time()
    prob, tokens = jev.ask({"review": review, "record": {"title": r["title"], "abstract": r["abstract"] or "(no abstract available)"}}, key)
    with lock:
        spent += tokens * common.PRICE_PER_TOKEN
    return {"scores": {r["id"]: {"overall": prob}}, "ms": int((time.time() - t) * 1000), "usage": {"input_tokens": tokens}, "n": 1}


for k in keys:
    done = common.answers(a.variant, k)
    todo = [r for r in common.capped(common.records(k), a.cap) if r["id"] not in done]
    review = {"title": meta[k]["title"], "eligibility_criteria": meta[k]["eligibility_criteria"]}
    with cf.ThreadPoolExecutor(6) as pool, (common.ANSWERS / f"{a.variant}-{k}.jsonl").open("a") as f:  # Jev allows 1,200 requests/min
        got = 0
        for res in pool.map(one, [review] * len(todo), todo):
            if res:
                f.write(json.dumps(res) + "\n")
                got += 1
    print(f"{k}: {got}/{len(todo)} new answers; variant {a.variant} spend US$ {spent:.3f}", file=sys.stderr)
    if spent + MARGIN >= a.budget:
        sys.exit(f"budget reached (US$ {spent:.3f} of {a.budget:.2f}); rerun with a higher --budget to continue")
