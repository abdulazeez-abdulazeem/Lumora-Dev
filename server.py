"""
Lumora Dev – static file server + reverse proxy.
Serves frontend/ on port 5000.
Forwards /chat, /files, /file, /folder and all API paths to the FastAPI backend on port 8000.
"""
import http.server
import socketserver
import os
import urllib.request
import urllib.error
import json

PORT = 5000
API_PORT = 8000
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

# Any request whose path starts with one of these is proxied to FastAPI
PROXY_PATHS = (
    "/chat", "/files", "/file", "/folder",
    "/terminal", "/settings", "/git", "/github",
    "/activity", "/workspaces", "/codebase", "/db",
    "/auth", "/memory", "/planner", "/edits", "/browser",
)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def log_message(self, fmt, *args):
        # Suppress default access logs for a cleaner console
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    # ── CORS pre-flight ──────────────────────────────────────────────────
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── Helper: decide whether this path belongs to FastAPI ─────────────
    def _is_api(self):
        bare = self.path.split("?")[0]
        return any(bare == p or bare.startswith(p + "?") or bare.startswith(p + "/")
                   for p in PROXY_PATHS)

    # ── Helper: forward the request to FastAPI ───────────────────────────
    def _proxy(self, method: str, body: bytes | None = None):
        target = f"http://127.0.0.1:{API_PORT}{self.path}"
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(
            target,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = resp.read()
                self.send_response(resp.status)
                self.send_header("Content-Type", resp.headers.get("Content-Type", "application/json"))
                self.end_headers()
                self.wfile.write(payload)
        except urllib.error.HTTPError as exc:
            payload = exc.read()
            self.send_response(exc.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            error = json.dumps({"detail": f"Proxy error: {exc}"}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error)

    # ── Route POST ───────────────────────────────────────────────────────
    def do_POST(self):
        if self._is_api():
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            self._proxy("POST", body)
        else:
            self.send_error(405, "Method Not Allowed")


    # ── Route PUT ────────────────────────────────────────────────────────
    def do_PUT(self):
        if self._is_api():
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            self._proxy("PUT", body)
        else:
            self.send_error(405, "Method Not Allowed")

    # ── Route DELETE ─────────────────────────────────────────────────────
    def do_DELETE(self):
        if self._is_api():
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            self._proxy("DELETE", body)
        else:
            self.send_error(405, "Method Not Allowed")

    # ── Route GET: proxy API paths, serve files for everything else ──────
    def do_GET(self):
        if self._is_api():
            self._proxy("GET")
        else:
            super().do_GET()


if __name__ == "__main__":
    os.chdir(FRONTEND_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    # v3: bind localhost by default; set LUMORA_BIND=0.0.0.0 to expose
    bind_host = os.environ.get("LUMORA_BIND", "127.0.0.1")
    with socketserver.TCPServer((bind_host, PORT), Handler) as httpd:
        print(f"Lumora Dev v3  ·  frontend + proxy  →  http://{bind_host}:{PORT}")
        httpd.serve_forever()
