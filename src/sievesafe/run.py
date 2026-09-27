"""One screening run, shared by the CLI and the local page: read and check the input, estimate, score, write the outputs.

Safety rules on top of the threshold: a record that was not scored (budget) or has no abstract is never flagged or
excluded (the threshold was validated on records with abstracts only); copies of the same study (same DOI or title) are
scored once, from the copy with the longest abstract, and share its fate."""
from __future__ import annotations

import csv
import random
from dataclasses import dataclass, field
from pathlib import Path

from sievesafe import SAFE_THRESHOLD, jev, records, report

VALIDATION_SAMPLE = 50


@dataclass
class Run:
    source: Path
    title: str
    criteria: str
    mode: str
    out: Path
    export: records.Export | None = None
    recs: list = field(default_factory=list)
    rep: dict = field(default_factory=dict)  # record index → index of the copy that is scored for it
    cache: jev.Cache | None = None
    todo: list = field(default_factory=list)
    estimate: float = 0.0

    @property
    def fmt(self) -> str:
        return self.export.fmt if self.export else ""

    @property
    def no_abstract(self) -> int:
        return sum(1 for r in self.recs if not r.abstract)

    @property
    def duplicates(self) -> int:
        return sum(1 for i, j in self.rep.items() if i != j)


def prepare(source: Path, title: str, criteria: str, mode: str, out: Path) -> Run:
    """Read and validate; raises ValueError with a message meant for the user."""
    if mode not in ("rank", "exclude"):
        raise ValueError(f"unknown mode {mode!r}: use rank or exclude")
    title, criteria = title.strip(), criteria.strip()
    if not title:
        raise ValueError("give the review's title")
    if len(criteria) < 40:
        raise ValueError("the criteria look empty; paste the review's inclusion and exclusion criteria")
    export, recs = records.read(source)
    if not recs:
        raise ValueError(f"{source.name}: no records found")
    run = Run(source, title, criteria, mode, out, export, recs)
    first = records.duplicate_of(recs)
    groups: dict[int, list] = {}
    for r in recs:
        groups.setdefault(first.get(r.index, r.index), []).append(r)
    for members in groups.values():
        best = max(members, key=lambda r: (len(r.abstract), -r.index))
        run.rep.update({r.index: best.index for r in members})
    run.cache = jev.Cache(out / ".sievesafe-cache.tsv", criteria)
    run.todo = [r for r in recs if run.rep[r.index] == r.index and run.cache.get(r) is None]
    run.estimate = jev.estimate_tokens(title, criteria, run.todo) * jev.PRICE_PER_TOKEN
    return run


def execute(run: Run, key: str, budget: float, progress=lambda done, total: None) -> dict:
    """Score what is not cached (up to `budget` USD), write the outputs into run.out; → summary with the file names."""
    recs, out, suffix = run.recs, run.out, run.export.suffix
    reps = [r for r in recs if run.rep[r.index] == r.index]
    if run.todo:
        scores, spent = jev.score(reps, run.title, run.criteria, run.cache, key, budget, progress=progress)
    else:
        scores, spent = {r.index: run.cache.get(r) for r in reps}, 0.0
    scores = {r.index: scores[run.rep[r.index]] for r in recs if run.rep[r.index] in scores}
    has_abstract = {r.index: bool(recs[run.rep[r.index]].abstract) for r in recs}
    scored = [r for r in recs if r.index in scores]
    ordered = sorted(recs, key=lambda r: -scores.get(r.index, 1.0))  # unscored records go first: never hidden
    low = [r for r in scored if scores[r.index] < SAFE_THRESHOLD and has_abstract[r.index]]
    excluded = low if run.mode == "exclude" else []
    gone = {r.index for r in excluded}
    keep = [r for r in ordered if r.index not in gone]

    out.mkdir(parents=True, exist_ok=True)
    with (out / "ranked.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "record", "probability", "flag", "duplicate_of", "title"])
        for i, r in enumerate(ordered, 1):
            prob = scores.get(r.index)
            if prob is None:
                flag = "not scored"
            elif prob >= SAFE_THRESHOLD:
                flag = ""
            elif not has_abstract[r.index]:
                flag = "no abstract, kept"
            else:
                flag = "excluded" if r.index in gone else "below safe threshold"
            dup = run.rep[r.index] + 1 if run.rep[r.index] != r.index else ""
            w.writerow([i, r.index + 1, "" if prob is None else f"{prob:.4f}", flag, dup, r.title])
    files = ["ranked.csv", f"to-screen{suffix}"]
    records.write(out / f"to-screen{suffix}", run.export, keep)
    if run.mode == "exclude":
        records.write(out / f"excluded{suffix}", run.export, excluded)
        sample = random.Random(0).sample(excluded, min(VALIDATION_SAMPLE, len(excluded)))
        records.write(out / f"validation-sample{suffix}", run.export, sorted(sample, key=lambda r: r.index))
        files += [f"excluded{suffix}", f"validation-sample{suffix}"]
    (out / "report.md").write_text(report.build(
        source=run.source.name, title=run.title, criteria=run.criteria, mode=run.mode, n_total=len(recs), n_scored=len(scored),
        n_excluded=len(excluded), n_low=len(low), spent=spent, n_no_abstract=run.no_abstract, n_duplicates=run.duplicates,
        n_sample=min(VALIDATION_SAMPLE, len(excluded))), encoding="utf-8")
    files.append("report.md")
    return {"total": len(recs), "scored": len(scored), "below_threshold": len(low), "excluded": len(excluded), "spent": spent,
            "no_abstract": run.no_abstract, "duplicates": run.duplicates, "files": files}
