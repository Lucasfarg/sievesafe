"""sievesafe — zero-shot title/abstract screening that auto-excludes only below a pre-specified threshold."""

__version__ = "0.1.0"

# Frozen on 20 SYNERGY+ train reviews before the test split was looked at (benchmark/calibration.json).
SAFE_THRESHOLD = 0.06
MODEL = "jev-1.13.0"  # pinned: the version the jev-latest alias used for calibration pointed to; stability is in benchmark/results.md
