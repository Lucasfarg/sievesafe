"""sievesafe — zero-shot title/abstract screening that only auto-excludes when it is safe to.

  sievesafe screen <search.ris|.csv> --criteria criteria.txt --title "Review title" [options]

  --mode rank       (default) keep everything; order by probability and flag records below the safe threshold
  --mode exclude    remove records below the safe threshold before human screening (opt-in; validate locally)
  --out DIR         where results go (default: <input>-sievesafe/)
  --budget USD      hard cap on API spend for this run (default 2.00); unscored records are always kept
  --yes             do not ask before spending
  --key-file PATH   file with TYPESAFE_API_KEY=... (default: $TYPESAFE_API_KEY or ~/.config/sievesafe/typesafe.env)

Outputs: ranked.csv (rank, probability, flag, title), to-screen.<ris|csv> (ordered, original records untouched),
excluded.<ris|csv> in exclude mode, and report.md (PRISMA count, methods paragraph, validation evidence)."""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from sievesafe import SAFE_THRESHOLD, jev, records, report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sievesafe", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen", help="score a search export against eligibility criteria")
    s.add_argument("input", type=Path)
    s.add_argument("--criteria", type=Path, required=True)
    s.add_argument("--title", required=True)
    s.add_argument("--mode", choices=["rank", "exclude"], default="rank")
    s.add_argument("--out", type=Path)
    s.add_argument("--budget", type=float, default=2.0)
    s.add_argument("--yes", action="store_true")
    s.add_argument("--key-file", type=Path)
    a = p.parse_args(argv)
    try:
        return screen(a)
    except (ValueError, jev.JevError) as e:
        print(f"sievesafe: {e}", file=sys.stderr)
        return 1


def screen(a) -> int:
    fmt, recs = records.read(a.input)
    criteria = a.criteria.read_text(encoding="utf-8").strip()
    if not recs:
        raise ValueError(f"{a.input.name}: no records found")
    if len(criteria) < 40:
        raise ValueError("the criteria file looks empty; paste the review's inclusion and exclusion criteria")
    out = a.out or a.input.with_name(a.input.stem + "-sievesafe")
    out.mkdir(parents=True, exist_ok=True)
    cache = jev.Cache(out / ".sievesafe-cache.tsv", criteria)
    todo = [r for r in recs if cache.get(r) is None]
    estimate = jev.estimate_tokens(a.title, criteria, todo) * jev.PRICE_PER_TOKEN
    no_abstract = sum(1 for r in recs if not r.abstract)
    print(f"{len(recs)} records ({no_abstract} without abstract), {len(recs) - len(todo)} already scored; "
          f"estimated cost US$ {estimate:.3f} (budget US$ {a.budget:.2f})")
    if todo and not a.yes:
        if not sys.stdin.isatty():
            raise ValueError("refusing to spend without --yes when not run from a terminal")
        if input("proceed? [y/N] ").strip().lower() not in ("y", "yes", "s", "sim"):
            return 0
    key = jev.api_key(a.key_file) if todo else ""

    def progress(done: int, total: int) -> None:
        if done == total or done % 200 == 0:
            print(f"  scored {done}/{total}", file=sys.stderr)

    scores, spent = jev.score(recs, a.title, criteria, cache, key, a.budget, progress=progress) if todo else (
        {r.index: cache.get(r) for r in recs}, 0.0)
    scored = [r for r in recs if r.index in scores]
    ordered = sorted(recs, key=lambda r: -scores.get(r.index, 1.0))  # unscored records go first: never hidden
    low = [r for r in scored if scores[r.index] < SAFE_THRESHOLD]
    excluded = low if a.mode == "exclude" else []
    keep = [r for r in ordered if r not in excluded]

    with (out / "ranked.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "probability", "flag", "title"])
        for i, r in enumerate(ordered, 1):
            prob = scores.get(r.index)
            flag = "not scored" if prob is None else ("below safe threshold" if prob < SAFE_THRESHOLD else "")
            w.writerow([i, "" if prob is None else f"{prob:.4f}", flag, r.title])
    records.write(out / f"to-screen.{fmt}", fmt, keep)
    if a.mode == "exclude":
        records.write(out / f"excluded.{fmt}", fmt, excluded)
    (out / "report.md").write_text(report.build(source=a.input.name, title=a.title, criteria=criteria, mode=a.mode, n_total=len(recs),
                                                n_scored=len(scored), n_excluded=len(excluded), n_low=len(low), spent=spent), encoding="utf-8")
    print(f"done: {len(scored)}/{len(recs)} scored, {len(low)} below the safe threshold"
          + (" and excluded" if a.mode == "exclude" else " (flagged, kept)") + f"; spent US$ {spent:.4f} → {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
