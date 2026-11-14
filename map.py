#!/usr/bin/env python3
"""Run the polygon explorer locally using only Python's standard library."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import webbrowser


APP_DIRECTORY = Path(__file__).resolve().parent / "terra-polygon" / "dist"


class AppHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000, help="Local port (default: 8000)")
    parser.add_argument("--open", action="store_true", help="Open the app in your browser")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Port must be between 0 and 65535.")
    if not (APP_DIRECTORY / "index.html").is_file():
        parser.error(f"App files are missing from {APP_DIRECTORY}")

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
