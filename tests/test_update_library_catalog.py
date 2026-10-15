import tempfile
import unittest
from pathlib import Path

from scripts.modio_extract import generate_spec_markdown
from scripts.library_catalog import parse_library_rows
from scripts.update_library_catalog import (
    generate_library_markdown,
    parse_existing_mod_ids,
    parse_mod_readme,
    write_library_catalog,
)


class LibraryCatalogTests(unittest.TestCase):
    def test_parse_mod_readme_extracts_id_description_and_feature_count(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            mod_dir = Path(temporary_directory) / "gearup"
            mod_dir.mkdir()
            (mod_dir / "README.md").write_text(
                "# Mod Specification: GearUp\n"
                "**mod.io ID**: `12345`\n"
                "**Mod Slug**: `gearup` | **Features Documented**: 7 implemented\n\n"
                "## Overview\n"
                "Adds a complete equipment summoning system.\n",
                encoding="utf-8",
            )

            parsed = parse_mod_readme(mod_dir)

        self.assertEqual(parsed["mod_id"], "12345")
        self.assertEqual(parsed["slug"], "gearup")
        self.assertEqual(parsed["title"], "GearUp")
        self.assertEqual(parsed["description"], "Adds a complete equipment summoning system.")
        self.assertEqual(parsed["feature_count"], 7)

    def test_existing_legacy_ids_are_preserved_during_schema_migration(self):
        legacy_library = (
            "## Mod.io IDs\n"
            "| Mod Name | Slug | Mod.io ID |\n"
            "| :--- | :--- | ---: |\n"
            "| Alpha | `alpha` | 123 |\n"
            "| Beta | `beta` | 456 |\n"
        )

        self.assertEqual(
            parse_existing_mod_ids(legacy_library),
            {"alpha": "123", "beta": "456"},
        )

    def test_generated_rows_have_six_columns_and_relative_spec_links(self):
        markdown = generate_library_markdown(
            [
                {
                    "mod_id": "123",
                    "slug": "gearup",
                    "title": "GearUp",
                    "description": "Adds gear.",
                    "feature_count": 7,
                    "category": "Gear",
                }
            ]
        )
        rows = parse_library_rows(markdown)

        self.assertIn(
            "| Mod Id | Mod Name | Mod Slug | Description | Features Documented | Spec Link |",
            markdown,
        )
        self.assertEqual(
            rows[0],
            {
                "mod_id": "123",
                "name": "GearUp",
                "slug": "gearup",
                "description": "Adds gear.",
                "features_documented": "7 implemented",
                "spec_link": "gearup/README.md",
                "category": "Gear",
            },
        )
        self.assertNotIn("Mod.io IDs", markdown)

    def test_writer_migrates_known_ids_and_leaves_unknown_ids_blank(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            mods_dir = Path(temporary_directory) / "mods"
            mods_dir.mkdir()
            for slug in ("alpha", "beta"):
                mod_dir = mods_dir / slug
                mod_dir.mkdir()
                (mod_dir / "README.md").write_text(
                    f"# Mod Specification: {slug.title()}\n"
                    f"**Features Documented**: 2 implemented\n\n"
                    f"## Overview\nDescription for {slug}.\n",
                    encoding="utf-8",
                )
            library_file = mods_dir / "library.md"
            library_file.write_text(
                "## Mod.io IDs\n"
                "| Mod Name | Slug | Mod.io ID |\n"
                "| Alpha | `alpha` | 123 |\n",
                encoding="utf-8",
            )

            write_library_catalog(mods_dir, library_file)
            markdown = library_file.read_text(encoding="utf-8")
            rows = {row["slug"]: row for row in parse_library_rows(markdown)}

        self.assertEqual(rows["alpha"]["mod_id"], "123")
        self.assertEqual(rows["beta"]["mod_id"], "")
        self.assertEqual(rows["alpha"]["features_documented"], "2 implemented")
        self.assertEqual(rows["beta"]["spec_link"], "beta/README.md")
        self.assertNotIn("Mod.io IDs", markdown)

    def test_generated_spec_records_schema_metadata(self):
        spec = generate_spec_markdown(
            {
                "name": "Alpha",
                "name_id": "alpha",
                "id": 123,
                "summary": "A mod summary.",
                "submitted_by": {"username": "Author"},
                "modfile": {"version": "1.0"},
            },
            {"Author": "Author"},
            [
                {
                    "name": "Feature",
                    "type": "Spell",
                    "identifier": "Spell_Alpha",
                    "base_stats": "1d6 damage",
                    "granted_effects": "Deals fire damage",
                    "acquisition": "Level 1",
                }
            ],
            "Spells",
        )

        self.assertIn("**mod.io ID**: `123`", spec)
        self.assertIn("**Mod Slug**: `alpha`", spec)
        self.assertIn("**Features Documented**: 1 implemented", spec)


if __name__ == "__main__":
    unittest.main()
