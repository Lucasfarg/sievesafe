"""sievesafe — zero-shot title/abstract screening that only auto-excludes when it is safe to."""

__version__ = "0.1.0"

# Frozen on 20 SYNERGY+ train reviews before the test split was looked at (benchmark/calibration.json).
SAFE_THRESHOLD = 0.06
MODEL = "jev-1.13.0"  # pinned: the threshold was calibrated on this model version
