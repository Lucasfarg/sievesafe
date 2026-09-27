# Contributing

Bug reports and small, focused pull requests are welcome. If your change affects how records are screened, the
question sent to the model or the threshold, please open an issue first so we can talk it through.

## Setting up and running the checks

You need Python 3.11 or newer; the package itself has no dependencies.

```bash
python3 -m unittest discover -s tests      # runs offline, with the model mocked
uvx ruff check .                            # lint
```

The tests never call the TypeSafe API. Checks that need the SYNERGY+ or CLEF TAR data are skipped until you build that
data (see `benchmark/README.md`).

## Rules that keep the numbers honest

- **Numbers are generated, not typed.** Everything in `benchmark/results.md`, `benchmark/external/results*.md`, the
  number tables in `README.md` and `src/sievesafe/evidence.txt` is written by `benchmark/results.py` or
  `benchmark/external/evaluate.py`. Their `--check` option, which the tests run, fails if any of these files is out of
  date.
- **The threshold stays put.** `SAFE_THRESHOLD` and `benchmark/calibration.json` only change with a new model version
  or a new question, and then only after a new calibration and a new pre-registered test (`benchmark/external/PLAN.md`).
- **New evaluations are registered first.** Add the plan to `PLAN.md` and commit it before any record goes to the
  model, then report whatever verdict the plan gives, failures included.
- **No record text in the repository.** Answer files keep identifiers and probabilities only, and the test fixtures are
  made up.

## Screenshots

`docs/serve-light.png` and `docs/serve-dark.png` are made by `docs/screenshot.mjs` (Playwright). They show the confirm
step, so taking them costs nothing.
