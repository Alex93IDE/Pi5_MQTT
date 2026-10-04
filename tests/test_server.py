import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from server import SpaHandler


class SpaServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = os.path.join(cls.tmp.name, "public")
        os.makedirs(os.path.join(root, "assets"))
        with open(os.path.join(root, "index.html"), "w") as f:
            f.write("<h1>app</h1>")
        with open(os.path.join(root, "assets", "app.js"), "w") as f:
            f.write("console.log(1)")
        # Something next to the web root that must never be served.
        with open(os.path.join(cls.tmp.name, "secret.env"), "w") as f:
            f.write("MQTT_PASS=hunter2")

        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(SpaHandler, directory=root))
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.tmp.cleanup()

    def get(self, path):
        try:
            with urllib.request.urlopen(self.base + path) as r:
                return r.status, r.headers, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, ""

    def test_index_and_spa_routes(self):
        for path in ("/", "/services", "/some/deep/route"):
            with self.subTest(path=path):
                status, headers, body = self.get(path)
                self.assertEqual(status, 200)
                self.assertEqual(body, "<h1>app</h1>")
                self.assertEqual(headers["Cache-Control"], "no-cache")

    def test_assets_are_cached(self):
        status, headers, body = self.get("/assets/app.js")
        self.assertEqual(status, 200)
        self.assertIn("immutable", headers["Cache-Control"])

    def test_missing_file_is_404_not_html(self):
        self.assertEqual(self.get("/assets/missing.js")[0], 404)

    def test_no_directory_listing(self):
        self.assertEqual(self.get("/assets/")[0], 404)

    def test_cannot_escape_web_root(self):
        for path in ("/../secret.env", "/%2e%2e/secret.env", "/assets/../../secret.env"):
            with self.subTest(path=path):
                status, _, body = self.get(path)
                self.assertNotIn("hunter2", body)
                self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
