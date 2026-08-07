"""
Lumora Dev – static file server + reverse proxy.
Serves frontend/ and forwards API paths to the FastAPI backend.

Cloud-native:
  PORT / LUMORA_BIND / LUMORA_API_PORT from environment.
Local defaults:
  Frontend :5000, API proxy target :8000.
"""
import http.server
import socketserver
import os
import urllib.request
import urllib.error
import json

FRONTEND_PORT = int(os.getenv("LUMORA_FRONTEND_PORT", os.getenv("FRONTEND_PORT", "5000")))
API_PORT = int(os.getenv("LUMORA_API_PORT", os.getenv("API_PORT", os.getenv("PORT", "8000"))))
BIND_HOST = os.getenv("LUMORA_BIND", "0.0.0.0")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

PROXY_PATHS = (
    "/chat", "/files", "/file", "/folder",
    "/terminal", "/settings", "/git", "/github",
    "/activity", "/workspaces", "/codebase", "/db",
    "/auth", "/memory", "/planner", "/edits", "/browser",
    "/vision", "/knowledge", "/multiagent", "/system", "/deployment",
    "/health", "/docs", "/openapi.json", "/redoc",
)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Lumora-Token")
        self.end_headers()

    def _is_api(self):
        bare = self.path.split("?")[0]
        return any(
            bare == p or bare.startswith(p + "?") or bare.startswith(p + "/")
            for p in PROXY_PATHS
        )

    def _proxy(self, method: str, body: bytes | None = None):
        target = f"http://127.0.0.1:{API_PORT}{self.path}"
        headers = {"Content-Type": self.headers.get("Content-Type", "application/json")}
        token = self.headers.get("X-Lumora-Token")
        if token:
            headers["X-Lumora-Token"] = token
        req = urllib.request.Request(target, data=body, headers=headers, method=method)
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

    def do_POST(self):
        if self._is_api():
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            self._proxy("POST", body)
        else:
            self.send_error(405, "Method Not Allowed")

    def do_PUT(self):
        if self._is_api():
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            self._proxy("PUT", body)
        else:
            self.send_error(405, "Method Not Allowed")

    def do_DELETE(self):
        if self._is_api():
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            self._proxy("DELETE", body)
        else:
            self.send_error(405, "Method Not Allowed")

    def do_GET(self):
        if self._is_api():
            self._proxy("GET")
        else:
            super().do_GET()


if __name__ == "__main__":
    os.chdir(FRONTEND_DIR)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer((BIND_HOST, FRONTEND_PORT), Handler) as httpd:
        print(
            f"Lumora Dev  ·  frontend + proxy  →  http://{BIND_HOST}:{FRONTEND_PORT}"
            f"  (API proxy → 127.0.0.1:{API_PORT})"
        )
        httpd.serve_forever()
