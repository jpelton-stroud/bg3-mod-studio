import tempfile
import unittest
from pathlib import Path

from scripts.lib.env_paths import MY_MODS_DIR, normalize_mod_key, resolve_mod_dir
from scripts.lib.larian_parsers import (
    calculate_version64,
    compile_xml_bytes_to_loca,
    compile_xml_to_loca,
    decode_version64,
    format_version_tuple,
    has_balanced_parens,
    parse_loca_bytes,
    parse_localization_bytes,
    parse_meta_lsx,
    parse_progressions_lsx,
    parse_stats_txt,
    parse_version_str,
    split_larian_items,
)


class LarianParsersTests(unittest.TestCase):
    def test_version64_roundtrip(self):
        v64 = calculate_version64(1, 2, 3, 4)
        self.assertEqual(decode_version64(v64), (1, 2, 3, 4))
        self.assertEqual(format_version_tuple(decode_version64(v64)), "1.2.3.4")
        self.assertEqual(parse_version_str("2.1.0"), (2, 1, 0, 0))

    def test_split_larian_items_preserves_commas_in_parentheses(self):
        raw = "ActionResource(SpellSlot,1,1),Ability(Charisma,1,22);UnlockSpell(Target_Smite,1)"
        items = split_larian_items(raw)
        self.assertEqual(
            items,
            [
                "ActionResource(SpellSlot,1,1)",
                "Ability(Charisma,1,22)",
                "UnlockSpell(Target_Smite,1)",
            ],
        )

    def test_has_balanced_parens(self):
        self.assertTrue(has_balanced_parens("ActionResource(SpellSlot,1,1);AC(2)"))
        self.assertFalse(has_balanced_parens("ActionResource(SpellSlot"))
        self.assertFalse(has_balanced_parens("SpellSlot,1)"))

    def test_loca_compile_and_parse_roundtrip(self):
        xml_content = b"""<?xml version="1.0" encoding="utf-8"?>
<contentList>
    <content contentuid="h11111111g2222g3333g4444g555555555555" version="1">Blade of Dawn</content>
    <content contentuid="h66666666g7777g8888g9999gaaaaaaaaaaaa" version="2">Deals &lt;LSTag Tooltip="Radiant"&gt;1d8 Radiant&lt;/LSTag&gt; damage.</content>
</contentList>
"""
        loca_bytes = compile_xml_bytes_to_loca(xml_content)
        self.assertTrue(loca_bytes.startswith(b"LOCA"))
        parsed = parse_loca_bytes(loca_bytes, strip_tags=True)
        self.assertEqual(
            parsed["h11111111g2222g3333g4444g555555555555"],
            "Blade of Dawn",
        )
        self.assertEqual(
            parsed["h66666666g7777g8888g9999gaaaaaaaaaaaa"],
            "Deals 1d8 Radiant damage.",
        )

        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / "TestMod.xml"
            xml_path.write_bytes(xml_content)
            loca_path = compile_xml_to_loca(xml_path)
            self.assertTrue(loca_path.is_file())
            self.assertEqual(
                parse_localization_bytes(loca_path.read_bytes(), loca_path.name),
                parsed,
            )

    def test_parse_real_community_loca_file(self):
        real_loca = (
            Path(__file__).resolve().parent.parent
            / "mods"
            / "pact-and-power-warlock-equipment"
            / "data"
            / "PP_Warlock_Equipment.loca"
        )
        if real_loca.is_file():
            entries = parse_loca_bytes(real_loca.read_bytes())
            self.assertEqual(len(entries), 181)

    def test_resolve_mod_dir_handles_slug_and_uuid_folder(self):
        self.assertEqual(
            normalize_mod_key("PaladinsCall_7f92e4b1-82d3-4a16-9cf8-61d5302e1a90"),
            "paladinscall",
        )
        resolved_slug = resolve_mod_dir("paladins-call", roots=(MY_MODS_DIR,))
        resolved_uuid = resolve_mod_dir(
            "PaladinsCall_7f92e4b1-82d3-4a16-9cf8-61d5302e1a90",
            roots=(MY_MODS_DIR,),
        )
        if (MY_MODS_DIR / "paladins-call").is_dir():
            self.assertEqual(resolved_slug, (MY_MODS_DIR / "paladins-call").resolve())
            self.assertEqual(resolved_uuid, (MY_MODS_DIR / "paladins-call").resolve())

    def test_parse_meta_lsx(self):
        meta_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<save>
    <region id="Config">
        <node id="root">
            <children>
                <node id="ModuleInfo">
                    <attribute id="UUID" type="FixedString" value="11111111-2222-3333-4444-555555555555"/>
                    <attribute id="Name" type="LSString" value="TestMod"/>
                    <attribute id="Author" type="LSString" value="AuthorName"/>
                    <attribute id="Version64" type="int64" value="36028797018963968"/>
                </node>
            </children>
        </node>
    </region>
</save>"""
        meta = parse_meta_lsx(meta_xml)
        self.assertEqual(meta["UUID"], "11111111-2222-3333-4444-555555555555")
        self.assertEqual(meta["Name"], "TestMod")
        self.assertEqual(meta["Author"], "AuthorName")

    def test_parse_stats_txt(self):
        stats_txt = b"""
new entry "ARM_Magic_Robe"
type "Armor"
using "_Body"
data "ArmorClass" "12"
data "DisplayName" "h1234;1"
data "Description" "h5678;2"
"""
        loc_dict = {"h1234": "Magic Robe", "h5678": "A shimmering robe."}
        stats = parse_stats_txt(stats_txt, loc_dict=loc_dict)
        self.assertIn("ARM_Magic_Robe", stats)
        entry = stats["ARM_Magic_Robe"]
        self.assertEqual(entry["type"], "Armor")
        self.assertEqual(entry["data"]["ArmorClass"], "12")
        self.assertEqual(entry["resolved_display_name"], "Magic Robe")
        self.assertEqual(entry["resolved_description"], "A shimmering robe.")

    def test_parse_progressions_lsx(self):
        prog_xml = b"""<?xml version="1.0" encoding="utf-8"?>
<save>
    <region id="Progressions">
        <node id="root">
            <children>
                <node id="Progression">
                    <attribute id="Level" type="uint8" value="1"/>
                    <attribute id="Name" type="LSString" value="Paladin"/>
                    <attribute id="ProgressionType" type="uint8" value="0"/>
                    <attribute id="TableUUID" type="guid" value="aaaa-bbbb-cccc-dddd"/>
                </node>
            </children>
        </node>
    </region>
</save>"""
        progressions = parse_progressions_lsx(prog_xml)
        self.assertEqual(len(progressions), 1)
        self.assertEqual(progressions[0]["Name"], "Paladin")
        self.assertEqual(progressions[0]["Level"], "1")
        self.assertEqual(progressions[0]["TableUUID"], "aaaa-bbbb-cccc-dddd")


if __name__ == "__main__":
    unittest.main()
