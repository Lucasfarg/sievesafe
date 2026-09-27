#!/usr/bin/env python3
"""Build the external test set: CLEF TAR 2019 Task 2 Intervention test topics (20 Cochrane reviews). No API spend.

  clef_fetch.py [--cap 1000]                    Intervention topics → external/data/ (or $CLEF_DATA)
  clef_fetch.py --task dta --others 300         diagnostic test accuracy topics → external/data/dta/
  clef_fetch.py --task dta1718 --topics 40 --keep final --others 200     half of the CLEF 2017/2018 topics → data/dta1718/

Writes <topic>.csv and reviews.json. --others N: every include plus N other records per review, instead of --cap in all.
- Topics and labels: github.com/CLEF-TAR/tar at a pinned commit. Final labels = content-level qrels; title/abstract
  labels = abstract-level qrels.
- Records: every final or title/abstract include, plus a seeded sample of the other records up to --cap per review
  (random.Random(0) permutation, so a smaller cap is a prefix of a larger one); each sampled record weighs
  (others / sampled others). Titles and abstracts from PubMed (NCBI efetch).
- Eligibility criteria: the OBJECTIVES and SELECTION CRITERIA sections of the review's own abstract, from the latest
  version published up to 2019 (found with Europe PMC, text from PubMed). Results sections are left out."""
import argparse
import collections
import csv
import json
import os
import random
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("CLEF_DATA", HERE / "data")).expanduser()
CLEF_COMMIT = "dbc13d02bb3e2f8ebc90e62ff47f5eb591e5ca20"
RAW = f"https://raw.githubusercontent.com/CLEF-TAR/tar/{CLEF_COMMIT}"
T19 = "2019-TAR/Task2/Testing"
SOURCES = {  # task → [(content qrels, abstract qrels, CLEF edition year)]
    "intervention": [(f"{T19}/Intervention/qrels/full.test.intervention.content.2019.qrels", f"{T19}/Intervention/qrels/full.test.intervention.abs.2019.qrels", 2019)],
    "dta": [(f"{T19}/DTA/qrels/full.test.dta.content.2019.qrels", f"{T19}/DTA/qrels/full.test.dta.abs.2019.qrels", 2019)],
    "dta1718": [("2017-TAR/testing/qrels/qrel_content_test.txt", "2017-TAR/testing/qrels/qrel_abs_test.txt", 2017),
                ("2017-TAR/training/qrels/qrel_content_train", "2017-TAR/training/qrels/qrel_abs_train", 2017),
                ("2018-TAR/Task2/Testing/qrels/full.test.content.2018.qrels", "2018-TAR/Task2/Testing/qrels/full.test.abs.2018.qrels", 2018)],
}
EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
EPMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def get(url: str, data: dict | None = None, tries: int = 5) -> bytes:
    body = urllib.parse.urlencode(data).encode() if data else None
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers={"User-Agent": "sievesafe-benchmark"}), timeout=60) as r:
                return r.read()
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(2 ** i)
    raise RuntimeError(url)


def qrels(path: str) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = collections.defaultdict(dict)
    for line in get(f"{RAW}/{path}").decode().splitlines():
        topic, _, pmid, rel = line.split()
        out[topic][pmid] = int(rel)
    return out


def text(el) -> str:
    return " ".join("".join(el.itertext()).split()) if el is not None else ""


def pubmed(pmids: list[str]) -> dict[str, ET.Element]:
    out = {}
    for i in range(0, len(pmids), 200):
        root = ET.fromstring(get(EFETCH, {"db": "pubmed", "retmode": "xml", "id": ",".join(pmids[i:i + 200])}))
        for art in root.iter("PubmedArticle"):
            out[art.findtext(".//MedlineCitation/PMID")] = art
        for art in root.iter("PubmedBookArticle"):
            out[art.findtext(".//BookDocument/PMID")] = art
        time.sleep(0.4)  # NCBI allows 3 requests/s without a key
    return out


def title_abstract(art: ET.Element) -> tuple[str, str]:
    title = text(art.find(".//ArticleTitle")) or text(art.find(".//BookTitle"))
    parts = [(a.get("Label"), text(a)) for a in art.iter("AbstractText")]
    return title, " ".join(f"{label}: {t}" if label else t for label, t in parts if t)


def review(topic: str, year: int = 2019) -> dict:
    """The latest version of the Cochrane review published up to the CLEF edition's year, with objectives and selection criteria."""
    q = urllib.parse.urlencode({"query": f'"{topic}" AND ISSN:1469-493X', "format": "json", "resultType": "lite", "pageSize": 50})
    hits = [h for h in json.loads(get(f"{EPMC}?{q}"))["resultList"]["result"]
            if h.get("pmid") and topic.lower() in (h.get("doi") or "").lower() and int(h.get("pubYear") or 0) <= year]
    best = max(hits, key=lambda h: (int(h["pubYear"]), h["doi"]))
    art = pubmed([best["pmid"]])[best["pmid"]]
    sections = {a.get("Label"): text(a) for a in art.iter("AbstractText")}
    criteria = f"Objectives: {sections.get('OBJECTIVES', '')}\n\nSelection criteria: {sections.get('SELECTION CRITERIA', '')}"
    return {"review_pmid": best["pmid"], "doi": best["doi"], "year": int(best["pubYear"]), "title": text(art.find(".//ArticleTitle")).rstrip("."),
            "criteria": criteria, "has_selection_criteria": "SELECTION CRITERIA" in sections}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--task", choices=list(SOURCES), default="intervention")
    p.add_argument("--cap", type=int, default=1000)
    p.add_argument("--others", type=int)
    p.add_argument("--keep", choices=["either", "final"], default="either", help="always keep includes at either level, or final ones only")
    p.add_argument("--topics", type=int, help="a seeded random sample of this many topics (random.Random(0), sorted ids)")
    a = p.parse_args()
    out = DATA if a.task == "intervention" else DATA / a.task
    out.mkdir(parents=True, exist_ok=True)
    final, abstract, year = {}, {}, {}
    for content, abs_, edition in SOURCES[a.task]:
        for topic, labels in qrels(content).items():
            final.setdefault(topic, labels)
            year.setdefault(topic, edition)
        for topic, labels in qrels(abs_).items():
            abstract.setdefault(topic, labels)
    used = set()
    for other in SOURCES:
        path = DATA / "reviews.json" if other == "intervention" else DATA / other / "reviews.json"
        if other != a.task and path.exists():
            used |= set(json.loads(path.read_text())["reviews"])
    topics = sorted(t for t in final if t not in used)
    if a.topics:
        topics = sorted(random.Random(0).sample(topics, a.topics))
    meta = {}
    for topic in topics:
        labels = final[topic]
        abs_labels = abstract.get(topic, {}) if a.keep == "either" else {}
        keep = [m for m in labels if labels[m] or abs_labels.get(m)]
        others = [m for m in labels if not (labels[m] or abs_labels.get(m))]
        room = a.others if a.others is not None else max(a.cap - len(keep), 0)
        sample = random.Random(0).sample(others, len(others))[:room]
        weight = len(others) / len(sample) if sample else 1.0
        arts = pubmed(keep + sample)
        rows = []
        for m in keep + sample:
            t, ab = title_abstract(arts[m]) if m in arts else ("", "")
            rows.append({"pmid": m, "title": t, "abstract": ab, "y": labels[m], "ya": abstract.get(topic, {}).get(m, 0),
                         "w": 1.0 if m in keep else weight, "in_pubmed": int(m in arts)})
        with (out / f"{topic}.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        meta[topic] = {**review(topic, year[topic]), "edition": year[topic], "records_total": len(labels), "includes": sum(labels.values()),
                       "abstract_includes": sum(abstract.get(topic, {}).values()), "sampled": len(rows), "missing_from_pubmed": sum(1 - r["in_pubmed"] for r in rows),
                       "no_abstract": sum(1 for r in rows if not r["abstract"])}
        print(f"{topic}: {len(rows)}/{len(labels)} records, {meta[topic]['includes']} includes, criteria from {meta[topic]['doi']}", flush=True)
    (out / "reviews.json").write_text(json.dumps({"clef_commit": CLEF_COMMIT, "task": a.task, "cap": a.cap, "others": a.others, "keep": a.keep,
                                                  "topics": a.topics, "excluded_as_used": sorted(used & set(final)), "reviews": meta}, indent=1) + "\n")


if __name__ == "__main__":
    main()
