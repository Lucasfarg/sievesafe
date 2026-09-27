"""One screening run, shared by the CLI and the local page: read and check the input, estimate, score, write the outputs."""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from sievesafe import SAFE_THRESHOLD, jev, records, report


@dataclass
class Run:
    source: Path
    title: str
    criteria: str
    mode: str
    out: Path
    fmt: str = ""
    recs: list = field(default_factory=list)
    cache: jev.Cache | None = None
    todo: list = field(default_factory=list)
    estimate: float = 0.0

    @property
    def no_abstract(self) -> int:
        return sum(1 for r in self.recs if not r.abstract)


def prepare(source: Path, title: str, criteria: str, mode: str, out: Path) -> Run:
    """Read and validate; raises ValueError with a message meant for the user."""
    if mode not in ("rank", "exclude"):
        raise ValueError(f"unknown mode {mode!r}: use rank or exclude")
    title, criteria = title.strip(), criteria.strip()
    if not title:
        raise ValueError("give the review's title")
    if len(criteria) < 40:
        raise ValueError("the criteria look empty; paste the review's inclusion and exclusion criteria")
    fmt, recs = records.read(source)
    if not recs:
        raise ValueError(f"{source.name}: no records found")
    run = Run(source, title, criteria, mode, out, fmt, recs)
    run.cache = jev.Cache(out / ".sievesafe-cache.tsv", criteria)
    run.todo = [r for r in recs if run.cache.get(r) is None]
    run.estimate = jev.estimate_tokens(title, criteria, run.todo) * jev.PRICE_PER_TOKEN
    return run


def execute(run: Run, key: str, budget: float, progress=lambda done, total: None) -> dict:
    """Score what is not cached (up to `budget` USD), write the outputs into run.out; → summary with the file names."""
    if run.todo:
        scores, spent = jev.score(run.recs, run.title, run.criteria, run.cache, key, budget, progress=progress)
    else:
        scores, spent = {r.index: run.cache.get(r) for r in run.recs}, 0.0
    recs, fmt, out = run.recs, run.fmt, run.out
    scored = [r for r in recs if r.index in scores]
    ordered = sorted(recs, key=lambda r: -scores.get(r.index, 1.0))  # unscored records go first: never hidden
    low = [r for r in scored if scores[r.index] < SAFE_THRESHOLD]
    excluded = low if run.mode == "exclude" else []
    keep = [r for r in ordered if r not in excluded]

    out.mkdir(parents=True, exist_ok=True)
    with (out / "ranked.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "probability", "flag", "title"])
        for i, r in enumerate(ordered, 1):
            prob = scores.get(r.index)
            flag = "not scored" if prob is None else ("below safe threshold" if prob < SAFE_THRESHOLD else "")
            w.writerow([i, "" if prob is None else f"{prob:.4f}", flag, r.title])
    files = ["ranked.csv", f"to-screen.{fmt}"]
    records.write(out / f"to-screen.{fmt}", fmt, keep)
    if run.mode == "exclude":
        records.write(out / f"excluded.{fmt}", fmt, excluded)
        files.append(f"excluded.{fmt}")
    (out / "report.md").write_text(report.build(source=run.source.name, title=run.title, criteria=run.criteria, mode=run.mode,
                                                n_total=len(recs), n_scored=len(scored), n_excluded=len(excluded), n_low=len(low),
                                                spent=spent), encoding="utf-8")
    files.append("report.md")
    return {"total": len(recs), "scored": len(scored), "below_threshold": len(low), "excluded": len(excluded), "spent": spent, "files": files}
