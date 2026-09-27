# sievesafe benchmark

This folder holds everything behind the numbers sievesafe quotes, built from public data. The results files are written
by scripts, and none of their numbers is typed by hand.

## What is here

| path | what it contains |
|:--|:--|
| `answers/f1-<review>.jsonl.gz` | Jev's answer for every record of the 23 SYNERGY+ test reviews (33,001 calls) |
| `answers/c1-<review>.jsonl.gz` | Jev's answers for the 20 calibration reviews, capped at 1,000 records each (12,982 calls) |
| `answers/stability-jev-1.13.0.jsonl.gz` | 2,000 test records asked a second time with the model version pinned |
| `answers/asreview-3.0.8.json` | where the included studies came up in 69 ASReview simulations (23 reviews × 3 seeds) |
| `answers/clef*-<topic>.jsonl.gz` | Jev's answers for the CLEF TAR external validation, one prefix per condition |
| `calibration.json` | the thresholds set on the calibration reviews, with the time and the SHA-256 of the answers used |
| `data-manifest.json` | size, number of includes and a hash of the labels of every SYNERGY+ review used |
| `results.md` | the SYNERGY+ tables: calibration, test split, leave-one-review-out, title/abstract labels, ASReview, stopping rules, stability, cost |
| `external/PLAN.md` | the pre-specified plans for the CLEF TAR tests, each committed before its first model call |
| `external/results*.md` | the CLEF TAR results, one file per condition |

The answer files hold OpenAlex or PubMed ids, probabilities and token counts, and no titles or abstracts. The records
themselves are not redistributed here (SYNERGY+ abstracts may not be republished as plain text), so the first step
below downloads them.

## Reproducing the SYNERGY+ results

From the repository root, with Python 3.11 or newer and [uv](https://docs.astral.sh/uv/):

```bash
# 1. Download SYNERGY+ v3 into benchmark/data. "yes Y" answers the prompt about converting abstracts to plain text
#    on your machine. Takes about 3 minutes.
yes Y | SYNERGY_VERSION=3.0 uvx --from synergy-dataset==2.2 --with pandas synergy get -o benchmark/data

# 2. Check that the frozen calibration is exactly what the committed answers give (no API calls).
python3 benchmark/calibrate.py --as-frozen

# 3. Regenerate every table from the data and the committed answers (no API calls, a few seconds).
python3 benchmark/results.py
git diff --stat benchmark/results.md        # should show no change if your data matches data-manifest.json

# 4. Run the same checks as the test suite.
python3 -m unittest discover -s tests
```

`results.py` stops with an error if the downloaded data differs from `data-manifest.json`. If you keep the data
somewhere else, set `SYNERGY_DATA=/path/to/data` and skip step 1.

## Reproducing the CLEF TAR results

`external/clef_fetch.py` builds each set from the CLEF TAR repository (at a pinned commit), PubMed and Europe PMC. It
makes no model calls and takes a few minutes per set.

```bash
python3 benchmark/external/clef_fetch.py                                            # 2019 intervention reviews
python3 benchmark/external/clef_fetch.py --task dta --others 300                    # 2019 diagnostic accuracy reviews
python3 benchmark/external/clef_fetch.py --task dta1718 --topics 40 --keep final --others 200   # half of 2017–2018
for c in full objectives dta dta1718; do python3 benchmark/external/evaluate.py --condition $c; done
```

`evaluate.py --check` compares each results file with what the answers give, and the tests run it whenever the CLEF
data is present.

## Asking Jev again (this costs money)

You need a TypeSafe key (`TYPESAFE_API_KEY` or `~/.config/sievesafe/typesafe.env`). Every script that calls the model
takes a hard `--budget` in US$. It counts the answers already on disk for that variant and stops before a call could go
over the limit. New answers are written to `answers/*.jsonl`, which git ignores; compress them with `gzip -n` before
committing.

```bash
python3 benchmark/screen.py f2 test --budget 1.60                          # every test record, new variant f2: about US$ 1.55
python3 benchmark/screen.py c2 train --cap 1000 --budget 0.65              # the calibration reviews: about US$ 0.61
python3 benchmark/stability.py --n 2000 --budget 0.15                      # about US$ 0.09
python3 benchmark/external/screen.py --condition full --budget 0.95        # one CLEF condition; see PLAN.md for the others
```

A new variant only shows up in `results.md` after you point `common.TEST` or `common.TRAIN` at it. A new model or a
new question needs a new calibration (`calibrate.py --write`) and a new run on the test split, which is why sievesafe
pins `jev-1.13.0`.

## ASReview (no API, CPU only)

```bash
uv venv benchmark/.venv-asreview --python 3.12
uv pip install --python benchmark/.venv-asreview asreview==3.0.8
python3 benchmark/asreview_baseline.py        # 69 simulations into benchmark/.asreview/, then answers/asreview-3.0.8.json
```

## How the benchmark was designed

- **Data.** SYNERGY+ v3 has 114 reviews with published screening decisions, and its own split puts 23 of them in
  `test`. The labels are the final (full-text) inclusions; 12 test reviews also publish the title and abstract decision
  (section 4 of `results.md`).
- **Question.** Jev gets one zero-shot yes/no question per record, with the review's title and its SYNERGY+
  `eligibility_criteria` text, the record's title and abstract, and a policy that favours sending doubtful records on
  to full text. It is the same question `sievesafe screen` asks (`src/sievesafe/jev.py`); `screen.py` imports it from
  there.
- **Calibration.** We used 20 reviews from the SYNERGY+ train split, each capped at 1,000 records (all includes plus a
  seeded sample of the other records, weighted back to the full size). For each recall target, the threshold is the
  highest score that keeps that share of the pooled includes. It was frozen, time-stamped and hashed in
  `calibration.json`.
- **A known flaw in the frozen calibration.** The frozen run looked scores up by OpenAlex id across all the calibration
  reviews, so a paper that appears in two reviews took the score asked for the later one (section 1 of `results.md` has
  the counts). `calibrate.py --as-frozen` reproduces the frozen file exactly, and `calibrate.py` shows the corrected
  procedure, which gives higher thresholds. sievesafe keeps the frozen 0.06 because it was fixed before the test split
  was scored and it is the more cautious of the two; section 2 of `results.md` reports the test split at both.
- **Evaluation.** The test split is scored at the frozen thresholds and never retuned. Leave-one-review-out over all 43
  answered reviews shows how much the threshold moves from one set of reviews to another, and ASReview 3.0.8 with its
  default settings is the reference ranking tool.
- **External validation.** Each CLEF TAR condition was written into `external/PLAN.md` and committed before its first
  model call, including the rule for calling it a success or a failure. The results are reported as that rule says,
  failures included.
- **Model.** The f1 and c1 answers were requested in September 2026 under the model id `jev-latest`. The stability run,
  the CLEF TAR runs and sievesafe itself use the pinned `jev-1.13.0`.
