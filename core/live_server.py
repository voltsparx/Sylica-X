"""Legacy standalone live server (optional utility)."""

from __future__ import annotations

import json
from http.server import HTTPServer, SimpleHTTPRequestHandler

from core.storage import results_json_path, sanitize_target


PORT = 8000
TARGET = ""


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - stdlib hook
        target = sanitize_target(TARGET)
        if self.path != "/":
            self.send_error(404)
            return

        file_path = results_json_path(target)
        if not file_path.exists():
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h2>No results found for target: {target}</h2>".encode())
            return

        with file_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)

        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())


if __name__ == "__main__":
    if not TARGET:
        TARGET = input("Enter target to view live results: ").strip()

    server_address = ("", PORT)
    print(f"Serving {sanitize_target(TARGET)} at http://localhost:{PORT}/")
    with HTTPServer(server_address, Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")
