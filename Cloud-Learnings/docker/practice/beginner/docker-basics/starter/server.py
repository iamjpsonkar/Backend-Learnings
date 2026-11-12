"""
Starter code for the Docker Basics exercise.
Complete the TODOs to make this a working HTTP server.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = int(os.getenv("APP_PORT", "8080"))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # TODO (optional): replace with structured logging
        pass

    def do_GET(self):
        # TODO: Route based on self.path
        # - "/" → 200, {"message": "Hello from Docker!"}
        # - "/health" → 200, {"status": "ok"}
        # - anything else → 404, {"error": "Not found"}

        if self.path == "/health":
            # TODO: send 200 with JSON body
            pass
        elif self.path == "/":
            # TODO: send 200 with JSON body
            pass
        else:
            # TODO: send 404 with JSON body
            pass

    def _send_json(self, status: int, data: dict) -> None:
        """Helper to send a JSON response."""
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
