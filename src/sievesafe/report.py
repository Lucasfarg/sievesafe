"""The report a reviewer can paste into their methods and PRISMA flow diagram (RAISE / PRISMA 2020 reporting)."""
from __future__ import annotations

import datetime

from sievesafe import MODEL, SAFE_THRESHOLD, __version__

EVIDENCE = ("On the SYNERGY+ benchmark (v3), with the threshold frozen on 20 training reviews before the 23 test reviews "
            "(33,001 records, 597 included studies) were looked at, records scoring below it contained none of the studies "
            "finally included in any of the 23 reviews, while 29% of all records fell below it. Recalibrating with each of 43 "
            "reviews held out in turn kept ≥98% of included studies in every review (100% in 42 of 43). Against human "
            "title/abstract decisions the threshold is stricter: it kept 96% of records humans passed at that stage (range 78–100%), "
            "losing only records later excluded at full text.")


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
                                     f"which were always kept; all remaining records were "
                                     f"screened by two independent reviewers." if mode == "exclude" else
                                     "Records were presented to reviewers in descending order of probability; "
                                     "all records were screened by two independent reviewers.")),
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
