#!/usr/bin/env python3
"""
tests/test_modio_client.py
--------------------------
Unit tests for bg3_core.modio_client: ModioClient, pagination, auth, and error redaction.
"""

import io
import json
import unittest
import urllib.error
from unittest.mock import Mock

from bg3_core.modio.modio_client import ModioClient, ModioError


class ModioClientTests(unittest.TestCase):
    def test_request_headers_and_bearer_auth(self):
        response = Mock()
        response.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=response)

        client = ModioClient("secret-pat", opener=opener)
        payload = client.request("GET", "/games/6715/mods")

        self.assertEqual(payload, {"status": "ok"})
        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-pat")
        self.assertEqual(request.get_header("Accept"), "application/json")
        self.assertIn("g-6715.modapi.io", request.full_url)

    def test_request_handles_full_url(self):
        response = Mock()
        response.read.return_value = b"{}"
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=response)

        client = ModioClient("pat", opener=opener)
        client.request("GET", "https://api.mod.io/v1/me/subscribed")

        request = opener.call_args.args[0]
        self.assertTrue(request.full_url.startswith("https://api.mod.io/v1/me/subscribed"))

    def test_request_redacts_token_on_http_error(self):
        token = "super-secret-token"
        error = urllib.error.HTTPError(
            "https://example.invalid",
            401,
            "Unauthorized",
            {},
            io.BytesIO(f"failed authentication with token {token}".encode("utf-8")),
        )
        opener = Mock(side_effect=error)
        client = ModioClient(token, opener=opener)

        with self.assertRaises(ModioError) as cm:
            client.request("GET", "/me/subscribed")

        self.assertNotIn(token, str(cm.exception))
        self.assertIn("[REDACTED]", str(cm.exception))

    def test_get_paged_collects_all_pages(self):
        calls = []

        def fake_opener(req, timeout=30):
            calls.append(req.full_url)
            if "_offset=0" in req.full_url:
                body = json.dumps(
                    {
                        "data": [{"id": 1, "name": "Mod 1"}, {"id": 2, "name": "Mod 2"}],
                        "result_total": 3,
                    }
                ).encode("utf-8")
            else:
                body = json.dumps(
                    {
                        "data": [{"id": 3, "name": "Mod 3"}],
                        "result_total": 3,
                    }
                ).encode("utf-8")

            resp = Mock()
            resp.read.return_value = body
            resp.__enter__ = Mock(return_value=resp)
            resp.__exit__ = Mock(return_value=False)
            return resp

        client = ModioClient("tok", opener=fake_opener)
        items = client.get_paged("/me/subscribed", page_size=2)

        self.assertEqual(len(items), 3)
        self.assertEqual([i["id"] for i in items], [1, 2, 3])
        self.assertEqual(len(calls), 2)

    def test_get_paged_rejects_invalid_list_shape(self):
        response = Mock()
        response.read.return_value = json.dumps({"data": "not a list"}).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=response)

        client = ModioClient("tok", opener=opener)
        with self.assertRaises(ModioError):
            client.get_paged("/me/subscribed")

    def test_get_caches_response_and_avoids_second_network_call(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            response = Mock()
            response.read.return_value = json.dumps({"result": "cached_val"}).encode("utf-8")
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            opener = Mock(return_value=response)

            client = ModioClient(
                "tok", opener=opener, cache_path=cache_file, cache_ttl_seconds=60, enable_cache=True
            )
            res1 = client.request("GET", "/games/6715")
            self.assertEqual(res1, {"result": "cached_val"})
            self.assertEqual(opener.call_count, 1)

            # Second call should read from cache without invoking opener
            res2 = client.request("GET", "/games/6715")
            self.assertEqual(res2, {"result": "cached_val"})
            self.assertEqual(opener.call_count, 1)

    def test_post_clears_cache(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            response = Mock()
            response.read.return_value = json.dumps({"status": "ok"}).encode("utf-8")
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            opener = Mock(return_value=response)

            client = ModioClient(
                "tok", opener=opener, cache_path=cache_file, cache_ttl_seconds=60, enable_cache=True
            )
            client.request("GET", "/games/6715")
            self.assertTrue(cache_file.exists())

            client.request("POST", "/games/6715/mods")
            self.assertFalse(cache_file.exists())

    def test_bypass_cache_flag(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_file = Path(tmpdir) / "test_cache.json"
            response = Mock()
            response.read.return_value = json.dumps({"status": "live"}).encode("utf-8")
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            opener = Mock(return_value=response)

            client = ModioClient(
                "tok", opener=opener, cache_path=cache_file, cache_ttl_seconds=60, enable_cache=True
            )
            client.request("GET", "/games/6715")
            self.assertEqual(opener.call_count, 1)

            client.request("GET", "/games/6715", bypass_cache=True)
            self.assertEqual(opener.call_count, 2)

    def test_multipart_binary_file_upload_encoding(self):
        response = Mock()
        response.read.return_value = json.dumps({"id": 999, "version": "1.0.0"}).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=response)

        client = ModioClient("test-token", opener=opener)
        dummy_pak = b"PK_DUMMY_BINARY_DATA_12345"
        fields = [
            ("filedata", ("my_mod.pak", dummy_pak, "application/octet-stream")),
            ("version", "1.0.0"),
            ("active", "true"),
        ]

        payload = client.request("POST", "/games/6715/mods/42/files", fields=fields, multipart=True)
        self.assertEqual(payload["id"], 999)

        request = opener.call_args.args[0]
        content_type = request.get_header("Content-type")
        self.assertIn("multipart/form-data; boundary=", content_type)

        req_data = request.data
        self.assertIsInstance(req_data, bytes)
        self.assertIn(
            b'Content-Disposition: form-data; name="filedata"; filename="my_mod.pak"', req_data
        )
        self.assertIn(b"Content-Type: application/octet-stream", req_data)
        self.assertIn(dummy_pak, req_data)
        self.assertIn(b'Content-Disposition: form-data; name="version"', req_data)
        self.assertIn(b"1.0.0", req_data)

    def test_upload_mod_file_api(self):
        import tempfile
        from pathlib import Path

        from bg3_core.modio.modio_client import upload_mod_file

        with tempfile.TemporaryDirectory() as tmpdir:
            pak_path = Path(tmpdir) / "TestMod.pak"
            pak_path.write_bytes(b"LSPK_MOCK_BYTES")

            response = Mock()
            response.read.return_value = json.dumps({"status": "uploaded", "id": 101}).encode(
                "utf-8"
            )
            response.__enter__ = Mock(return_value=response)
            response.__exit__ = Mock(return_value=False)
            opener = Mock(return_value=response)

            client = ModioClient("test-token", opener=opener)
            res = upload_mod_file(
                mod_id=42,
                file_path=pak_path,
                version="1.0.0",
                changelog="Initial release",
                active=True,
                client=client,
            )
            self.assertEqual(res["status"], "uploaded")
            self.assertEqual(res["id"], 101)

            req = opener.call_args.args[0]
            self.assertEqual(req.get_method(), "POST")
            self.assertIn("/games/6715/mods/42/files", req.full_url)
            self.assertIn(b'filename="TestMod.pak"', req.data)
            self.assertIn(b"LSPK_MOCK_BYTES", req.data)
            self.assertIn(b"Initial release", req.data)

    def test_upload_mod_file_validations(self):
        from bg3_core.modio.modio_client import upload_mod_file

        # Missing file raises FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            upload_mod_file(mod_id=42, file_path="/nonexistent/path/Mod.pak")

        # Missing token raises ModioError
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir) / "dummy.pak"
            p.write_bytes(b"data")
            with self.assertRaises(ModioError):
                upload_mod_file(mod_id=42, file_path=p, client=ModioClient(token=""))


if __name__ == "__main__":
    unittest.main()
