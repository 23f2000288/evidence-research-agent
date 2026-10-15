"""Local demonstration viewer. Binds only to loopback; no third-party services."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import subprocess
import sys
import threading
import time
from agent import ROOT, SECTIONS

process = None
live_folder = None
lock = threading.Lock()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def state():
    runs = []
    for name in ("v1", "v2", "v3"):
        folder = ROOT / "runs" / name
        runs.append({"name": name, "run": read_json(folder / "run.json"),
                     "evaluation": read_json(folder / "evaluation.json"),
                     "validation": read_json(folder / "validation.json")})
    result = read_json(ROOT / "runs/v3/result.json")
    docs = read_json(ROOT / "runs/v3/documents.json")
    live = {"status": "idle", "log": "Click Run agent to launch a fresh model-backed run."}
    if live_folder:
        live = read_json(live_folder / "run.json") or {"status": "starting"}
        live["folder"] = live_folder.name
        live["log"] = (live_folder.parent / f"{live_folder.name}.log").read_text(encoding="utf-8", errors="replace")
        live["result"] = read_json(live_folder / "result.json")
    return {"runs": runs, "result": result, "documents": docs, "live": live}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self, body, content_type="application/json", status=200):
        if not isinstance(body, bytes):
            body = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/api/state":
            return self.respond(json.dumps(state(), ensure_ascii=False))
        if path == "/brief.md":
            return self.respond((ROOT / "runs/v3/brief.md").read_bytes(), "text/markdown")
        if path in ("/", "/index.html"):
            return self.respond((ROOT / "demo/index.html").read_bytes(), "text/html")
        self.respond("Not found", "text/plain", 404)

    def do_POST(self):
        global process, live_folder
        # Same-origin POST only; a remote website cannot trigger model runs.
        origin = self.headers.get("Origin", "")
        if origin and origin not in {"http://127.0.0.1:8765", "http://localhost:8765"}:
            return self.respond('{"error":"Invalid origin"}', status=403)
        if self.path != "/api/start":
            return self.respond("Not found", "text/plain", 404)
        with lock:
            if process and process.poll() is None:
                return self.respond('{"status":"already running"}')
            live_folder = ROOT / "runs" / f"demo-{time.time_ns()}"
            log = (live_folder.parent / f"{live_folder.name}.log").open("w", encoding="utf-8")
            process = subprocess.Popen([sys.executable, "-u", str(ROOT / "agent.py"),
                                        "--ticker", "SRVCABLE", "--as-of", "2026-09-23",
                                        "--out", str(live_folder)],
                                       cwd=ROOT, stdout=log, stderr=log,
                                       env={**__import__('os').environ, "PYTHONIOENCODING": "utf-8"},
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            log.close()
        self.respond('{"status":"started"}')


if __name__ == "__main__":
    print("Research Agent demo: http://127.0.0.1:8765", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
