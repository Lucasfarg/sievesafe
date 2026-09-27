"""`sievesafe serve`: a local page for people who would rather not use a terminal. Standard library only.

The server listens on 127.0.0.1 only and keeps the API key to itself. Every /api request must carry the token that is
written into the page it served (a custom header, so another website cannot send it without a CORS preflight, which this
server never grants) and a Host of 127.0.0.1/localhost (against DNS rebinding). One run at a time.

  GET  /                              the page
  POST /api/runs                      {filename, data: base64 file, title, criteria, mode[, validated]} → estimate (nothing spent)
  POST /api/runs/<id>/start           {budget} → starts scoring; budget ≤ --max-budget
  GET  /api/runs/<id>                 progress, then the summary and the file names
  GET  /api/runs/<id>/files/<name>    one output file, as a download"""
from __future__ import annotations

import base64
import binascii
import json
import re
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path

from sievesafe import MODEL, SAFE_THRESHOLD, __version__, jev, run

MAX_UPLOAD = 60 * 1024 * 1024
CONTENT_TYPES = {".csv": "text/csv", ".tsv": "text/tab-separated-values", ".ris": "application/x-research-info-systems",
                 ".txt": "text/plain", ".nbib": "text/plain", ".md": "text/markdown"}


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int, workdir: Path, max_budget: float, key_file: Path | None = None):
        super().__init__(("127.0.0.1", port), Handler)
        self.workdir, self.max_budget, self.key_file = workdir, max_budget, key_file
        self.token = secrets.token_urlsafe(24)
        self.runs: dict[str, dict] = {}
        self.lock = threading.Lock()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server_address[1]}/"

    def key(self) -> str | None:
        try:
            return jev.api_key(self.key_file)
        except jev.JevError:
            return None


class Handler(BaseHTTPRequestHandler):
    server: Server

    def log_message(self, fmt, *args) -> None:  # quiet: the terminal shows only what the user needs
        pass

    def send(self, status: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def json(self, status: int, data: dict) -> None:
        self.send(status, json.dumps(data).encode(), "application/json")

    def allowed(self, api: bool) -> bool:
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        if host not in ("127.0.0.1", "localhost"):
            self.json(403, {"error": "this server only answers on 127.0.0.1"})
            return False
        if api and not secrets.compare_digest(self.headers.get("X-Sievesafe-Token") or "", self.server.token):
            self.json(403, {"error": "missing or wrong token: reload the page"})
            return False
        return True

    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/":
            if self.allowed(api=False):
                page = resources.files("sievesafe").joinpath("page.html").read_text(encoding="utf-8")
                page = page.replace("__TOKEN__", self.server.token).replace("__VERSION__", __version__)
                page = page.replace("__MODEL__", MODEL).replace("__THRESHOLD__", str(SAFE_THRESHOLD))
                self.send(200, page.encode(), "text/html; charset=utf-8", {
                    "Content-Security-Policy": "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                                               "connect-src 'self'; img-src data:; form-action 'none'; base-uri 'none'"})
            return
        if not self.allowed(api=True):
            return
        if m := re.fullmatch(r"/api/runs/(\w+)", path):
            if job := self.server.runs.get(m.group(1)):
                return self.json(200, public(job))
        elif m := re.fullmatch(r"/api/runs/(\w+)/files/([\w.-]+)", path):
            job = self.server.runs.get(m.group(1))
            if job and job["state"] == "done" and m.group(2) in job["summary"]["files"]:
                f = job["run"].out / m.group(2)
                name = f"{job['run'].source.stem}-{m.group(2)}"
                return self.send(200, f.read_bytes(), CONTENT_TYPES.get(f.suffix, "application/octet-stream") + "; charset=utf-8",
                                 {"Content-Disposition": f'attachment; filename="{name}"'})
        self.json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self.allowed(api=True):
            return
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD:
            return self.json(413, {"error": f"file too large (limit {MAX_UPLOAD // 2**20} MB)"})
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return self.json(400, {"error": "expected JSON"})
        path = self.path.split("?", 1)[0]
        if path == "/api/runs":
            return self.create(body)
        if m := re.fullmatch(r"/api/runs/(\w+)/start", path):
            return self.start(m.group(1), body)
        self.json(404, {"error": "not found"})

    def create(self, body: dict) -> None:
        name = Path(str(body.get("filename") or "")).name
        stem, suffix = Path(name).stem, Path(name).suffix.lower()
        if suffix not in (".ris", ".txt", ".nbib", ".csv", ".tsv"):
            return self.json(400, {"error": "choose a .ris, .nbib, .txt or .csv export from your search"})
        try:
            data = base64.b64decode(str(body.get("data") or ""), validate=True)
        except (binascii.Error, ValueError):
            return self.json(400, {"error": "the file did not arrive intact; try again"})
        if body.get("mode") == "exclude" and body.get("validated") is not True:
            return self.json(400, {"error": "Exclude needs your commitment to validate the removed records locally (RAISE)"})
        safe_stem = re.sub(r"[^\w.-]+", "_", stem).strip("._")[:60] or "search"
        folder = self.server.workdir / f"{safe_stem}-sievesafe"
        folder.mkdir(parents=True, exist_ok=True)
        source = folder / f"input{suffix}"
        source.write_bytes(data)
        try:
            job = run.prepare(source, str(body.get("title") or ""), str(body.get("criteria") or ""), str(body.get("mode") or "rank"), folder)
        except ValueError as e:
            return self.json(400, {"error": str(e).replace("input" + suffix, name)})
        job.source = folder / (safe_stem + suffix)
        source.replace(job.source)
        run_id = secrets.token_hex(6)
        with self.server.lock:
            self.server.runs[run_id] = {"id": run_id, "run": job, "state": "estimated", "done": 0, "total": len(job.todo), "error": None, "summary": None}
        self.json(200, public(self.server.runs[run_id]) | {
            "has_key": bool(self.server.key()) or not job.todo, "max_budget": self.server.max_budget})

    def start(self, run_id: str, body: dict) -> None:
        job = self.server.runs.get(run_id)
        if not job:
            return self.json(404, {"error": "unknown run: upload the file again"})
        try:
            budget = float(body.get("budget"))
        except (TypeError, ValueError):
            return self.json(400, {"error": "give a budget in US$"})
        if not 0 <= budget <= self.server.max_budget:
            return self.json(400, {"error": f"the budget must be between 0 and US$ {self.server.max_budget:.2f} (--max-budget)"})
        key = self.server.key() if job["run"].todo else ""
        if key is None:
            return self.json(400, {"error": "no TypeSafe API key: set TYPESAFE_API_KEY or put it in ~/.config/sievesafe/typesafe.env"})
        with self.server.lock:
            if any(j["state"] == "running" for j in self.server.runs.values()):
                return self.json(409, {"error": "another run is in progress; wait for it to finish"})
            if job["state"] != "estimated":
                return self.json(409, {"error": "this run was already started; upload the file again for a new one"})
            job["state"] = "running"
        threading.Thread(target=work, args=(job, key, budget), daemon=True).start()
        self.json(202, public(job))


def work(job: dict, key: str, budget: float) -> None:
    def progress(done: int, total: int) -> None:
        job["done"], job["total"] = done, total

    try:
        job["summary"] = run.execute(job["run"], key, budget, progress)
        job["state"] = "done"
    except (jev.JevError, OSError, ValueError) as e:
        job["error"], job["state"] = str(e), "error"


def public(job: dict) -> dict:
    r = job["run"]
    return {"id": job["id"], "state": job["state"], "done": job["done"], "total": job["total"], "error": job["error"],
            "summary": job["summary"], "records": len(r.recs), "no_abstract": r.no_abstract, "duplicates": r.duplicates, "cached": len(r.recs) - len(r.todo),
            "estimate": r.estimate, "mode": r.mode, "format": r.fmt}


def serve(port: int, workdir: Path, max_budget: float, key_file: Path | None, open_browser: bool) -> None:
    server = Server(port, workdir.resolve(), max_budget, key_file)
    print(f"sievesafe {__version__} on {server.url}  (results in {server.workdir}/; Ctrl+C to stop)", flush=True)
    if not server.key():
        print("no TypeSafe API key found: set TYPESAFE_API_KEY or put TYPESAFE_API_KEY=... in ~/.config/sievesafe/typesafe.env")
    if open_browser:
        webbrowser.open(server.url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
