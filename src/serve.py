"""Local demo server: serves web/ and runs the real pipeline on an enquiry typed into the page.

Run:  python src/serve.py        then open http://localhost:8000

Every "Run" spends real API money (about 2 AU cents), so this only ever listens on
this computer. The hosted page has no server; it shows the saved runs only.
"""
import json
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import llm
import pipeline
from run_all import to_record

ROOT = Path(__file__).resolve().parent.parent
PORT = 8000
DEMO_PROFILE = "kitchens_joinery"  # the one business the demo page shows
MAX_CHARS = 4000                   # a real enquiry is far shorter; caps the cost of one run
PROFILE = json.loads((ROOT / "profiles" / f"{DEMO_PROFILE}.json").read_text(encoding="utf-8"))


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/run":
            return self.send_error(404)
        # Two checks so other websites open in your browser can't spend your key:
        # a JSON content type forces the browser to ask permission first (which we never give),
        # and the Host check stops a hostile domain pointed at 127.0.0.1.
        if self.headers.get("Content-Type") != "application/json" or \
                self.headers.get("Host") not in (f"localhost:{PORT}", f"127.0.0.1:{PORT}"):
            return self.send_error(403)
        try:
            text = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))["text"].strip()
        except (ValueError, KeyError, TypeError, AttributeError):
            return self._json(400, {"error": "Send {\"text\": \"...\"}."})
        if not text or len(text) > MAX_CHARS:
            return self._json(400, {"error": f"Enquiry must be 1-{MAX_CHARS} characters."})

        start = time.perf_counter()
        try:
            result = pipeline.run("custom", text, PROFILE)
        except Exception as e:  # API down, refusal, cut-off answer: show it, don't crash the server
            return self._json(502, {"error": f"The pipeline failed: {e}"})
        finally:
            llm.flush()
        record = to_record(result, time.perf_counter() - start)
        record["text"] = text
        self._json(200, record)

    def _json(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Handler, directory=str(ROOT / "web")))
    print(f"Serving http://localhost:{PORT}  (Ctrl+C to stop)")
    server.serve_forever()
