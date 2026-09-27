"""TypeSafe Jev client: one yes/no question per record, cached, with a cost estimate and a hard budget."""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from sievesafe import MODEL
from sievesafe.records import Record

API = "https://api.typesafe.ai/v1/systemone"
PRICE_PER_TOKEN = 0.042 / 1e6  # USD, input only (https://docs.typesafe.ai/models)
# Fitted on 33,001 SYNERGY+ calls: tokens ≈ chars / 4.92 + 503 per record (chars = criteria + review title + record text),
# worst review under-estimated by 145 tokens. The estimate uses a conservative 4.5 chars/token + 650 so it errs high.
CHARS_PER_TOKEN, OVERHEAD_TOKENS = 4.5, 650
POLICY = ("Title/abstract screening stage: a record moves on to full-text review when it could meet every inclusion "
          "criterion, including when the title and abstract do not give enough information to tell. Exclude only "
          "when the record clearly fails a criterion. Missing a relevant study is far worse than reading an extra one.")
FOCUS = "`review` describes a systematic review and its eligibility criteria; each record is one search result (title and abstract)."
QUESTION = {"overall": {
    "type": "noul",
    "instructions": {"question": "Should `record` move on to full-text review for `review`?", "focus": FOCUS, "policy": POLICY},
    "criteria": {"true": "It could meet every inclusion criterion and clearly meets no exclusion criterion, or the abstract does not say enough to rule it out.",
                 "false": "It clearly fails at least one inclusion criterion, or clearly meets an exclusion criterion."}}}


class JevError(Exception):
    pass


def api_key(key_file: Path | None = None) -> str:
    if key := os.environ.get("TYPESAFE_API_KEY"):
        return key
    for path in filter(None, [key_file, Path.home() / ".config/sievesafe/typesafe.env"]):
        path = Path(path).expanduser()
        if path.exists():
            for line in path.read_text().splitlines():
                if m := re.match(r"\s*(?:export\s+)?TYPESAFE_API_KEY=(.*)", line):
                    return m.group(1).strip().strip("\"'")
    raise JevError("no API key: set TYPESAFE_API_KEY or put TYPESAFE_API_KEY=... in ~/.config/sievesafe/typesafe.env")


def estimate_tokens(title: str, criteria: str, records: list[Record]) -> int:
    return sum(int((len(title) + len(criteria) + len(r.title) + len(r.abstract)) / CHARS_PER_TOKEN) + OVERHEAD_TOKENS for r in records)


class Cache:
    """answers keyed by (model, criteria, record text), so a rerun or an edited file costs only the new records."""

    def __init__(self, path: Path, criteria: str):
        self.path, self.lock = path, threading.Lock()
        self.prefix = f"{MODEL}:{hash_text(criteria)}:"
        self.data: dict[str, float] = {}
        if path.exists():
            for line in path.read_text().splitlines():
                k, v = line.rsplit("\t", 1)
                self.data[k] = float(v)

    def get(self, r: Record) -> float | None:
        return self.data.get(self.prefix + r.key)

    def put(self, r: Record, score: float) -> None:
        with self.lock:
            self.data[self.prefix + r.key] = score
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a") as f:
                f.write(f"{self.prefix}{r.key}\t{score}\n")


def hash_text(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def ask(state: dict, key: str, timeout: float = 60, retries: int = 5) -> tuple[float, int]:
    """→ (probability of yes, input tokens). Retries 429/5xx and network errors with backoff."""
    body = json.dumps({"model": MODEL, "state": state, "questions": QUESTION}).encode()
    req = urllib.request.Request(API, data=body, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.load(resp)
            try:
                return float(data["answers"]["overall"]["noul"]), int(data.get("usage", {}).get("input_tokens", 0))
            except (KeyError, TypeError, ValueError) as e:
                raise JevError(f"unexpected answer from Jev: {str(data)[:200]}") from e
        except urllib.error.HTTPError as e:
            if (e.code == 429 or e.code >= 500) and attempt < retries:
                time.sleep(float(e.headers.get("Retry-After") or 2 ** attempt))
                continue
            raise JevError(f"Jev answered {e.code}: {e.read().decode(errors='replace')[:200]}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise JevError(f"Jev unreachable: {getattr(e, 'reason', e)}") from e
    raise JevError("Jev unreachable")


def score(records: list[Record], title: str, criteria: str, cache: Cache, key: str, budget: float, workers: int = 6,
          progress=lambda done, total: None) -> tuple[dict[int, float], float]:
    """→ ({record index: probability}, spent USD). A call is only sent if the spend so far, the estimated cost of the calls
    in flight and its own estimated cost (estimate_tokens errs high) fit in `budget`; unscored records are left out."""
    review = {"title": title, "eligibility_criteria": criteria}
    scores = {r.index: s for r in records if (s := cache.get(r)) is not None}
    todo = [r for r in records if r.index not in scores]
    spent, reserved, lock = 0.0, 0.0, threading.Lock()

    def one(r: Record):
        nonlocal spent, reserved
        cost = estimate_tokens(title, criteria, [r]) * PRICE_PER_TOKEN
        with lock:
            if spent + reserved + cost > budget:
                return None
            reserved += cost
        try:
            p, tokens = ask({"review": review, "record": {"title": r.title, "abstract": r.abstract or "(no abstract available)"}}, key)
        finally:
            with lock:
                reserved -= cost
        cache.put(r, p)
        with lock:
            spent += tokens * PRICE_PER_TOKEN
        return r.index, p

    with cf.ThreadPoolExecutor(workers) as pool:  # Jev allows 1,200 requests/min
        for i, got in enumerate(pool.map(one, todo), 1):
            if got:
                scores[got[0]] = got[1]
            progress(i, len(todo))
    return scores, spent
