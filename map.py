#!/usr/bin/env python3
"""Run the polygon explorer and its local farmland map layer."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
from urllib.parse import parse_qs, urlparse
import webbrowser


APP_DIRECTORY = Path(__file__).resolve().parent / "terra-polygon" / "dist"


class AppHandler(SimpleHTTPRequestHandler):
    farmland = None

    def send_content(self, content, content_type, status=200):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass  # A map pan can cancel in-flight requests.

    def send_json(self, value, status=200):
        self.send_content(json.dumps(value, allow_nan=False).encode(), "application/json", status)

    def do_GET(self):
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/farmland/"):
            return super().do_GET()
        if self.farmland is None:
            return self.send_json({"ready": False, "error": "Field data is not prepared. Run prepare_farmland.py first."}, 503)
        try:
            if parsed.path == "/api/farmland/meta":
                return self.send_json(self.farmland.metadata)
            if parsed.path == "/api/farmland/hover":
                query = parse_qs(parsed.query)
                feature = self.farmland.hover(float(query["lng"][0]), float(query["lat"][0]))
                return self.send_json({"feature": feature})
            tile = re.fullmatch(r"/api/farmland/tiles/(\d+)/(\d+)/(\d+)\.png", parsed.path)
            if tile:
                content = self.farmland.tile(*map(int, tile.groups()))
                return self.send_content(content, "image/png")
            return self.send_json({"error": "Unknown farmland endpoint."}, 404)
        except (KeyError, ValueError, OverflowError):
            return self.send_json({"error": "Invalid map coordinates."}, 400)
        except Exception:
            self.log_error("Farmland request failed")
            return self.send_json({"error": "Could not load field data. Check the local server."}, 500)

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main():
    # Preserve the original `python3 map.py` launch command after local setup.
    try:
        from farmland import FarmlandStore
    except ModuleNotFoundError:
        environment_python = Path(__file__).resolve().parent / ".venv" / "bin" / "python"
        if environment_python.is_file() and sys.prefix == sys.base_prefix:
            os.execv(str(environment_python), [str(environment_python), str(Path(__file__).resolve()), *sys.argv[1:]])
        FarmlandStore = None
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000, help="Local port (default: 8000)")
    parser.add_argument("--open", action="store_true", help="Open the app in your browser")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535.")
    if not (APP_DIRECTORY / "index.html").is_file():
        parser.error(f"App files are missing from {APP_DIRECTORY}")

    if FarmlandStore is not None:
        try:
            AppHandler.farmland = FarmlandStore()
            print(f"Farmland layer: {AppHandler.farmland.metadata['count']:,} fields", flush=True)
        except (OSError, sqlite3.Error):
            print("Farmland data is not prepared; polygon drawing is still available.", flush=True)

    handler = partial(AppHandler, directory=str(APP_DIRECTORY))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    except OSError as error:
        print(f"Could not start the app: {error}", file=sys.stderr)
        print("Try a different port: python3 map.py --port 8001", file=sys.stderr)
        return 1

    with server:
        url = f"http://127.0.0.1:{server.server_port}"
        print(f"Terra is running locally at {url}", flush=True)
        print("Press Ctrl+C to stop.", flush=True)
        if args.open:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nTerra stopped.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
