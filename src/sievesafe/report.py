"""The report a reviewer can paste into their methods and PRISMA flow diagram (RAISE / PRISMA 2020 reporting)."""
from __future__ import annotations

import datetime
from importlib import resources

from sievesafe import MODEL, SAFE_THRESHOLD, __version__

# written by benchmark/results.py from the benchmark, like the numbers in the README
EVIDENCE = resources.files("sievesafe").joinpath("evidence.txt").read_text(encoding="utf-8").strip()


def build(*, source: str, title: str, criteria: str, mode: str, n_total: int, n_scored: int, n_excluded: int,
          n_low: int, spent: float, n_no_abstract: int = 0, n_duplicates: int = 0, n_sample: int = 0) -> str:
    today = datetime.datetime.now(datetime.UTC).astimezone().date().isoformat()
    lines = [
        f"# sievesafe report — {title}",
        "",
        f"- Date: {today} · sievesafe {__version__} · model {MODEL} · threshold {SAFE_THRESHOLD}",
        f"- Input: `{source}` — {n_total} records, {n_scored} scored"
        + (f", {n_total - n_scored} not scored (budget) and kept" if n_scored < n_total else ""),
        f"- Mode: **{mode}** — " + ("records below the threshold were removed before human screening."
                                    if mode == "exclude" else "nothing was removed; records are ordered by probability and low ones flagged."),
        f"- Below the threshold: {n_low} records ({n_low / max(n_total, 1):.0%})" + (f" — **{n_excluded} excluded by automation**" if mode == "exclude" else ""),
        f"- Without an abstract: {n_no_abstract} records — never flagged or excluded (the threshold was validated on records with abstracts)",
        f"- Duplicates (same DOI or title as another record): {n_duplicates} — each study scored once; every copy kept in the files",
        f"- Cost: US$ {spent:.4f}",
        "",
        "## PRISMA 2020 flow diagram",
        "",
        f"Records marked as ineligible by automation tools: **{n_excluded}**" if mode == "exclude"
        else "No records were marked as ineligible by automation tools (sievesafe used for prioritisation only).",
        "",
        "## Methods paragraph (edit before use)",
        "",
        (f"Title and abstract screening was supported by sievesafe {__version__} (model {MODEL}), which estimates for each record "
         f"the probability that it should proceed to full-text review given the review's eligibility criteria, without training "
         f"on labelled records. " + (f"Records with a probability below the pre-specified threshold of {SAFE_THRESHOLD} "
                                     f"({n_excluded} of {n_total}) were excluded by automation, except records without an abstract, "
                                     f"which were always kept. [Describe how the remaining records were screened, e.g. by two "
                                     f"independent reviewers.]" if mode == "exclude" else
                                     "Records were presented to reviewers in descending order of probability. [Describe how the "
                                     "records were screened, e.g. by two independent reviewers.]")),
        "",
        "## Validation evidence",
        "",
        EVIDENCE,
        "",
        ("Local validation is recommended before relying on automated exclusion (RAISE): screen a random sample of the records "
         "below the threshold and report how many would have been included."
         + (f" `validation-sample` holds {n_sample} records drawn at random (seed 0) from the excluded ones for this." if n_sample else "")),
        "",
        "## Eligibility criteria given to the tool",
        "",
        criteria.strip(),
        "",
    ]
    return "\n".join(lines)
