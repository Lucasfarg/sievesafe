"""The CLEF TAR 2019 set built by clef_fetch.py, and the conditions it is screened under (see PLAN.md).

A condition is (answers variant, criteria given to the model, how many non-included records per review). Every
condition keeps every record included at either level; the others are a prefix of the same seeded permutation, so the
smaller sample is a subset of the larger one and conditions can be compared record by record."""
import csv
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
CONDITIONS = {
    "full": {"variant": "clef", "criteria": "objectives and selection criteria", "others": None},
    "objectives": {"variant": "clefobj", "criteria": "objectives only", "others": 300},
}


def reviews() -> dict:
    return json.loads((DATA / "reviews.json").read_text())


def criteria(meta: dict, condition: str) -> str:
    full = meta["criteria"]
    return full if condition == "full" else full.split("\n\nSelection criteria:")[0]


def rows(topic: str, meta: dict, condition: str) -> list[dict]:
    """Records of one review under a condition, each with its weight back to the review's size."""
    with (DATA / f"{topic}.csv").open(encoding="utf-8") as f:
        recs = list(csv.DictReader(f))
    keep = [r for r in recs if r["y"] == "1" or r["ya"] == "1"]
    others = [r for r in recs if not (r["y"] == "1" or r["ya"] == "1")][:CONDITIONS[condition]["others"]]
    weight = (meta["records_total"] - len(keep)) / len(others) if others else 1.0
    return [{**r, "w": 1.0} for r in keep] + [{**r, "w": weight} for r in others]
