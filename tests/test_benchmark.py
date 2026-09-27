"""Benchmark checks. The first ones run on the committed answers alone; the last two need SYNERGY+ in benchmark/data."""
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

BENCH = Path(__file__).resolve().parent.parent / "benchmark"
sys.path.insert(0, str(BENCH))
import common

from sievesafe import SAFE_THRESHOLD

HAS_DATA = (common.DATA / "metadata/review_metadata.csv").exists()


class CommittedAnswers(unittest.TestCase):
    def test_calibration_was_frozen_on_the_committed_train_answers(self):
        cal = json.loads(common.CALIBRATION.read_text())
        self.assertEqual(common.answers_sha(common.TRAIN), cal["answers_sha256"])
        self.assertEqual(len(common.answer_files(common.TRAIN)), len(cal["train_reviews"]))

    def test_the_package_uses_the_frozen_safe_threshold(self):
        self.assertEqual(SAFE_THRESHOLD, json.loads(common.CALIBRATION.read_text())["targets"]["100%"]["threshold"])

    def test_every_test_review_has_answers_and_asreview_runs(self):
        asr = json.loads((common.ANSWERS / "asreview-3.0.8.json").read_text())
        self.assertEqual(len(asr), 23)
        self.assertEqual({f.name.split("-", 1)[1].split(".jsonl")[0] for f in common.answer_files(common.TEST)}, set(asr))


class Metrics(unittest.TestCase):
    def test_wss(self):
        # 10 records, 2 includes found at positions 1 and 4: 95% of 2 needs both → 6 of 10 not read, minus 0.05
        self.assertAlmostEqual(common.wss([1, 0, 0, 1, 0, 0], 10, 2, 0.95), 0.55)
        self.assertAlmostEqual(common.wss([1, 0, 0, 1], 10, 2, 1.0), 0.6)
        self.assertTrue(math.isnan(common.wss([1, 0], 10, 2, 1.0)))

    def test_threshold_matches_brute_force(self):
        pairs = [(0.9, 1), (0.5, 0), (0.4, 1), (0.4, 1), (0.2, 0), (0.1, 1), (0.05, 0)]
        for target in (1.0, 0.75, 0.5, 0.25):
            P = sum(y for _, y in pairs)
            brute = max(s for s, y in pairs if y and sum(yy for ss, yy in pairs if ss >= s) / P >= target)
            self.assertEqual(common.threshold(pairs, target), brute)

    def test_clopper_pearson_upper_bound(self):
        self.assertAlmostEqual(common.cp_upper(0, 43), 1 - 0.05 ** (1 / 43), places=6)
        self.assertGreater(common.cp_upper(1, 43), common.cp_upper(0, 43))

    def test_knee_never_stops_before_min_read(self):
        self.assertEqual(common.knee_stop([1] * 5 + [0] * 100), 105)
        self.assertLess(common.knee_stop([1] * 30 + [0] * 1000), 1030)


@unittest.skipUnless(HAS_DATA, "SYNERGY+ not in benchmark/data (see benchmark/README.md)")
class WithData(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run([sys.executable, *args], cwd=BENCH, capture_output=True, text=True, check=False)

    def test_the_frozen_calibration_is_reproduced_exactly(self):
        r = self.run_script("calibrate.py", "--as-frozen")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless((BENCH / "external/data/reviews.json").exists(), "CLEF TAR data not built (external/clef_fetch.py)")
    def test_external_results_md_is_what_the_answers_give(self):
        r = self.run_script("external/evaluate.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_results_md_is_what_the_data_and_answers_give(self):
        r = self.run_script("results.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
