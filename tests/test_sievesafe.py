import csv
import io
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sievesafe import SAFE_THRESHOLD, cli, jev, records

RIS = """TY  - JOUR
TI  - Emicizumab pharmacokinetics in children
AB  - We report population PK of emicizumab.
PY  - 2020
ER  -

TY  - JOUR
T1  - A survey of cooking habits
N2  - Nothing to do with haemophilia.
ER  -

TY  - JOUR
TI  - Untitled record without abstract
ER  -
"""
CRITERIA = "Include emicizumab studies in humans that report pharmacokinetic data. Exclude reviews and editorials."


def fake_ask(state, key, **_):
    """High probability for anything mentioning emicizumab; 1000 tokens per call."""
    text = (state["record"]["title"] + state["record"]["abstract"]).lower()
    return (0.9 if "emicizumab" in text else 0.01), 1000


class Records(unittest.TestCase):
    def test_ris_titles_abstracts_and_untouched_roundtrip(self):
        recs = records.read_ris(RIS)
        self.assertEqual([r.title for r in recs], ["Emicizumab pharmacokinetics in children", "A survey of cooking habits", "Untitled record without abstract"])
        self.assertEqual(recs[1].abstract, "Nothing to do with haemophilia.")
        self.assertEqual(recs[2].abstract, "")
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "x.ris"
            records.write(out, records.Export("ris", ".ris"), recs)
            self.assertEqual([r.title for r in records.read_ris(out.read_text())], [r.title for r in recs])

    def test_csv_finds_columns_case_insensitively(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.csv"
            p.write_text("Title,Abstract,Year\nA,aa,2020\nB,,2021\n", encoding="utf-8")
            export, recs = records.read(p)
            self.assertEqual((export.fmt, [r.title for r in recs], recs[1].abstract), ("csv", ["A", "B"], ""))

    def test_csv_without_title_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.csv"
            p.write_text("foo,bar\n1,2\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                records.read(p)


@mock.patch("sievesafe.jev.ask", side_effect=fake_ask)
@mock.patch("sievesafe.jev.api_key", return_value="test-key")
class Screen(unittest.TestCase):
    def run_cli(self, d: Path, *extra: str) -> int:
        (d / "search.ris").write_text(RIS, encoding="utf-8")
        (d / "criteria.txt").write_text(CRITERIA, encoding="utf-8")
        return cli.main(["screen", str(d / "search.ris"), "--criteria", str(d / "criteria.txt"), "--title", "Emicizumab PK", "--yes", *extra])

    def test_rank_mode_keeps_everything_in_order(self, _key, ask):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.assertEqual(self.run_cli(d), 0)
            out = d / "search-sievesafe"
            ranked = list(csv.DictReader((out / "ranked.csv").open()))
            self.assertEqual(ranked[0]["title"], "Emicizumab pharmacokinetics in children")
            self.assertEqual([r["flag"] for r in ranked], ["", "below safe threshold", "no abstract, kept"])
            self.assertEqual(len(records.read_ris((out / "to-screen.ris").read_text())), 3)
            self.assertFalse((out / "excluded.ris").exists())
            self.assertIn("No records were marked as ineligible", (out / "report.md").read_text())

    def test_exclude_mode_writes_both_files_and_the_prisma_count(self, _key, ask):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.run_cli(d, "--mode", "exclude")
            out = d / "search-sievesafe"
            self.assertEqual(len(records.read_ris((out / "to-screen.ris").read_text())), 2)  # the record without abstract stays
            self.assertEqual([r.title for r in records.read_ris((out / "excluded.ris").read_text())], ["A survey of cooking habits"])
            self.assertEqual(len(records.read_ris((out / "validation-sample.ris").read_text())), 1)
            self.assertIn("Records marked as ineligible by automation tools: **1**", (out / "report.md").read_text())

    def test_rerun_uses_the_cache(self, _key, ask):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.run_cli(d)
            calls = ask.call_count
            self.run_cli(d)
            self.assertEqual(ask.call_count, calls)

    def test_budget_stops_calls_and_unscored_records_are_kept(self, _key, ask):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            with mock.patch("sievesafe.jev.cf.ThreadPoolExecutor") as pool:  # run serially so the budget check is deterministic
                pool.return_value.__enter__.return_value.map = map
                self.run_cli(d, "--mode", "exclude", "--budget", "0.00004")
            out = d / "search-sievesafe"
            # the first call is estimated at ~700 tokens (fits) and costs 1000 × $0.042/M = $0.000042; nothing else fits after it
            self.assertEqual(ask.call_count, 1)
            self.assertFalse(records.read_ris((out / "excluded.ris").read_text()))  # nothing unscored is ever excluded
            self.assertIn("not scored (budget) and kept", (out / "report.md").read_text())

    def test_refuses_to_spend_without_yes_outside_a_terminal(self, _key, ask):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "search.ris").write_text(RIS, encoding="utf-8")
            (d / "criteria.txt").write_text(CRITERIA, encoding="utf-8")
            with mock.patch("sys.stdin.isatty", return_value=False):
                code = cli.main(["screen", str(d / "search.ris"), "--criteria", str(d / "criteria.txt"), "--title", "t"])
            self.assertEqual((code, ask.call_count), (1, 0))


class Budget(unittest.TestCase):
    def test_calls_in_flight_count_against_the_budget(self):
        recs = [records.Record(f"title {i:02d}", "abstract", "", i) for i in range(20)]
        tokens = jev.estimate_tokens("t", CRITERIA, recs[:1])

        def slow_ask(state, key, **_):
            time.sleep(0.02)  # keep several calls in flight at once
            return 0.5, tokens  # each call costs exactly its estimate

        with tempfile.TemporaryDirectory() as d, mock.patch("sievesafe.jev.ask", side_effect=slow_ask) as ask:
            _, spent = jev.score(recs, "t", CRITERIA, jev.Cache(Path(d) / "c.tsv", CRITERIA), "k", budget=tokens * jev.PRICE_PER_TOKEN * 3.5)
        self.assertEqual(ask.call_count, 3)  # six threads, but only three calls fit
        self.assertLessEqual(spent, tokens * jev.PRICE_PER_TOKEN * 3.5)

    def test_an_unexpected_answer_is_a_jev_error(self):
        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch("urllib.request.urlopen", return_value=Resp(b'{"answers": {}}')), self.assertRaises(jev.JevError):
            jev.ask({}, "k")


class Estimate(unittest.TestCase):
    def test_estimate_errs_high_but_close_to_the_measured_cost(self):
        recs = [records.Record("t" * 120, "a" * 1400, "", i) for i in range(1000)]
        per_record = jev.estimate_tokens("r" * 100, "c" * 973, recs) / 1000
        fitted = (100 + 973 + 120 + 1400) / 4.92 + 503  # the fit on SYNERGY+ calls
        self.assertTrue(fitted < per_record < fitted * 1.3, (per_record, fitted))

    def test_threshold_is_the_frozen_one(self):
        self.assertEqual(SAFE_THRESHOLD, 0.06)


if __name__ == "__main__":
    unittest.main()
