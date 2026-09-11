#!/usr/bin/env python3
"""
Security tests for ui/server.py:
  - Origin/Referer check on every POST (blocks a cross-origin page's
    fetch()/form POST from driving the local UI — same idea as CSRF
    protection, since the server has no auth of its own beyond "only
    127.0.0.1/localhost may talk to it").
  - write_env() rejects values containing \\n / \\r (blocks a POST body
    from injecting extra lines — e.g. a bogus key=value pair — into .env).

Spins the real Handler on an ephemeral 127.0.0.1 port (not the hardcoded
8765, so this can run alongside a live `Screener.command` instance) and
drives it with plain http.client, overriding the Host header to match
ALLOWED_HOSTS (patched to the ephemeral port for the duration of each test).
.env is isolated to a tempdir so these tests never touch a real .env.

Usage:
    python3 -m unittest tests/test_server_security.py -v
    python3 -m pytest tests/test_server_security.py -v   # if pytest is installed
"""
import http.client
import json
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ui"))

import server as server_mod  # noqa: E402


class ServerTestBase(unittest.TestCase):
    def setUp(self):
        # Isolate .env so a test run never reads/writes the real repo .env.
        self._tmp_env_dir = tempfile.TemporaryDirectory()
        self._orig_env_path = server_mod.ENV_PATH
        server_mod.ENV_PATH = Path(self._tmp_env_dir.name) / ".env"

        # Bind an ephemeral port, then patch ALLOWED_HOSTS to match it so
        # the Host-header check (unrelated to what we're testing here)
        # doesn't reject every request out of the gate.
        self._orig_allowed_hosts = server_mod.ALLOWED_HOSTS
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), server_mod.Handler)
        self.port = self.httpd.server_address[1]
        self.host_header = f"127.0.0.1:{self.port}"
        server_mod.ALLOWED_HOSTS = {self.host_header}

        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        server_mod.ENV_PATH = self._orig_env_path
        server_mod.ALLOWED_HOSTS = self._orig_allowed_hosts
        self._tmp_env_dir.cleanup()

    def _post(self, path, body_obj, origin="null", extra_headers=None):
        """origin=None omits the Origin header entirely; any string value
        (including "null") sends that literal Origin header."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        payload = json.dumps(body_obj).encode()
        headers = {
            "Host": self.host_header,
            "Content-Type": "application/json",
            "Content-Length": str(len(payload)),
        }
        if origin is not None:
            headers["Origin"] = origin
        if extra_headers:
            headers.update(extra_headers)
        try:
            conn.request("POST", path, body=payload, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            return resp.status, data
        finally:
            conn.close()


class TestOriginCheck(ServerTestBase):
    def test_no_origin_header_allowed(self):
        status, _ = self._post("/api/keys/save", {}, origin=None)
        self.assertEqual(status, 200)

    def test_null_origin_allowed(self):
        status, _ = self._post("/api/keys/save", {}, origin="null")
        self.assertEqual(status, 200)

    def test_matching_localhost_8765_origin_allowed(self):
        status, _ = self._post("/api/keys/save", {}, origin="http://localhost:8765")
        self.assertEqual(status, 200)

    def test_matching_127_0_0_1_8765_origin_allowed(self):
        status, _ = self._post("/api/keys/save", {}, origin="http://127.0.0.1:8765")
        self.assertEqual(status, 200)

    def test_cross_origin_rejected(self):
        status, body = self._post("/api/keys/save", {}, origin="http://evil.example")
        self.assertEqual(status, 403)
        self.assertIn(b"forbidden origin", body)

    def test_off_origin_referer_rejected_when_origin_absent(self):
        status, _ = self._post("/api/keys/save", {}, origin=None,
                                extra_headers={"Referer": "http://evil.example/attack.html"})
        self.assertEqual(status, 403)

    def test_matching_referer_allowed_when_origin_absent(self):
        status, _ = self._post("/api/keys/save", {}, origin=None,
                                extra_headers={"Referer": "http://127.0.0.1:8765/"})
        self.assertEqual(status, 200)


class TestEnvNewlineGuard(ServerTestBase):
    def test_newline_in_value_rejected_and_nothing_written(self):
        status, _ = self._post(
            "/api/keys/save",
            {"anthropic": "sk-real-key\nOPENAI_API_KEY=sk-injected"},
        )
        self.assertEqual(status, 400)
        self.assertFalse(server_mod.ENV_PATH.exists())

    def test_carriage_return_in_value_rejected(self):
        status, _ = self._post("/api/keys/save", {"openai": "abc\rdef"})
        self.assertEqual(status, 400)

    def test_clean_value_accepted_and_persisted_stripped(self):
        status, _ = self._post("/api/keys/save", {"anthropic": "  sk-clean-value  "})
        self.assertEqual(status, 200)
        self.assertTrue(server_mod.ENV_PATH.exists())
        content = server_mod.ENV_PATH.read_text()
        self.assertIn("ANTHROPIC_API_KEY=sk-clean-value\n", content)
        # exactly the two known keys — no injected third line
        lines = [l for l in content.splitlines() if l.strip()]
        self.assertEqual(len(lines), 2)


if __name__ == "__main__":
    unittest.main()
