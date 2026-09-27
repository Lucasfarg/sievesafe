# Contributing

Bug reports and small, focused pull requests are welcome. Open an issue first for anything that changes screening
behaviour, the question sent to the model, or the threshold.

## Setup and checks

Python 3.11 or newer; the package itself has no dependencies.

```bash
python3 -m unittest discover -s tests      # offline; the model is mocked
uvx ruff check .                            # lint
```

Tests never call the TypeSafe API. Checks that need SYNERGY+ or CLEF TAR data are skipped until you build the data
(see `benchmark/README.md`).

## Rules that keep the numbers honest

- **No number is typed by hand.** Everything in `benchmark/results.md`, `benchmark/external/results*.md`, the numbers
  blocks of `README.md` and `src/sievesafe/evidence.txt` is written by `benchmark/results.py` or
  `benchmark/external/evaluate.py`; `--check` (run by the tests) fails if any of them is stale.
- **The threshold does not move.** `SAFE_THRESHOLD` and `benchmark/calibration.json` change only with a new model
  version or a new question, followed by a new calibration and a new pre-registered test (`benchmark/external/PLAN.md`).
- **A new evaluation is registered first.** Add its plan to `PLAN.md` and commit it before any record is sent to the
  model; report the verdict it gives, including failures.
- **No record text in the repository.** Answers keep identifiers and probabilities only; test fixtures are fictional.

## Screenshots

`docs/serve-light.png` and `docs/serve-dark.png` come from `docs/screenshot.mjs` (Playwright), at the confirm step so
nothing is spent.
