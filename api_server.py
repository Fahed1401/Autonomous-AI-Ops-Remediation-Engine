"""Zero-dependency, loopback-only web server for the AIOps portfolio lab.

Launch: python3 api_server.py
Optional LocalStack: AIOPS_MODE=localstack python3 api_server.py
Do not expose this unauthenticated development service to the public Internet.
"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from aiops.core import RemediationError
from aiops.service import OperationsService

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "frontend"
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/styles.css": ("styles.css", "text/css; charset=utf-8"),
          "/app.js": ("app.js", "application/javascript; charset=utf-8"),
          "/favicon.svg": ("favicon.svg", "image/svg+xml")}


def make_handler(service: OperationsService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "AIOpsLab/1.0"
        sys_version = ""

        def _headers(self, status, mime, length):
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(length))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()

        def _send(self, code, data):
            encoded = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
            self._headers(code, "application/json; charset=utf-8", len(encoded))
            self.wfile.write(encoded)

        def _allowed_host(self):
            host = self.headers.get("Host", "")
            return host in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def _valid_origin(self):
            origin = self.headers.get("Origin")
            if not origin:
                # Non-browser clients on loopback can use the API; server is NOT for untrusted users.
                return True
            parsed = urlsplit(origin)
            return parsed.scheme == "http" and parsed.netloc in {
                f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"} and not parsed.path.strip("/")

        def do_GET(self):
            if not self._allowed_host():
                return self._send(403, {"error": "Host denied"})
            path = urlsplit(self.path).path
            try:
                if path == "/api/overview":
                    return self._send(200, service.overview())
                if path == "/api/health":
                    return self._send(200, service.health())
                if path == "/api/runbooks":
                    return self._send(200, service.runbooks())
                if path in STATIC:
                    file_name, mime = STATIC[path]
                    data = (PUBLIC / file_name).read_bytes()
                    self._headers(200, mime, len(data))
                    return self.wfile.write(data)
                return self._send(404, {"error": "Not found"})
            except Exception:
                return self._send(500, {"error": "Internal server error"})

        def do_POST(self):
            if not self._allowed_host() or not self._valid_origin():
                return self._send(403, {"error": "Cross-origin or invalid Host request rejected"})
            path = urlsplit(self.path).path
            if path not in {"/api/analyze", "/api/approve", "/api/execute", "/api/reset"}:
                return self._send(404, {"error": "Not found"})
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                return self._send(415, {"error": "application/json content type required"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 0 or length > 32_768:
                    return self._send(413, {"error": "Invalid request size"})
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    return self._send(400, {"error": "Expected a JSON object"})
                if path == "/api/analyze":
                    return self._send(200, service.analyze(body.get("incident_id", "")))
                if path == "/api/approve":
                    return self._send(200, service.approve(body.get("plan_id", ""),
                                                         body.get("confirmation", ""),
                                                         body.get("acknowledged", False)))
                if path == "/api/execute":
                    return self._send(200, service.execute(body.get("plan_id", ""),
                                                         body.get("approval_token", "")))
                return self._send(200, service.reset_demo())
            except RemediationError as exc:
                return self._send(400, {"error": str(exc)})
            except (ValueError, TypeError, UnicodeDecodeError):
                return self._send(400, {"error": "Malformed JSON request"})
            except Exception:
                return self._send(500, {"error": "Internal server error"})

        def log_message(self, format, *args):
            # Logs URL/method only; never writes request bodies or approval secrets.
            super().log_message(format, *args)

    return Handler


def main():
    mode = os.getenv("AIOPS_MODE", "demo").lower()
    port = int(os.getenv("AIOPS_PORT", "8501"))
    service = OperationsService(mode=mode)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(service))
    print(f"AIOps Remediation Lab ({mode.upper()}) is running at http://127.0.0.1:{port}")
    print("Local development only: do not proxy this server to the public Internet.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
