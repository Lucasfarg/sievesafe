#!/usr/bin/env python3
"""ASReview (the field's reference active-learning tool) on the 23 SYNERGY+ test reviews, for the comparison in results.md.

  asreview_baseline.py [--asreview PATH] [--projects DIR] [--seeds 3]

For each test review and seed: `asreview simulate` with its default model and 1 included + 1 excluded prior record
(--prior-seed = --seed = seed); the simulated reviewer labels records in the order ASReview asks until every include is
found. Only the reading positions of the includes are kept, in answers/asreview-3.0.8.json (no record text), which is
all WSS needs. Existing .asreview projects in --projects (default benchmark/.asreview/) are reused, missing ones are run.
Needs ASReview 3.0.8 in its own environment (see README); one simulation takes seconds to minutes, 69 in total.
Runs at nice 19 on 4 cores."""
import argparse
import json
import os
import sqlite3
import subprocess
import tempfile
import zipfile
from pathlib import Path

import common

p = argparse.ArgumentParser()
p.add_argument("--asreview", default=str(common.HERE / ".venv-asreview/bin/asreview"))
p.add_argument("--projects", type=Path, default=common.HERE / ".asreview")
p.add_argument("--seeds", type=int, default=3)
a = p.parse_args()
a.projects.mkdir(exist_ok=True)
env = {**os.environ, "OMP_NUM_THREADS": "4", "OPENBLAS_NUM_THREADS": "4", "MKL_NUM_THREADS": "4"}


def include_positions(key: str, seed: int) -> list[int]:
    project = a.projects / f"{key}-s{seed}.asreview"
    if not project.exists():
        subprocess.run(["nice", "-n", "19", "taskset", "-c", "0-3", a.asreview, "simulate", str(common.DATA / f"{key}.csv"),
                        "--n-prior-included", "1", "--n-prior-excluded", "1", "--prior-seed", str(seed), "--seed", str(seed),
                        "-o", str(project)], check=True, capture_output=True, env=env)
    with tempfile.TemporaryDirectory() as d:
        zipfile.ZipFile(project).extract("results.db", d)
        con = sqlite3.connect(Path(d) / "results.db")
        labels = [row[0] for row in con.execute("select label from results order by time")]
        con.close()
    return [i for i, y in enumerate(labels, 1) if y == 1]


out = {k: {str(s): include_positions(k, s) for s in range(1, a.seeds + 1)} for k in common.test_keys()}
(common.ANSWERS / "asreview-3.0.8.json").write_text(json.dumps(out, separators=(",", ":")) + "\n")
print(f"{len(out)} reviews × {a.seeds} seeds → answers/asreview-3.0.8.json")
