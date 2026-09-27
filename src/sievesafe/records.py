"""Reading search exports (RIS, CSV) and writing results back without touching the original records."""
from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

csv.field_size_limit(10**8)
RIS_TAG = re.compile(r"^([A-Z][A-Z0-9])  - ?(.*)$")
TITLE_TAGS = ("TI", "T1", "CT", "BT")
ABSTRACT_TAGS = ("AB", "N2")
TITLE_COLUMNS = ("title", "ti", "article title", "primary title")
ABSTRACT_COLUMNS = ("abstract", "ab", "abstract note", "abstracttext")


@dataclass
class Record:
    title: str
    abstract: str
    raw: str | dict = field(repr=False)  # the original RIS block or CSV row, written back untouched
    index: int = 0

    @property
    def key(self) -> str:
        """Stable id for caching: same text → same answer, whatever the file order."""
        return hashlib.sha256(f"{self.title}\n{self.abstract}".encode()).hexdigest()[:20]


def read(path: Path) -> tuple[str, list[Record]]:
    """→ (format, records). Format is taken from the extension (.ris/.txt → RIS, .csv/.tsv → CSV)."""
    suffix = path.suffix.lower()
    if suffix in (".ris", ".txt"):
        return "ris", read_ris(path.read_text(encoding="utf-8-sig", errors="replace"))
    if suffix in (".csv", ".tsv"):
        return "csv", read_csv(path, "\t" if suffix == ".tsv" else ",")
    raise ValueError(f"{path.name}: use a .ris or .csv export")


def read_ris(text: str) -> list[Record]:
    records, block, fields = [], [], {}
    for line in text.splitlines():
        m = RIS_TAG.match(line)
        if m and m.group(1) == "TY" and block:
            block, fields = [], {}  # a TY without ER: start over rather than merge two records
        block.append(line)
        if m:
            tag, value = m.groups()
            fields.setdefault(tag, []).append(value.strip())
            if tag == "ER":
                title = next((fields[t][0] for t in TITLE_TAGS if t in fields), "")
                abstract = " ".join(next((fields[t] for t in ABSTRACT_TAGS if t in fields), []))
                records.append(Record(title, abstract, "\n".join(block), len(records)))
                block, fields = [], {}
    return records


def read_csv(path: Path, delimiter: str) -> list[Record]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=delimiter))
    if not rows:
        return []
    cols = {c.lower().strip(): c for c in rows[0]}
    tcol = next((cols[c] for c in TITLE_COLUMNS if c in cols), None)
    acol = next((cols[c] for c in ABSTRACT_COLUMNS if c in cols), None)
    if not tcol:
        raise ValueError(f"{path.name}: no title column (looked for {', '.join(TITLE_COLUMNS)})")
    return [Record((r.get(tcol) or "").strip(), (r.get(acol) or "").strip() if acol else "", r, i) for i, r in enumerate(rows)]


def write(path: Path, fmt: str, records: list[Record]) -> None:
    if fmt == "ris":
        path.write_text("\n\n".join(r.raw for r in records) + ("\n" if records else ""), encoding="utf-8")
        return
    fields = list(records[0].raw) if records else []
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(r.raw for r in records)
