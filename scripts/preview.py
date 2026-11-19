#!/usr/bin/env python3
"""
Local preview of the bioatlas.io site.

Serves site/ at http://localhost:8000. With --tiles, the original Bio-Atlas
tiles written by bioatlas_extract.py are served as well, and the pages are
told to use them, so every slide in slides-index.js opens in the local viewer
before anything is uploaded:

    python scripts/preview.py
    python scripts/preview.py --tiles E:\\LegacyBioAtlas_Histology\\bioatlas_fullres\\tiles

Nothing in the repository is changed; the tile location is added to config.js
only in the copy that is sent to the browser. Requires Python 3.8+ only.
"""
import argparse
import http.server
import os
import posixpath
import urllib.parse
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
MOUNT = "/_tiles"


class Handler(http.server.SimpleHTTPRequestHandler):
    tiles = None

    def translate_path(self, path):
        clean = urllib.parse.unquote(path.split("?", 1)[0].split("#", 1)[0])
        if self.tiles and clean.startswith(MOUNT + "/"):
            rel = posixpath.normpath(clean[len(MOUNT) + 1:])
            if rel.startswith(".."):
                return os.path.join(self.tiles, "_not_found_")
            return os.path.join(self.tiles, *rel.split("/"))
        return super().translate_path(path)

    def do_GET(self):
        if self.tiles and self.path.split("?", 1)[0] == "/assets/js/config.js":
            body = (SITE / "assets/js/config.js").read_bytes()
            body += ('\nBIOATLAS_CONFIG.ORIGINAL_TILE_BASE = "%s";\n' % MOUNT).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/javascript")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        if not (args and str(args[0]).startswith("GET " + MOUNT)):   # keep tile requests quiet
            super().log_message(fmt, *args)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tiles", help="tiles folder written by bioatlas_extract.py")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()
    if args.tiles:
        if not os.path.isdir(args.tiles):
            raise SystemExit("Not found: " + args.tiles)
        Handler.tiles = os.path.abspath(args.tiles)

    def handler(*a, **kw):
        return Handler(*a, directory=str(SITE), **kw)

    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as httpd:
        print("Serving %s at http://localhost:%d/" % (SITE, args.port))
        if args.tiles:
            print("Original tiles from %s" % Handler.tiles)
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
