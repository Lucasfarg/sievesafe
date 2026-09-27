"""Reading search exports and writing results back in the same format, without touching the original records.

Formats: RIS (.ris/.txt: Scopus, Web of Science, Rayyan, EndNote, Zotero…), PubMed/MEDLINE (.nbib/.txt), Web of Science
plain text (.txt), and CSV/TSV (, ; or tab, as Rayyan, Covidence or a spreadsheet saves it). Text is read as UTF-8 and,
if that fails, as Windows-1252/Latin-1; results are written back in the encoding and delimiter they came in."""
from __future__ import annotations

import csv
import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

csv.field_size_limit(10**8)
RIS_TAG = re.compile(r"^([A-Z][A-Z0-9])  ?- ?(.*)$")
MEDLINE_TAG = re.compile(r"^([A-Z][A-Z0-9]{0,3}) *- (.*)$")
WOS_TAG = re.compile(r"^([A-Z][A-Z0-9]) (.*)$")
TITLE_TAGS = ("TI", "T1", "CT", "BT")
ABSTRACT_TAGS = ("AB", "N2")
TITLE_COLUMNS = ("title", "ti", "article title", "primary title", "document title")
ABSTRACT_COLUMNS = ("abstract", "ab", "abstract note", "abstracttext", "abstract text")
DOI_COLUMNS = ("doi", "di", "do")


@dataclass
class Record:
    title: str
    abstract: str
    raw: str | dict = field(repr=False)  # the original block or CSV row, written back untouched
    index: int = 0
    doi: str = ""

    @property
    def key(self) -> str:
        """Stable id for caching: same text → same answer, whatever the file order."""
        return hashlib.sha256(f"{self.title}\n{self.abstract}".encode()).hexdigest()[:20]


@dataclass
class Export:
    fmt: str  # ris | medline | wos | csv
    suffix: str  # written back with the same extension
    encoding: str = "utf-8"
    delimiter: str = ","
    header: str = ""  # Web of Science: the FN/VR lines before the first record
    columns: list[str] = field(default_factory=list)


def decode(data: bytes) -> tuple[str, str]:
    """→ (text, encoding). UTF-8 (with or without BOM) first; otherwise Windows-1252, then Latin-1, which never fails."""
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace"), "utf-8-sig"
    for enc in ("utf-8", "cp1252"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1"), "latin-1"


def read(path: Path) -> tuple[Export, list[Record]]:
    """→ (export, records). The format comes from the extension, and for .txt from the content."""
    suffix = path.suffix.lower()
    if suffix not in (".ris", ".txt", ".nbib", ".csv", ".tsv"):
        raise ValueError(f"{path.name}: use a .ris, .nbib, .txt or .csv export")
    text, enc = decode(path.read_bytes())
    if suffix in (".csv", ".tsv"):
        return read_csv(text, enc, suffix, path.name)
    head = text.lstrip(" \r\n")[:4000]
    if head.startswith("FN ") or (re.search(r"^PT [A-Z]\s*$", head, re.MULTILINE) and not re.search(r"^TY  ?- ", head, re.MULTILINE)):
        return read_wos(text, enc, suffix)
    if re.search(r"^PMID- ", head, re.MULTILINE):
        return Export("medline", suffix, enc), read_medline(text)
    return Export("ris", suffix, enc), read_ris(text)


def fields_record(fields: dict[str, list[str]], raw: str, index: int, abstract_tags=ABSTRACT_TAGS, doi_tags=("DO",)) -> Record:
    title = next((" ".join(fields[t][0].split()) for t in TITLE_TAGS if t in fields), "")
    abstract = " ".join(" ".join(next((fields[t] for t in abstract_tags if t in fields), [])).split())
    doi = next((fields[t][0].strip() for t in doi_tags if t in fields), "")
    return Record(title, abstract, raw, index, doi)


def read_ris(text: str) -> list[Record]:
    """RIS: `XX  - value`, one record from TY to ER; untagged lines continue the previous field."""
    records, block, fields, last = [], [], {}, None
    for line in text.splitlines():
        m = RIS_TAG.match(line)
        if m and m.group(1) == "TY" and fields:
            block, fields = [], {}  # a TY without ER: start over rather than merge two records
        if not block and not m:
            continue  # blank lines or notes between records
        block.append(line)
        if m:
            last, value = m.group(1), m.group(2).strip()
            fields.setdefault(last, []).append(value)
            if last == "ER":
                records.append(fields_record(fields, "\n".join(block), len(records)))
                block, fields, last = [], {}, None
        elif last and line.strip():
            fields[last][-1] += " " + line.strip()
    return records


def read_medline(text: str) -> list[Record]:
    """PubMed/MEDLINE (.nbib): `TAG - value` with 6-space continuation lines; records are separated by blank lines."""
    records = []
    for block in re.split(r"\n\s*\n(?=PMID- )", text.replace("\r\n", "\n").strip("\n ")):
        fields, last = {}, None
        for line in block.splitlines():
            if m := MEDLINE_TAG.match(line):
                last = m.group(1)
                fields.setdefault(last, []).append(m.group(2).strip())
            elif last and line.startswith(" "):
                fields[last][-1] += " " + line.strip()
        if "PMID" in fields:
            rec = fields_record(fields, block.strip("\n"), len(records))
            rec.doi = next((v.split(" [doi]")[0] for v in fields.get("AID", []) + fields.get("LID", []) if v.endswith("[doi]")), "")
            records.append(rec)
    return records


def read_wos(text: str, enc: str, suffix: str) -> tuple[Export, list[Record]]:
    """Web of Science plain text: FN/VR header, `XX value`, 3-space continuation lines, ER ends a record, EF ends the file."""
    header, records, block, fields, last = [], [], [], {}, None
    for line in text.replace("\r\n", "\n").split("\n"):
        if not block and (line.startswith(("FN ", "VR ")) or not line.strip()):
            if not records and line.strip():
                header.append(line)
            continue
        if line.strip() == "EF":
            break
        block.append(line)
        if line.strip() == "ER":
            records.append(fields_record(fields, "\n".join(block), len(records), abstract_tags=("AB",), doi_tags=("DI",)))
            block, fields, last = [], {}, None
        elif m := WOS_TAG.match(line):
            last = m.group(1)
            fields.setdefault(last, []).append(m.group(2).strip())
        elif last and line.startswith("   "):
            fields[last][-1] += " " + line.strip()
    return Export("wos", suffix, enc, header="\n".join(header)), records


def read_csv(text: str, enc: str, suffix: str, name: str) -> tuple[Export, list[Record]]:
    first = text.split("\n", 1)[0]
    delimiter = "\t" if suffix == ".tsv" else max((",", ";", "\t"), key=first.count)
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter)
    rows = list(reader)
    export = Export("csv", suffix, enc, delimiter, columns=list(reader.fieldnames or []))
    if not rows:
        return export, []
    cols = {c.lower().strip(): c for c in export.columns}
    tcol = next((cols[c] for c in TITLE_COLUMNS if c in cols), None)
    acol = next((cols[c] for c in ABSTRACT_COLUMNS if c in cols), None)
    dcol = next((cols[c] for c in DOI_COLUMNS if c in cols), None)
    if not tcol:
        raise ValueError(f"{name}: no title column (looked for {', '.join(TITLE_COLUMNS)})")

    def cell(r: dict, c: str | None) -> str:
        return " ".join((r.get(c) or "").split()) if c else ""

    return export, [Record(cell(r, tcol), cell(r, acol), r, i, cell(r, dcol)) for i, r in enumerate(rows)]


def duplicate_of(records: list[Record]) -> dict[int, int]:
    """{index: index of the first record with the same DOI or the same normalised title} for every later copy."""
    first: dict[str, int] = {}
    out = {}
    for r in records:
        doi = r.doi.lower().strip().removeprefix("https://doi.org/").removeprefix("doi:")
        keys = [f"doi:{doi}"] if doi else []
        norm = re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", r.title).encode("ascii", "ignore").decode().lower())
        if len(norm) >= 20:
            keys.append(f"title:{norm}")
        hit = next((first[k] for k in keys if k in first), None)
        if hit is not None:
            out[r.index] = hit
        for k in keys:
            first.setdefault(k, r.index if hit is None else hit)
    return out


def write(path: Path, export: Export, records: list[Record]) -> None:
    if export.fmt == "csv":
        with path.open("w", encoding=export.encoding, errors="replace", newline="") as f:
            w = csv.DictWriter(f, fieldnames=export.columns, delimiter=export.delimiter, extrasaction="ignore")
            w.writeheader()
            w.writerows(r.raw for r in records)
        return
    blocks = [r.raw.rstrip("\n") for r in records]
    if export.fmt == "wos":
        text = (export.header + "\n" if export.header else "") + "\n\n".join(blocks) + ("\n\n" if blocks else "") + "EF\n"
    else:
        text = "\n\n".join(blocks) + ("\n" if blocks else "")
    path.write_text(text, encoding=export.encoding, errors="replace")
