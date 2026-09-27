#!/usr/bin/env python3
"""Ask Jev about every record of the CLEF TAR 2019 set built by clef_fetch.py (the only external step that spends).

  screen.py [--condition full|objectives|dta|dta1718] [--budget USD]

Same question, state and pinned model as `sievesafe screen`. Answers are appended to benchmark/answers/clef-<topic>.jsonl;
--budget caps the total spend of all clef answers, committed ones included, and stops before a call could cross it."""
import argparse
import concurrent.futures as cf
import json
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import clef
import common

from sievesafe import jev

p = argparse.ArgumentParser()
p.add_argument("--condition", choices=list(clef.CONDITIONS), default="full")
p.add_argument("--budget", type=float, default=0.95)
a = p.parse_args()
VARIANT = clef.CONDITIONS[a.condition]["variant"]
reviews = clef.reviews(a.condition)["reviews"]
spent, lock = common.spent(VARIANT), threading.Lock()
key = jev.api_key()
MARGIN = 6 * 3000 * common.PRICE_PER_TOKEN


def one(review: dict, r: dict) -> dict | None:
    global spent
    with lock:
        if spent + MARGIN >= a.budget:
            return None
    t = time.time()
    prob, tokens = jev.ask({"review": review, "record": {"title": r["title"], "abstract": r["abstract"] or "(no abstract available)"}}, key)
    with lock:
        spent += tokens * common.PRICE_PER_TOKEN
    return {"scores": {r["pmid"]: {"overall": prob}}, "ms": int((time.time() - t) * 1000), "usage": {"input_tokens": tokens}, "n": 1}


for topic, meta in reviews.items():
    done = common.answers(VARIANT, topic)
    todo = [r for r in clef.rows(topic, meta, a.condition) if r["pmid"] not in done and (r["title"] or r["abstract"])]  # not in PubMed: nothing to ask
    review = {"title": meta["title"], "eligibility_criteria": clef.criteria(meta, a.condition)}
    with cf.ThreadPoolExecutor(6) as pool, (common.ANSWERS / f"{VARIANT}-{topic}.jsonl").open("a") as f:
        got = 0
        for res in pool.map(one, [review] * len(todo), todo):
            if res:
                f.write(json.dumps(res) + "\n")
                got += 1
    print(f"{topic}: {got}/{len(todo)} new answers; {VARIANT} spend US$ {spent:.3f}", file=sys.stderr, flush=True)
    if spent + MARGIN >= a.budget:
        sys.exit(f"budget reached (US$ {spent:.3f} of {a.budget:.2f})")
