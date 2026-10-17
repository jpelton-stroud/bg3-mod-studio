import io
import tempfile
import unittest
from pathlib import Path

from scripts.management.modio_update_metadata import (
    BG3_GAME_ID,
    COMMUNITY_OPTIONS,
    CREDIT_OPTIONS_MASK,
    ModioClient,
    ModioError,
    extract_allowed_tag_map,
    find_remote_mod,
    normalize_name,
    validate_selected_tags,
)


class MockModioClient:
    def __init__(self, routes=None):
        self.routes = routes or {}
        self.calls = []

    def request(self, method, path, params=None, fields=None, multipart=False):
        self.calls.append((method, path, params, fields, multipart))
        key = (method, path)
        if key in self.routes:
            handler = self.routes[key]
            if callable(handler):
                return handler(params, fields)
            return handler
        raise AssertionError(f"Unexpected request: {method} {path} params={params}")


class ModioUpdateMetadataTests(unittest.TestCase):
    def test_find_remote_mod_prioritizes_user_mods_exact_slug(self):
        client = MockModioClient(
            {
                ("GET", "/me/mods"): lambda params, fields: {
                    "data": [
                        {
                            "id": 6454220,
                            "name": "Paladin's Call",
                            "name_id": "paladins-call",
                            "visible": 0,
                        }
                    ]
                }
            }
        )
        mod_dir = Path("/tmp/my_mods/paladins-call")
        mod = find_remote_mod(client, mod_dir, "Paladin's Call")
        self.assertEqual(mod["id"], 6454220)
        self.assertEqual(mod["name_id"], "paladins-call")
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0][1], "/me/mods")

    def test_find_remote_mod_falls_back_to_catalog_if_not_in_user_mods(self):
        client = MockModioClient(
            {
                ("GET", "/me/mods"): {"data": []},
                ("GET", f"/games/{BG3_GAME_ID}/mods"): lambda params, fields: {
                    "data": [
                        {
                            "id": 12345,
                            "name": "Public Mod",
                            "name_id": "public-mod",
                            "visible": 1,
                        }
                    ]
                },
            }
        )
        mod_dir = Path("/tmp/my_mods/public-mod")
        mod = find_remote_mod(client, mod_dir, "Public Mod")
        self.assertEqual(mod["id"], 12345)
        self.assertEqual(mod["name_id"], "public-mod")

    def test_find_remote_mod_raises_when_no_match(self):
        client = MockModioClient(
            {
                ("GET", "/me/mods"): {"data": []},
                ("GET", f"/games/{BG3_GAME_ID}/mods"): {"data": []},
            }
        )
        mod_dir = Path("/tmp/my_mods/nonexistent-mod")
        with self.assertRaises(ModioError):
            find_remote_mod(client, mod_dir, None)

    def test_community_options_collection_bitmask(self):
        self.assertEqual(COMMUNITY_OPTIONS["allow_mod_use_in_collections"], 131072)
        self.assertEqual(COMMUNITY_OPTIONS["allow_mod_comments"], 1)
        self.assertEqual(COMMUNITY_OPTIONS["allow_dependency"], 1024)

    def test_extract_allowed_tag_map_handles_groups(self):
        game_tags = [
            {
                "name": "Type",
                "tags": ["Classes", "Spells", "Rules Changes"],
            },
            {
                "name": "Languages",
                "tags": ["English", "Spanish"],
            },
        ]
        tag_map = extract_allowed_tag_map(game_tags)
        self.assertIn("classes", tag_map)
        self.assertEqual(tag_map["classes"], "Classes")
        self.assertIn("ruleschanges", tag_map)
        self.assertEqual(tag_map["ruleschanges"], "Rules Changes")
        self.assertIn("english", tag_map)
        self.assertEqual(tag_map["english"], "English")

    def test_validate_selected_tags_canonicalizes_and_rejects_invalid(self):
        game_tags = [
            {
                "name": "Type",
                "tags": ["Classes", "Paladin", "Rules Changes"],
            }
        ]
        canonical = validate_selected_tags(["classes", "PALADIN"], game_tags)
        self.assertEqual(canonical, ["Classes", "Paladin"])

        with self.assertRaises(ModioError) as ctx:
            validate_selected_tags(["InvalidTag"], game_tags)
        self.assertIn("InvalidTag", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()

