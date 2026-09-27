"""sievesafe — zero-shot title/abstract screening that auto-excludes only below a pre-specified threshold.

  sievesafe screen <search.ris|.csv> --criteria criteria.txt --title "Review title" [options]
  sievesafe serve [--port 8765] [--dir sievesafe-results] [--max-budget 2.00]     the same in a local web page

  --mode rank       (default) keep everything; order by probability and flag records below the safe threshold
  --mode exclude    remove records below the safe threshold before human screening (opt-in; validate locally)
  --out DIR         where results go (default: <input>-sievesafe/)
  --budget USD      hard cap on API spend for this run (default 2.00); unscored records are always kept
  --yes             do not ask before spending
  --key-file PATH   file with TYPESAFE_API_KEY=... (default: $TYPESAFE_API_KEY or ~/.config/sievesafe/typesafe.env)

Inputs: RIS (.ris/.txt), PubMed/MEDLINE (.nbib/.txt), Web of Science plain text (.txt), CSV/TSV (, or ; any encoding).
Outputs, in the input's format: ranked.csv (rank, record, probability, flag, duplicate_of, title); to-screen.<ext> (ordered,
original records untouched); in exclude mode excluded.<ext> and validation-sample.<ext> (50 random excluded records to
screen for local validation); report.md (PRISMA count, methods paragraph, validation evidence).
Records without an abstract are never flagged or excluded; duplicates (same DOI or title) are scored once, all kept."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sievesafe import jev, run


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
    v = sub.add_parser("serve", help="open a local page to screen without the terminal")
    v.add_argument("--port", type=int, default=8765)
    v.add_argument("--dir", type=Path, default=Path("sievesafe-results"), help="where results are saved (default ./sievesafe-results)")
    v.add_argument("--max-budget", type=float, default=2.0, help="highest spend the page may confirm for one run (default 2.00)")
    v.add_argument("--key-file", type=Path)
    v.add_argument("--no-browser", action="store_true")
    a = p.parse_args(argv)
    if a.cmd == "serve":
        from sievesafe import serve
        serve.serve(a.port, a.dir, a.max_budget, a.key_file, not a.no_browser)
        return 0
    try:
        return screen(a)
    except (ValueError, jev.JevError) as e:
        print(f"sievesafe: {e}", file=sys.stderr)
        return 1


def screen(a) -> int:
    out = a.out or a.input.with_name(a.input.stem + "-sievesafe")
    job = run.prepare(a.input, a.title, a.criteria.read_text(encoding="utf-8"), a.mode, out)
    print(f"{len(job.recs)} records ({job.no_abstract} without abstract, {job.duplicates} duplicates), "
          f"{len(job.recs) - job.duplicates - len(job.todo)} already scored; estimated cost US$ {job.estimate:.4f} (budget US$ {a.budget:.2f})")
    if a.mode == "exclude":
        print("exclude mode: validate locally before relying on it (RAISE) — screen validation-sample and report how many "
              "you would have included", file=sys.stderr)
    if job.todo and not a.yes:
        if not sys.stdin.isatty():
            raise ValueError("refusing to spend without --yes when not run from a terminal")
        if input("proceed? [y/N] ").strip().lower() not in ("y", "yes", "s", "sim"):
            return 0

    def progress(done: int, total: int) -> None:
        if done == total or done % 200 == 0:
            print(f"  {done}/{total} records processed", file=sys.stderr)

    res = run.execute(job, jev.api_key(a.key_file) if job.todo else "", a.budget, progress)
    print(f"done: {res['scored']}/{res['total']} scored, {res['below_threshold']} below the safe threshold"
          + (" and excluded" if a.mode == "exclude" else " (flagged, kept)") + f"; spent US$ {res['spent']:.4f} → {out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
