import logging
import os
import threading
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from config import HTTP_HOST, HTTP_PORT, WEB_ROOT

log = logging.getLogger("http")


class SpaHandler(SimpleHTTPRequestHandler):
    """Static files, with unknown routes falling back to index.html.

    The dashboard uses history-mode routing, so a reload on /whatever has to
    get the app back. Anything that looks like a file (has an extension)
    still 404s, so a missing asset doesn't come back as HTML.
    """

    def translate_path(self, path):
        full = super().translate_path(path)
        if not os.path.exists(full) and not os.path.splitext(full)[1]:
            return os.path.join(self.directory, "index.html")
        return full

    def list_directory(self, path):
        self.send_error(404)
        return None

    def end_headers(self):
        # Vite hashes everything under assets/, index.html must never be stale.
        if self.path.startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def log_message(self, format, *args):
        pass


def start_server():
    """Serve WEB_ROOT on HTTP_PORT in a background thread. No-op if unset."""
    if not HTTP_PORT:
        return None

    if not os.path.isfile(os.path.join(WEB_ROOT, "index.html")):
        log.warning("%s/index.html not found — deploy the dashboard there", WEB_ROOT)

    handler = partial(SpaHandler, directory=WEB_ROOT)
    httpd = ThreadingHTTPServer((HTTP_HOST, HTTP_PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    log.info("Serving %s on %s:%s", WEB_ROOT, HTTP_HOST, HTTP_PORT)
    return httpd
