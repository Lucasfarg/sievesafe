"""`sievesafe serve` endpoints, against a real server on a free port with Jev mocked."""
import base64
import http.client
import json
import re
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from test_sievesafe import CRITERIA, RIS, fake_ask

from sievesafe import jev, records, serve


class Serve(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patches = [mock.patch("sievesafe.jev.ask", side_effect=fake_ask), mock.patch("sievesafe.jev.api_key", return_value="test-key")]
        self.ask = patches[0].start()
        patches[1].start()
        for p in patches:
            self.addCleanup(p.stop)
        self.server = serve.Server(0, Path(self.tmp.name), max_budget=1.0)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.port = self.server.server_address[1]

    def request(self, method, path, body=None, token=True, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Host": host or f"127.0.0.1:{self.port}", "Content-Type": "application/json"}
        if token:
            headers["X-Sievesafe-Token"] = self.server.token
        conn.request(method, path, body=json.dumps(body).encode() if body is not None else None, headers=headers)
        res = conn.getresponse()
        data = res.read()
        conn.close()
        return res.status, dict(res.getheaders()), data

    def upload(self, name="my search.ris", content=RIS, mode="rank", **extra):
        body = {"filename": name, "data": base64.b64encode(content.encode()).decode(), "title": "Emicizumab PK",
                "criteria": CRITERIA, "mode": mode, **extra}
        status, _, data = self.request("POST", "/api/runs", body)
        return status, json.loads(data)

    def finish(self, run_id, budget=0.5):
        status, _, data = self.request("POST", f"/api/runs/{run_id}/start", {"budget": budget})
        self.assertEqual(status, 202, data)
        for _ in range(100):
            job = json.loads(self.request("GET", f"/api/runs/{run_id}")[2])
            if job["state"] != "running":
                return job
            time.sleep(0.05)
        self.fail("run did not finish")

    def test_page_is_self_contained_and_carries_the_token(self):
        status, headers, data = self.request("GET", "/", token=False)
        page = data.decode()
        self.assertEqual(status, 200)
        self.assertIn(self.server.token, page)
        self.assertIn("default-src 'none'", headers["Content-Security-Policy"])
        self.assertNotRegex(page, r"(src|href)\s*=\s*[\"']?(https?:)?//|url\(\s*[\"']?(https?:)?//|@import")
        self.assertFalse(re.findall(r"__(TOKEN|VERSION|MODEL|THRESHOLD)__", page))

    def test_api_needs_the_token_and_a_local_host(self):
        self.assertEqual(self.request("GET", "/api/runs/abc", token=False)[0], 403)
        self.assertEqual(self.request("POST", "/api/runs", {}, token=False)[0], 403)
        self.assertEqual(self.request("GET", "/", host="evil.example:80")[0], 403)
        self.assertEqual(self.request("POST", "/api/runs", {}, host=f"attacker.test:{self.port}")[0], 403)
        self.assertEqual(self.ask.call_count, 0)

    def test_estimate_then_rank_run_and_download(self):
        status, est = self.upload()
        self.assertEqual(status, 200, est)
        self.assertEqual((est["records"], est["no_abstract"], est["cached"], est["state"]), (3, 1, 0, "estimated"))
        self.assertGreater(est["estimate"], 0)
        self.assertEqual(self.ask.call_count, 0)  # estimating spends nothing
        job = self.finish(est["id"])
        self.assertEqual(job["state"], "done", job)
        self.assertEqual(job["summary"]["files"], ["ranked.csv", "to-screen.ris", "report.md"])
        status, headers, data = self.request("GET", f"/api/runs/{est['id']}/files/ranked.csv")
        self.assertEqual(status, 200)
        self.assertIn('filename="my_search-ranked.csv"', headers["Content-Disposition"])
        self.assertTrue(data.decode().splitlines()[1].endswith("Emicizumab pharmacokinetics in children"))
        report = self.request("GET", f"/api/runs/{est['id']}/files/report.md")[2].decode()
        self.assertIn("`my_search.ris`", report)
        self.assertEqual(len(records.read_ris(self.request("GET", f"/api/runs/{est['id']}/files/to-screen.ris")[2].decode())), 3)

    def test_exclude_needs_the_validation_commitment(self):
        status, err = self.upload(mode="exclude")
        self.assertEqual(status, 400)
        self.assertIn("RAISE", err["error"])
        status, est = self.upload(mode="exclude", validated=True)
        job = self.finish(est["id"])
        self.assertEqual((job["summary"]["excluded"], job["summary"]["files"][2:4]), (1, ["excluded.ris", "validation-sample.ris"]))
        self.assertEqual(len(records.read_ris(self.request("GET", f"/api/runs/{est['id']}/files/excluded.ris")[2].decode())), 1)

    def test_budget_limits_and_one_start_per_run(self):
        _, est = self.upload()
        self.assertEqual(self.request("POST", f"/api/runs/{est['id']}/start", {"budget": 5})[0], 400)  # above --max-budget
        self.assertEqual(self.request("POST", f"/api/runs/{est['id']}/start", {"budget": "lots"})[0], 400)
        self.finish(est["id"])
        self.assertEqual(self.request("POST", f"/api/runs/{est['id']}/start", {"budget": 0.5})[0], 409)

    def test_a_second_upload_of_the_same_file_costs_nothing(self):
        _, est = self.upload()
        self.finish(est["id"])
        calls = self.ask.call_count
        _, again = self.upload()
        self.assertEqual((again["cached"], again["estimate"]), (3, 0))
        self.assertEqual(self.finish(again["id"])["state"], "done")
        self.assertEqual(self.ask.call_count, calls)

    def test_bad_inputs_get_a_plain_message(self):
        self.assertEqual(self.upload(name="search.pdf")[0], 400)
        status, err = self.upload(content="nothing useful here")
        self.assertEqual((status, err["error"]), (400, "my search.ris: no records found"))
        body = {"filename": "s.ris", "data": base64.b64encode(RIS.encode()).decode(), "title": "t", "criteria": "short", "mode": "rank"}
        self.assertIn("criteria", json.loads(self.request("POST", "/api/runs", body)[2])["error"])
        self.assertEqual(self.request("POST", "/api/runs", {**body, "data": "***"})[0], 400)

    def test_files_are_only_the_outputs_of_a_finished_run(self):
        _, est = self.upload()
        self.assertEqual(self.request("GET", f"/api/runs/{est['id']}/files/ranked.csv")[0], 404)  # not started
        self.finish(est["id"])
        for name in ("input.ris", ".sievesafe-cache.tsv", "..%2F..%2Fetc%2Fpasswd", "my_search.ris"):
            self.assertEqual(self.request("GET", f"/api/runs/{est['id']}/files/{name}")[0], 404, name)

    def test_an_unexpected_failure_does_not_leave_the_server_stuck(self):
        _, est = self.upload()
        self.ask.side_effect = RuntimeError("boom")
        job = self.finish(est["id"])
        self.assertEqual(job["state"], "error")
        self.ask.side_effect = fake_ask
        _, again = self.upload()
        self.assertEqual(self.finish(again["id"])["state"], "done")  # a new run can start

    def test_negative_content_length_is_refused(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.putrequest("POST", "/api/runs")
        for k, v in {"Host": f"127.0.0.1:{self.port}", "X-Sievesafe-Token": self.server.token, "Content-Length": "-1"}.items():
            conn.putheader(k, v)
        conn.endheaders()
        self.assertEqual(conn.getresponse().status, 400)
        conn.close()

    def test_no_key_blocks_spending(self):
        _, est = self.upload()
        with mock.patch("sievesafe.jev.api_key", side_effect=jev.JevError("no key")):
            status, _, data = self.request("POST", f"/api/runs/{est['id']}/start", {"budget": 0.5})
            self.assertEqual(status, 400)
            self.assertIn("API key", json.loads(data)["error"])


if __name__ == "__main__":
    unittest.main()
