"""Shared by the benchmark scripts: SYNERGY+ data, cached Jev answers, the train/test split and the metrics.

Data: SYNERGY+ v3 CSVs in benchmark/data/ (or $SYNERGY_DATA), one per review plus metadata/review_metadata.csv.
Answers: answers/<variant>-<review>.jsonl.gz (committed) and .jsonl (new, uncommitted runs), one Jev call per line:
{"scores": {openalex_id: {"overall": p}}, "ms": ..., "usage": {"input_tokens": ...}, "n": 1}.
Variants: f1 = every record of the 23 test reviews; c1 = the 20 train reviews, capped at 1,000 records each."""
from __future__ import annotations

import csv
import datetime
import gzip
import hashlib
import json
import math
import os
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ANSWERS = HERE / "answers"
DATA = Path(os.environ.get("SYNERGY_DATA", HERE / "data")).expanduser()
CALIBRATION = HERE / "calibration.json"
MANIFEST = HERE / "data-manifest.json"
TEST, TRAIN, TRAIN_CAP = "f1", "c1", 1000
PRICE_PER_TOKEN = 0.042 / 1e6
csv.field_size_limit(10**8)
sys.path.insert(0, str(HERE.parent / "src"))


def meta() -> dict[str, dict]:
    path = DATA / "metadata/review_metadata.csv"
    if not path.exists():
        sys.exit(f"SYNERGY+ data not found in {DATA}: see benchmark/README.md (or set SYNERGY_DATA)")
    with path.open(encoding="utf-8") as f:
        return {r["key"]: r for r in csv.DictReader(f)}


def test_keys() -> list[str]:
    return sorted(k for k, r in meta().items() if r["split"] == "test")


def train_keys() -> list[str]:
    return json.loads(CALIBRATION.read_text())["train_reviews"]


def label(v: str | None) -> int | None:
    return None if v in (None, "") else int(float(v))


def records(key: str) -> list[dict]:
    """Every record of a review in file order: id, title, abstract, y (final label), ya (title/abstract label or None)."""
    with (DATA / f"{key}.csv").open(encoding="utf-8") as f:
        return [{"id": r["openalex_id"], "title": (r["title"] or "").strip(), "abstract": (r["abstract"] or "").strip(),
                 "y": label(r["label_included"]) or 0, "ya": label(r.get("label_abstract_included"))} for r in csv.DictReader(f)]


def capped(recs: list[dict], cap: int) -> list[dict]:
    """Every include plus a seeded sample of excludes; each sampled exclude weighs (excludes / sampled)."""
    recs = [{**r, "w": 1.0} for r in recs]
    if not cap or len(recs) <= cap:
        return recs
    inc, exc = [r for r in recs if r["y"]], [r for r in recs if not r["y"]]
    keep = random.Random(0).sample(exc, max(cap - len(inc), 1))
    for r in keep:
        r["w"] = len(exc) / len(keep)
    return inc + keep


def answer_files(variant: str, key: str = "*") -> list[Path]:
    return sorted([*ANSWERS.glob(f"{variant}-{key}.jsonl.gz"), *ANSWERS.glob(f"{variant}-{key}.jsonl")])


def read_lines(path: Path) -> list[str]:
    return (gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()).decode().splitlines()


def calls(variant: str, key: str = "*") -> list[dict]:
    return [json.loads(line) for f in answer_files(variant, key) for line in read_lines(f)]


def answers(variant: str, key: str) -> dict[str, float]:
    return {i: s["overall"] for c in calls(variant, key) for i, s in c["scores"].items()}


def answers_sha(variant: str) -> str:
    """SHA-256 of the answers as first written (the lab's plain .jsonl bytes, file by file in name order)."""
    h = hashlib.sha256()
    for f in answer_files(variant):
        h.update(gzip.decompress(f.read_bytes()) if f.suffix == ".gz" else f.read_bytes())
    return h.hexdigest()


def spent(variant: str) -> float:
    return sum(c["usage"]["input_tokens"] for c in calls(variant)) * PRICE_PER_TOKEN


def scored(variant: str, key: str, cap: int = 0) -> list[dict]:
    """Records of `key` that have an answer, with s (score) and w (weight), in file order."""
    s = answers(variant, key)
    return [{**r, "s": s[r["id"]]} for r in capped(records(key), cap) if r["id"] in s]


def calibrate(as_frozen: bool = False) -> dict:
    """Thresholds for 95/98/100% pooled train recall (see calibrate.py). as_frozen: the frozen run's id-pooled score lookup."""
    keys = sorted({f.name.split("-", 1)[1].split(".jsonl")[0] for f in answer_files(TRAIN)})
    pooled = {i: s for k in keys for i, s in answers(TRAIN, k).items()}  # later review wins, as in the frozen run
    rows = [{**r, "review": k, **({"s": pooled[r["id"]]} if as_frozen else {})} for k in keys for r in scored(TRAIN, k, TRAIN_CAP)]
    P, W = sum(r["y"] for r in rows), sum(r["w"] for r in rows)
    candidates = sorted({round(r["s"], 4) for r in rows if r["y"]} | {0.0})
    result = {"variant": TRAIN, "frozen_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
              "answers_sha256": answers_sha(TRAIN), "train_reviews": keys, "records": len(rows), "includes": P, "targets": {}}
    for target in (0.95, 0.98, 1.0):
        best = max(t for t in candidates if sum(r["y"] for r in rows if r["s"] >= t) / P >= target)
        result["targets"][f"{target:.0%}"] = {"threshold": best, "train_recall": sum(r["y"] for r in rows if r["s"] >= best) / P,
                                               "train_auto_excluded": 1 - sum(r["w"] for r in rows if r["s"] >= best) / W}
    result["id_pooling_changed"] = {"records": sum(r["s"] != pooled[r["id"]] for r in rows),
                                    "includes": sum(r["y"] for r in rows if r["s"] != pooled[r["id"]])}
    return result


def threshold(pairs: list[tuple[float, int]], target: float) -> float:
    """Highest include score t such that the share of includes scoring ≥ t still meets `target` (0.0 if none)."""
    P, found, best = sum(y for _, y in pairs), 0, 0.0
    by_score: dict[float, int] = {}
    for s, y in pairs:
        by_score[s] = by_score.get(s, 0) + y
    for s in sorted(by_score, reverse=True):
        found += by_score[s]
        if by_score[s] and found / P >= target:
            return s
    return best


def auc(s: list[float], y: list[int]) -> float:
    pos = [a for a, b in zip(s, y) if b]
    neg = [a for a, b in zip(s, y) if not b]
    if not pos or not neg:
        return float("nan")
    return sum((p > n) + 0.5 * (p == n) for p in pos for n in neg) / (len(pos) * len(neg))


def wss(labels_in_order: list[int], n_total: int, n_inc: int, target: float) -> float:
    """Work saved over sampling: share of records NOT read when `target` of the includes are found, minus (1 − target)."""
    need, found = math.ceil(target * n_inc), 0
    for k, y in enumerate(labels_in_order, 1):
        found += y
        if found >= need:
            return (n_total - k) / n_total - (1 - target)
    return float("nan")


def ranked(rows: list[dict], label_key: str = "y") -> list[int]:
    """Labels in descending score order; among equal scores the includes come last (the pessimistic reading order)."""
    return [r[label_key] for r in sorted(rows, key=lambda r: (-r["s"], r[label_key]))]


def cp_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """Clopper–Pearson one-sided upper bound for k failures in n."""
    lo, hi = k / n, 1.0
    for _ in range(60):
        p = (lo + hi) / 2
        tail = sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))
        lo, hi = (p, hi) if tail > alpha else (lo, p)
    return hi


def knee_stop(labels: list[int], min_read: int = 150, ratio: float = 6.0, margin: float = 0.1) -> int:
    """Records read when the knee method (Cormack & Grossman 2016) stops, with a 10% margin; len(labels) if it never does."""
    cum, found = [], 0
    for y in labels:
        found += y
        cum.append(found)
    for s in range(min_read, len(labels) + 1):
        rel_s = cum[s - 1]
        best_i, best_d = 1, -1.0
        for i in range(1, s + 1):
            d = cum[i - 1] * s - i * rel_s
            if d > best_d:
                best_i, best_d = i, d
        rel_i = cum[best_i - 1]
        if rel_s >= 1 and (rel_i / best_i) / ((rel_s - rel_i + 1) / max(s - best_i, 1)) >= ratio:
            return min(len(labels), int(s * (1 + margin)))
    return len(labels)
