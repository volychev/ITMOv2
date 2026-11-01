import io
import json
import os
import sys
import types
import unittest
from unittest import mock
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rubrica.narrative import NarrativeUnavailable, request_narrative  # noqa: E402


@contextmanager
def env(key, value):
    old = os.environ.get(key)
    try:
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


class DummyResp:
    def __init__(self, payload, code=200):
        self._payload = payload
        self.code = code

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class NarrativeTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"spec": "demo", "score": 1, "max_score": 1, "findings": []}

    def test_requires_api_key(self):
        with env("VSELLM_API_KEY", None):
            with self.assertRaises(NarrativeUnavailable) as ctx:
                request_narrative(self.payload)
            self.assertIn("VSELLM_API_KEY", str(ctx.exception))

    def test_successful_response(self):
        def fake_urlopen(req, timeout=None):
            data = {
                "id": "x",
                "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": "Review text"}}
                ],
            }
            return DummyResp(json.dumps(data).encode("utf-8"))

        import urllib.request as _u

        with env("VSELLM_API_KEY", "sk-test-key"), mock.patch.object(_u, "urlopen", fake_urlopen):
            text = request_narrative(self.payload, model="gpt-any", timeout=0.1, endpoint="https://x/y")
            self.assertEqual(text, "Review text")

    def test_http_error(self):
        import urllib.error as ue
        import urllib.request as _u

        def fake_urlopen(req, timeout=None):
            raise ue.HTTPError(req.full_url, 500, "Internal", hdrs=None, fp=None)

        with env("VSELLM_API_KEY", "k"), mock.patch.object(_u, "urlopen", fake_urlopen):
            with self.assertRaises(NarrativeUnavailable) as ctx:
                request_narrative(self.payload)
            self.assertIn("HTTP", str(ctx.exception))

    def test_timeout_error(self):
        import urllib.error as ue
        import urllib.request as _u
        import socket

        def fake_urlopen(req, timeout=None):
            raise ue.URLError(socket.timeout("timed out"))

        with env("VSELLM_API_KEY", "k"), mock.patch.object(_u, "urlopen", fake_urlopen):
            with self.assertRaises(NarrativeUnavailable) as ctx:
                request_narrative(self.payload, timeout=0.01)
            self.assertIn("таймаут", str(ctx.exception))

    def test_non_json_response(self):
        import urllib.request as _u

        def fake_urlopen(req, timeout=None):
            return DummyResp(b"<html>not json</html>")

        with env("VSELLM_API_KEY", "k"), mock.patch.object(_u, "urlopen", fake_urlopen):
            with self.assertRaises(NarrativeUnavailable) as ctx:
                request_narrative(self.payload)
            self.assertIn("не-JSON", str(ctx.exception))

    def test_missing_choices(self):
        import urllib.request as _u

        def fake_urlopen(req, timeout=None):
            data = {"id": "x", "choices": []}
            return DummyResp(json.dumps(data).encode("utf-8"))

        with env("VSELLM_API_KEY", "k"), mock.patch.object(_u, "urlopen", fake_urlopen):
            with self.assertRaises(NarrativeUnavailable) as ctx:
                request_narrative(self.payload)
            self.assertIn("choices", str(ctx.exception))

    def test_missing_message_content(self):
        import urllib.request as _u

        def fake_urlopen(req, timeout=None):
            data = {"choices": [{"message": {"role": "assistant", "content": ""}}]}
            return DummyResp(json.dumps(data).encode("utf-8"))

        with env("VSELLM_API_KEY", "k"), mock.patch.object(_u, "urlopen", fake_urlopen):
            with self.assertRaises(NarrativeUnavailable) as ctx:
                request_narrative(self.payload)
            self.assertIn("не содержит", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
