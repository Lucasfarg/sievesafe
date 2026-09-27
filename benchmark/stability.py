#!/usr/bin/env python3
"""Run-to-run stability with the model pinned: re-ask a seeded sample of test records and compare with the f1 answers.

  stability.py [--n 2000] [--budget 0.15]

Same question and state as screen.py, model sievesafe.MODEL (jev-1.13.0). The sample is random.Random(1).sample over
every answered test record (reviews in name order, records in file order). Writes answers/stability-<model>.jsonl
({"old", "new", "model", "usage"} per record); results.md reports correlation and threshold crossings. Costs ~US$ 0.10."""
import argparse
import concurrent.futures as cf
import json
import random
import threading

import common

from sievesafe import MODEL, jev

p = argparse.ArgumentParser()
p.add_argument("--n", type=int, default=2000)
p.add_argument("--budget", type=float, default=0.15)
a = p.parse_args()
meta = common.meta()
pool = [(k, r) for k in common.test_keys() for r in common.scored(common.TEST, k)]
sample = random.Random(1).sample(pool, a.n)
key, spent, lock = jev.api_key(), 0.0, threading.Lock()


def one(item):
    global spent
    k, r = item
    with lock:
        if spent + 6 * 3000 * common.PRICE_PER_TOKEN >= a.budget:
            return None
    state = {"review": {"title": meta[k]["title"], "eligibility_criteria": meta[k]["eligibility_criteria"]},
             "record": {"title": r["title"], "abstract": r["abstract"] or "(no abstract available)"}}
    prob, tokens = jev.ask(state, key)
    with lock:
        spent += tokens * common.PRICE_PER_TOKEN
    return {"old": r["s"], "new": prob, "model": MODEL, "usage": {"input_tokens": tokens}}


with cf.ThreadPoolExecutor(6) as ex:
    got = [g for g in ex.map(one, sample) if g]
(common.ANSWERS / f"stability-{MODEL}.jsonl").write_text("\n".join(json.dumps(g) for g in got))
print(f"{len(got)}/{a.n} records re-asked, US$ {spent:.3f} → answers/stability-{MODEL}.jsonl")
