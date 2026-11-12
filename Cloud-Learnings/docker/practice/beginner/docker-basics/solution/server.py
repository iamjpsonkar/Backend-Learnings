"""
Solution for Docker Basics exercise.
"""

import json
import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.getenv("APP_PORT", "8080"))
request_count = {"total": 0}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass  # Suppress default access logs

    def do_GET(self):
        request_count["total"] += 1

        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
        elif self.path == "/":
            self._send_json(200, {
                "message": "Hello from Docker!",
                "hostname": socket.gethostname()
            })
        elif self.path == "/metrics":
            body = f"# HELP http_requests_total Total requests\n# TYPE http_requests_total counter\nhttp_requests_total {request_count['total']}\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body.encode())
        else:
            self._send_json(404, {"error": "Not found", "path": self.path})

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Server listening on port {PORT}")
    server.serve_forever()
