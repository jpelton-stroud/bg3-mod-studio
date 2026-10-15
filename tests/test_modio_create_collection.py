import io
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock

from scripts.modio_create_collection import (
    BG3_GAME_ID,
    ModEntry,
    ModioClient,
    ModioError,
    apply_changes,
    build_changes,
    parse_catalog,
    run_workflow,
)


class StubClient:
    def __init__(self):
        self.calls = []

    def request(self, method, path, params=None, fields=None):
        self.calls.append((method, path, params, fields))
        if path.endswith("/mods/101"):
            return {"id": 101, "game_id": BG3_GAME_ID}
        if path == "/me/collections":
            return {"data": [], "result_total": 0}
        raise AssertionError(f"Unexpected API request: {method} {path}")


class CreateClient:
    def __init__(self):
        self.calls = []

    def request(self, method, path, params=None, fields=None):
        self.calls.append((method, path, params, fields))
        if path == f"/games/{BG3_GAME_ID}/mods/101":
            return {"id": 101, "game_id": BG3_GAME_ID}
        if path == "/me/collections":
            return {"data": [], "result_total": 0}
        if method == "POST" and path == f"/games/{BG3_GAME_ID}/collections":
            return {"id": 505}
        if path == f"/games/{BG3_GAME_ID}/collections/505":
            return {"id": 505, "game_id": BG3_GAME_ID}
        if method == "POST" and path == f"/games/{BG3_GAME_ID}/collections/505/mods":
            return {}
        raise AssertionError(f"Unexpected API request: {method} {path}")


class ModioCollectionTests(unittest.TestCase):
    def make_library(self, content):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        library_path = Path(temporary_directory.name) / "library.md"
        library_path.write_text(content, encoding="utf-8")
        return library_path

    def test_parse_catalog_includes_only_valid_documented_ids(self):
        library = self.make_library(
            "# Mod Library\n\n"
            "| Mod Name | Description | Features | Spec Link |\n"
            "| :--- | :--- | :--- | :--- |\n"
            "| **[Alpha](alpha/README.md)** | A | 1 | [Spec](alpha/README.md) |\n"
            "| **[Beta](beta/README.md)** | B | 0 | [Spec](beta/README.md) |\n"
            "| **[Gamma](gamma/README.md)** | C | 0 | [Spec](gamma/README.md) |\n\n"
            "## Mod.io IDs\n\n"
            "| Mod Name | Slug | Mod.io ID |\n"
            "| :--- | :--- | ---: |\n"
            "| Alpha | `alpha` | 101 |\n"
            "| Gamma | `gamma` | not-a-number |\n"
        )

        entries, warnings, missing_count = parse_catalog(library)

        self.assertEqual(entries, [ModEntry("Alpha", "alpha", 101)])
        self.assertEqual(missing_count, 2)
        self.assertTrue(any("gamma" in warning and "valid" in warning for warning in warnings))
        self.assertTrue(any("2 documented library entries" in warning for warning in warnings))

    def test_parse_catalog_rejects_duplicate_numeric_ids(self):
        library = self.make_library(
            "| **[Alpha](alpha/README.md)** | A | 1 | [Spec](alpha/README.md) |\n"
            "| **[Beta](beta/README.md)** | B | 1 | [Spec](beta/README.md) |\n"
            "## Mod.io IDs\n"
            "| Mod Name | Slug | Mod.io ID |\n"
            "| Alpha | `alpha` | 101 |\n"
            "| Beta | `beta` | 101 |\n"
        )

        with self.assertRaisesRegex(ModioError, "assigns ID 101 to both"):
            parse_catalog(library)

    def test_build_changes_adds_missing_and_only_replaces_when_selected(self):
        selected = [ModEntry("Alpha", "alpha", 101)]
        current = {101: "Alpha", 202: "Other"}

        add_only = build_changes(selected, current, "add")
        replace = build_changes(selected, current, "replace")

        self.assertEqual(add_only, ([], []))
        self.assertEqual(replace, ([], [(202, "Other")]))

    def test_dry_run_does_not_send_api_writes(self):
        library = self.make_library(
            "| **[Alpha](alpha/README.md)** | A | 1 | [Spec](alpha/README.md) |\n"
            "## Mod.io IDs\n"
            "| Mod Name | Slug | Mod.io ID |\n"
            "| Alpha | `alpha` | 101 |\n"
        )
        client = StubClient()
        answers = iter(["1", "c", "My Collection", "A description"])
        output = io.StringIO()

        result = run_workflow(
            client,
            library_path=library,
            dry_run=True,
            input_fn=lambda _prompt: next(answers),
            output=output,
        )

        self.assertEqual(result["status"], "dry_run")
        self.assertFalse(any(call[0] in ("POST", "DELETE") for call in client.calls))
        self.assertIn("Dry run: no changes were sent", output.getvalue())

    def test_declined_confirmation_does_not_send_api_writes(self):
        library = self.make_library(
            "| **[Alpha](alpha/README.md)** | A | 1 | [Spec](alpha/README.md) |\n"
            "## Mod.io IDs\n"
            "| Mod Name | Slug | Mod.io ID |\n"
            "| Alpha | `alpha` | 101 |\n"
        )
        client = StubClient()
        answers = iter(["1", "c", "My Collection", "A description", "no"])
        output = io.StringIO()

        result = run_workflow(
            client,
            library_path=library,
            input_fn=lambda _prompt: next(answers),
            output=output,
        )

        self.assertEqual(result["status"], "cancelled")
        self.assertFalse(any(call[0] in ("POST", "DELETE") for call in client.calls))

    def test_create_requires_confirmation_and_adds_selected_mods(self):
        library = self.make_library(
            "| **[Alpha](alpha/README.md)** | A | 1 | [Spec](alpha/README.md) |\n"
            "## Mod.io IDs\n"
            "| Mod Name | Slug | Mod.io ID |\n"
            "| Alpha | `alpha` | 101 |\n"
        )
        client = CreateClient()
        answers = iter(["1", "c", "My Collection", "A description", "yes"])
        output = io.StringIO()

        result = run_workflow(
            client,
            library_path=library,
            input_fn=lambda _prompt: next(answers),
            output=output,
        )

        create_call = next(call for call in client.calls if call[1] == f"/games/{BG3_GAME_ID}/collections")
        add_call = next(call for call in client.calls if call[1].endswith("/collections/505/mods"))
        self.assertEqual(result["status"], "success")
        self.assertIn(("visible", "1"), create_call[3])
        self.assertIn(("summary", "A description"), create_call[3])
        self.assertEqual(add_call[3], [("mods[]", "101")])
        self.assertIn("Description: A description", output.getvalue())

    def test_failed_add_preserves_collection_mods_in_replace_mode(self):
        client = Mock()
        client.request.side_effect = ModioError("write rejected")

        result = apply_changes(
            client,
            collection_id=55,
            to_add=[ModEntry("Alpha", "alpha", 101)],
            to_remove=[(202, "Other")],
        )

        self.assertEqual(result["status"], "partial_failure")
        self.assertEqual(result["operations"]["add_mods"]["status"], "failed")
        self.assertEqual(result["operations"]["remove_mods"]["status"], "skipped")
        self.assertEqual(client.request.call_count, 1)

    def test_client_redacts_token_from_http_error(self):
        token = "secret-token"
        error = urllib.error.HTTPError(
            "https://example.invalid",
            403,
            "Forbidden",
            {},
            io.BytesIO(f"invalid token {token}".encode()),
        )
        opener = Mock(side_effect=error)
        client = ModioClient(token, opener=opener)

        with self.assertRaises(ModioError) as raised:
            client.request("GET", "/me/collections")

        self.assertNotIn(token, str(raised.exception))
        self.assertIn("[REDACTED]", str(raised.exception))
        self.assertEqual(opener.call_args.kwargs["timeout"], 30)

    def test_client_sends_pat_as_bearer_authorization(self):
        response = Mock()
        response.read.return_value = b"{}"
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        opener = Mock(return_value=response)
        client = ModioClient("test-token", opener=opener)

        client.request("GET", "/me/collections")

        request = opener.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")


if __name__ == "__main__":
    unittest.main()
