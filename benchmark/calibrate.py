#!/usr/bin/env python3
"""Freeze the auto-exclude threshold on the TRAIN reviews only, before the test split is looked at.

  calibrate.py --as-frozen   rerun the procedure exactly as frozen and check it reproduces calibration.json (exit 1 if not)
  calibrate.py               the corrected procedure (see below); prints its thresholds next to the frozen ones
  calibrate.py --write       overwrite calibration.json with the corrected procedure (new model or question only; rerun the test)

For each recall target (95/98/100%) the threshold is the highest score t such that the pooled train recall (every include
of every train review, capped at 1,000 records as sampled when asked) at score ≥ t still meets the target. The file
records when it was frozen and the SHA-256 of the answers it used, so anyone can check it came before the test split.

Known flaw of the frozen run: it looked scores up by OpenAlex id pooled over all train reviews, so a paper that appears in
two reviews got the score asked for the later one (298 of 12,982 records, 24 of them includes). The corrected procedure
uses each review's own answers and gives higher (less conservative) thresholds; sievesafe keeps the frozen 0.06, which is
the value fixed before the test split was seen, and results.py reports the test split at both."""
import json
import sys

import common

AS_FROZEN = "--as-frozen" in sys.argv
result = common.calibrate(as_frozen=AS_FROZEN)
result.pop("id_pooling_changed")

if "--write" in sys.argv and not AS_FROZEN:
    common.CALIBRATION.write_text(json.dumps(result, indent=1) + "\n")
    print(f"wrote {common.CALIBRATION.name}: " + ", ".join(f"{k} → t={v['threshold']}" for k, v in result["targets"].items()))
    sys.exit(0)
frozen = json.loads(common.CALIBRATION.read_text())
same = all(frozen[k] == result[k] for k in ("answers_sha256", "train_reviews", "records", "includes", "targets"))
print(f"frozen {frozen['frozen_at']} (answers sha {frozen['answers_sha256'][:12]}): "
      + ", ".join(f"{k} → t={v['threshold']}" for k, v in frozen["targets"].items()))
if AS_FROZEN:
    print("rerun as frozen from answers/: " + ("identical" if same else "DIFFERENT: " + json.dumps(result["targets"])))
    sys.exit(0 if same else 1)
print("corrected procedure: " + ", ".join(f"{k} → t={v['threshold']} (train recall {v['train_recall']:.1%}, auto-excluded "
                                           f"{v['train_auto_excluded']:.0%})" for k, v in result["targets"].items()))
