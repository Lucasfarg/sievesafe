"""Search exports as the databases write them (hand-written fictional fixtures in tests/fixtures), and writing them back."""
import csv
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from test_sievesafe import CRITERIA, fake_ask

from sievesafe import cli, records

FIX = Path(__file__).resolve().parent / "fixtures"


def roundtrip(name: str) -> tuple[records.Export, list, list, bytes]:
    """Read a fixture, write every record back, read that again → (export, records, records again, written bytes)."""
    export, recs = records.read(FIX / name)
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / f"out{export.suffix}"
        records.write(out, export, recs)
        return export, recs, records.read(out)[1], out.read_bytes()


class Formats(unittest.TestCase):
    def test_pubmed_medline(self):
        export, recs, again, _ = roundtrip("pubmed.nbib")
        self.assertEqual(export.fmt, "medline")
        self.assertEqual([r.title for r in recs], ["Emicizumab prophylaxis in children with haemophilia A: a multicentre cohort study.",
                                                   "Letter: dosing of factor VIII concentrates.", "Cooking habits of university students."])
        self.assertTrue(recs[0].abstract.startswith("BACKGROUND:") and recs[0].abstract.endswith("fell from 4.1 to 0.6."))
        self.assertEqual((recs[1].abstract, recs[0].doi, recs[2].doi), ("", "10.9999/fict.2021.001", "10.9999/fict.2022.003"))
        self.assertEqual([r.raw for r in again], [r.raw for r in recs])

    def test_pubmed_medline_saved_as_txt(self):
        with tempfile.TemporaryDirectory() as d:
            shutil.copy(FIX / "pubmed.nbib", Path(d) / "pubmed-export.txt")
            export, recs = records.read(Path(d) / "pubmed-export.txt")
        self.assertEqual((export.fmt, export.suffix, len(recs)), ("medline", ".txt", 3))

    def test_scopus_ris(self):
        export, recs, again, _ = roundtrip("scopus.ris")
        self.assertEqual((export.fmt, len(recs)), ("ris", 2))
        self.assertEqual(recs[0].doi, "10.9999/fict.2023.010")
        self.assertIn("40 infants", recs[0].abstract)
        self.assertEqual((recs[1].title, recs[1].abstract), ("Réunion annuelle: résumé des communications", ""))
        self.assertEqual([r.raw for r in again], [r.raw for r in recs])

    def test_web_of_science_plain_text(self):
        export, recs, again, written = roundtrip("wos.txt")
        self.assertEqual((export.fmt, len(recs)), ("wos", 2))
        self.assertEqual(recs[0].title, "Long-term safety of emicizumab in adults with haemophilia A and inhibitors")
        self.assertEqual(recs[0].doi, "10.9999/fict.2020.020")
        self.assertIn("No thrombotic events", recs[0].abstract)
        text = written.decode()
        self.assertTrue(text.startswith("FN Clarivate Analytics Web of Science\nVR 1.0\nPT J"), text[:60])
        self.assertTrue(text.endswith("ER\n\nEF\n"))
        self.assertEqual([r.title for r in again], [r.title for r in recs])

    def test_rayyan_ris_with_windows_line_endings(self):
        _export, recs, again, _ = roundtrip("rayyan.ris")
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0].abstract, "Sixty patients were randomised to emicizumab or factor VIII prophylaxis for 48 weeks.")
        self.assertIn("RAYYAN-INCLUSION", recs[0].raw)  # the reviewer's decisions travel back untouched
        self.assertEqual(len(again), 2)

    def test_rayyan_csv_with_quotes_and_newlines(self):
        export, recs, again, _ = roundtrip("rayyan.csv")
        self.assertEqual((export.fmt, export.delimiter, len(recs)), ("csv", ",", 2))
        self.assertEqual(recs[0].abstract, 'Five patients, aged 6 to 40, were treated. One had a "breakthrough" bleed. Follow-up was 12 months.')
        self.assertEqual((recs[0].doi, recs[1].abstract), ("10.9999/fict.2022.040", ""))
        self.assertEqual([r.raw for r in again], [r.raw for r in recs])

    def test_semicolon_latin1_csv_is_written_back_the_same_way(self):
        export, recs, _again, written = roundtrip("excel-semicolon-latin1.csv")
        self.assertEqual((export.delimiter, len(recs)), (";", 2))
        self.assertNotEqual(export.encoding, "utf-8")
        self.assertEqual(recs[0].title, "Emicizumabe em crianças: estudo de coorte")
        self.assertEqual(recs[0].abstract, "Avaliação de 50 crianças tratadas com emicizumabe; sangramentos reduziram.")
        self.assertEqual(written, (FIX / "excel-semicolon-latin1.csv").read_bytes().replace(b"\n", b"\r\n"))

    def test_utf8_bom_survives(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "bom.csv"
            p.write_bytes(b"\xef\xbb\xbfTitle,Abstract\nCaf\xc3\xa9 study,text\n")
            export, recs = records.read(p)
            records.write(Path(d) / "out.csv", export, recs)
            self.assertEqual(recs[0].title, "Café study")
            self.assertTrue((Path(d) / "out.csv").read_bytes().startswith(b"\xef\xbb\xbfTitle,Abstract"))

    def test_duplicates_by_doi_or_title(self):
        _, recs = records.read(FIX / "rayyan.ris")
        self.assertEqual(records.duplicate_of(recs), {1: 0})
        a = records.Record("Emicizumab pharmacokinetics in children, a study", "x", "", 0)
        b = records.Record("EMICIZUMAB PHARMACOKINETICS IN CHILDREN: A STUDY.", "", "", 1)
        c = records.Record("Short", "", "", 2)
        d = records.Record("Short", "", "", 3)  # too short a title to call it a duplicate
        self.assertEqual(records.duplicate_of([a, b, c, d]), {1: 0})

    def test_unknown_extension_is_refused(self):
        with self.assertRaises(ValueError):
            records.read(Path("search.pdf"))


@mock.patch("sievesafe.jev.ask", side_effect=fake_ask)
@mock.patch("sievesafe.jev.api_key", return_value="test-key")
class ScreenFormats(unittest.TestCase):
    def screen(self, name: str, *extra: str) -> Path:
        d = Path(self.enterContext(tempfile.TemporaryDirectory()))
        shutil.copy(FIX / name, d / name)
        (d / "criteria.txt").write_text(CRITERIA, encoding="utf-8")
        self.assertEqual(cli.main(["screen", str(d / name), "--criteria", str(d / "criteria.txt"), "--title", "Emicizumab", "--yes", *extra]), 0)
        return d / (Path(name).stem + "-sievesafe")

    def test_outputs_keep_the_input_format(self, _key, ask):
        out = self.screen("wos.txt", "--mode", "exclude")
        self.assertEqual(sorted(p.name for p in out.iterdir() if not p.name.startswith(".")),
                         ["excluded.txt", "ranked.csv", "report.md", "to-screen.txt", "validation-sample.txt"])
        self.assertEqual(records.read(out / "to-screen.txt")[0].fmt, "wos")
        self.assertEqual([r.title for r in records.read(out / "excluded.txt")[1]], ["Soil microbiome in tropical forests"])

    def test_duplicates_are_scored_once_and_both_kept(self, _key, ask):
        out = self.screen("rayyan.ris")
        self.assertEqual(ask.call_count, 1)
        ranked = list(csv.DictReader((out / "ranked.csv").open(encoding="utf-8")))
        self.assertEqual({r["probability"] for r in ranked}, {"0.9000"})
        self.assertEqual(sorted(r["duplicate_of"] for r in ranked), ["", "1"])
        self.assertEqual(len(records.read(out / "to-screen.ris")[1]), 2)
        self.assertIn("Duplicates (same DOI or title as another record): 1", (out / "report.md").read_text())

    def test_records_without_abstract_are_never_excluded(self, _key, ask):
        out = self.screen("pubmed.nbib", "--mode", "exclude")
        ranked = {r["title"]: r["flag"] for r in csv.DictReader((out / "ranked.csv").open(encoding="utf-8"))}
        self.assertEqual(ranked["Letter: dosing of factor VIII concentrates."], "no abstract, kept")
        self.assertEqual(ranked["Cooking habits of university students."], "excluded")
        self.assertEqual([r.title for r in records.read(out / "excluded.nbib")[1]], ["Cooking habits of university students."])

    def test_a_copy_without_abstract_is_kept_when_its_twin_is_excluded(self, _key, ask):
        d = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (d / "dup.ris").write_text("TY  - JOUR\nTI  - A survey of cooking habits at university\nAB  - Students cook.\nDO  - 10.9999/x\nER  - \n\n"
                                   "TY  - JOUR\nTI  - A survey of cooking habits at university\nDO  - 10.9999/x\nER  - \n", encoding="utf-8")
        (d / "criteria.txt").write_text(CRITERIA, encoding="utf-8")
        cli.main(["screen", str(d / "dup.ris"), "--criteria", str(d / "criteria.txt"), "--title", "E", "--yes", "--mode", "exclude"])
        out = d / "dup-sievesafe"
        self.assertEqual(len(records.read(out / "excluded.ris")[1]), 1)
        self.assertEqual([r.abstract for r in records.read(out / "to-screen.ris")[1]], [""])

    def test_latin1_semicolon_csv_end_to_end(self, _key, ask):
        out = self.screen("excel-semicolon-latin1.csv", "--mode", "exclude")
        data = (out / "to-screen.csv").read_bytes()
        self.assertTrue(data.startswith(b"Title;Abstract;Year"))
        self.assertIn("crianças".encode("latin-1"), data)


if __name__ == "__main__":
    unittest.main()
