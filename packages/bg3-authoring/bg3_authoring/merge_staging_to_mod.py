#!/usr/bin/env python3
"""
Merge staged components from my_mods/arcane-progression/.staging/
into the official files of my_mods/arcane-progression/.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

MOD_DIR = Path("my_mods/arcane-progression")
STAGING_DIR = MOD_DIR / ".staging"
PUBLIC_DIR = MOD_DIR / "Public" / "ArcaneProgression_cfef8d1a-128b-4b02-b518-4177f162e61a"
LOCALIZATION_XML = MOD_DIR / "Localization" / "English" / "ArcaneProgression.xml"
PROGRESSIONS_LSX = PUBLIC_DIR / "Progressions" / "Progressions.lsx"
PROGRESSION_DESCRIPTIONS_LSX = PUBLIC_DIR / "Progressions" / "ProgressionDescriptions.lsx"
STATS_DIR = PUBLIC_DIR / "Stats" / "Generated" / "Data"

def merge_localization(staging_data: dict[str, Any], xml_path: Path) -> None:
    print("Merging localization...")
    tree = ET.parse(xml_path)
    root = tree.getroot()
    existing_uids = {c.get("contentuid") for c in root.findall("content")}

    added = 0
    for file_name, d in staging_data.items():
        loc = d.get("localization", [])
        if isinstance(loc, list):
            for item in loc:
                uid = item.get("handle")
                text = item.get("text", "")
                version = str(item.get("version", "1"))
                if uid and uid not in existing_uids:
                    elem = ET.SubElement(root, "content")
                    elem.set("contentuid", uid)
                    elem.set("version", version)
                    elem.text = text
                    existing_uids.add(uid)
                    added += 1
        elif isinstance(loc, dict):
            for uid, text in loc.items():
                if uid not in existing_uids:
                    elem = ET.SubElement(root, "content")
                    elem.set("contentuid", uid)
                    elem.set("version", "1")
                    elem.text = text
                    existing_uids.add(uid)
                    added += 1

    # Pretty indent
    ET.indent(tree, space="  ", level=0)
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)
    print(f"Added {added} localization strings to {xml_path}")

def format_stat_entry(
    entry_type: str,
    name: str,
    data: dict[str, Any],
    using: str | None = None,
    spell_type: str | None = None,
    status_type: str | None = None,
) -> str:
    lines = [f'new entry "{name}"', f'type "{entry_type}"']
    if using:
        lines.append(f'using "{using}"')
    if spell_type:
        lines.append(f'data "SpellType" "{spell_type}"')
    if status_type:
        lines.append(f'data "StatusType" "{status_type}"')
    for k, v in data.items():
        if k in ("SpellType", "StatusType"):
            continue
        lines.append(f'data "{k}" "{v}"')
    return "\n".join(lines) + "\n\n"

def append_stats_file(file_path: Path, entries_text: str) -> None:
    if not entries_text.strip():
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    new_text = ""
    for block in entries_text.split("new entry "):
        if not block.strip():
            continue
        full_block = "new entry " + block
        name = block.split('"')[1]
        if f'new entry "{name}"' not in content:
            new_text += full_block
    if new_text:
        with open(file_path, "a", encoding="utf-8") as f:
            if not content.endswith("\n\n"):
                f.write("\n")
            f.write(new_text)
        print(f"Appended new entries to {file_path}")

def merge_stats(staging_data: dict[str, Any]) -> None:
    print("Merging stats files...")
    passives_text = ""
    statuses_text = ""
    interrupts_text = ""
    shouts_text = ""
    targets_text = ""
    zones_text = ""
    projectiles_text = ""

    for fname, d in staging_data.items():
        # Passives
        for p in d.get("passives", []):
            if "raw" in p and p["raw"]:
                passives_text += p["raw"] + "\n\n"
            else:
                passives_text += format_stat_entry(p.get("type", "PassiveData"), p["name"], p.get("data", {}))

        # Statuses
        for s in d.get("statuses", []):
            if "raw" in s and s["raw"]:
                statuses_text += s["raw"] + "\n\n"
            else:
                statuses_text += format_stat_entry(s.get("type", "StatusData"), s["name"], s.get("data", {}), using=s.get("using"), status_type=s.get("status_type"))

        # Interrupts
        for i in d.get("interrupts", []):
            if "raw" in i and i["raw"]:
                interrupts_text += i["raw"] + "\n\n"
            else:
                interrupts_text += format_stat_entry(i.get("type", "InterruptData"), i["name"], i.get("data", {}), using=i.get("using"))

        # Spells
        for sp in d.get("spells", []):
            stype = sp.get("spell_type") or sp.get("data", {}).get("SpellType")
            sname = sp.get("name")
            text = sp.get("raw") + "\n\n" if ("raw" in sp and sp["raw"]) else format_stat_entry(sp.get("type", "SpellData"), sname, sp.get("data", {}), using=sp.get("using"), spell_type=stype)

            if stype == "Shout" or sname.startswith("Shout_"):
                shouts_text += text
            elif stype == "Target" or sname.startswith("Target_"):
                targets_text += text
            elif stype == "Zone" or sname.startswith("Zone_"):
                zones_text += text
            elif stype == "Projectile" or sname.startswith("Projectile_"):
                projectiles_text += text
            else:
                targets_text += text

    append_stats_file(STATS_DIR / "Passive.txt", passives_text)
    append_stats_file(STATS_DIR / "Status_BOOST.txt", statuses_text)
    append_stats_file(STATS_DIR / "Interrupt.txt", interrupts_text)
    append_stats_file(STATS_DIR / "Spell_Shout.txt", shouts_text)
    append_stats_file(STATS_DIR / "Spell_Target.txt", targets_text)
    append_stats_file(STATS_DIR / "Spell_Zone.txt", zones_text)
    append_stats_file(STATS_DIR / "Spell_Projectile.txt", projectiles_text)

def create_progression_node(parent_children: ET.Element, pdict: dict[str, Any]) -> None:
    node = ET.SubElement(parent_children, "node", id="Progression")
    for key, val in pdict.items():
        if key in ("xml", "raw_xml"):
            continue
        attr = ET.SubElement(node, "attribute", id=key)
        if key in ("Level", "ProgressionType"):
            attr.set("type", "uint8")
            attr.set("value", str(val))
        elif key in ("TableUUID", "UUID"):
            attr.set("type", "guid")
            attr.set("value", str(val))
        elif key == "AllowImprovement":
            attr.set("type", "bool")
            attr.set("value", "true" if val else "false")
        else:
            attr.set("type", "LSString")
            attr.set("value", str(val))

def create_progression_desc_node(parent_children: ET.Element, pdict: dict[str, Any]) -> None:
    node = ET.SubElement(parent_children, "node", id="ProgressionDescription")
    for key, val in pdict.items():
        if key in ("xml", "raw_xml"):
            continue
        attr = ET.SubElement(node, "attribute", id=key)
        if key in ("Description", "DisplayName"):
            attr.set("type", "TranslatedString")
            handle = str(val).split(";")[0]
            attr.set("handle", handle)
            attr.set("version", "1")
        elif key in ("ProgressionTableId", "ProgressionId", "UUID"):
            attr.set("type", "guid")
            attr.set("value", str(val))
        elif key in ("ExactMatch", "PassivePrototype", "SelectorId", "Type"):
            attr.set("type", "FixedString")
            attr.set("value", str(val))
        else:
            attr.set("type", "LSString")
            attr.set("value", str(val))

def merge_lsx(staging_data: dict[str, Any]) -> None:
    print("Merging Progressions.lsx...")
    tree = ET.parse(PROGRESSIONS_LSX)
    root = tree.getroot()
    children = root.find(".//region[@id='Progressions']/node[@id='root']/children")
    if children is None:
        return

    existing_uuids = set()
    for n in children.findall("node[@id='Progression']"):
        for a in n.findall("attribute[@id='UUID']"):
            existing_uuids.add(a.get("value"))

    added_progs = 0
    for fname, d in staging_data.items():
        for p in d.get("progressions", []):
            puuid = p.get("UUID")
            if "raw_xml" in p and p["raw_xml"]:
                # Parse raw xml
                subelem = ET.fromstring(p["raw_xml"])
                u_node = subelem.find("attribute[@id='UUID']")
                u = u_node.get("value") if u_node is not None else None
                if u and u not in existing_uuids:
                    children.append(subelem)
                    existing_uuids.add(u)
                    added_progs += 1
            elif "xml" in p and p["xml"]:
                subelem = ET.fromstring(p["xml"])
                u_node = subelem.find("attribute[@id='UUID']")
                u = u_node.get("value") if u_node is not None else None
                if u and u not in existing_uuids:
                    children.append(subelem)
                    existing_uuids.add(u)
                    added_progs += 1
            else:
                if puuid and puuid not in existing_uuids:
                    create_progression_node(children, p)
                    existing_uuids.add(puuid)
                    added_progs += 1

    ET.indent(tree, space="    ", level=0)
    tree.write(PROGRESSIONS_LSX, encoding="utf-8", xml_declaration=True)
    print(f"Added {added_progs} progressions to {PROGRESSIONS_LSX}")

    print("Merging ProgressionDescriptions.lsx...")
    dtree = ET.parse(PROGRESSION_DESCRIPTIONS_LSX)
    droot = dtree.getroot()
    dchildren = droot.find(".//region[@id='ProgressionDescriptions']/node[@id='root']/children")
    if dchildren is None:
        return

    existing_desc_uuids = set()
    for n in dchildren.findall("node[@id='ProgressionDescription']"):
        for a in n.findall("attribute[@id='UUID']"):
            existing_desc_uuids.add(a.get("value"))

    added_descs = 0
    for fname, d in staging_data.items():
        for pd in d.get("progression_descriptions", []):
            duuid = pd.get("UUID")
            if "raw_xml" in pd and pd["raw_xml"]:
                subelem = ET.fromstring(pd["raw_xml"])
                u_node = subelem.find("attribute[@id='UUID']")
                u = u_node.get("value") if u_node is not None else None
                if u and u not in existing_desc_uuids:
                    dchildren.append(subelem)
                    existing_desc_uuids.add(u)
                    added_descs += 1
            elif "xml" in pd and pd["xml"]:
                subelem = ET.fromstring(pd["xml"])
                u_node = subelem.find("attribute[@id='UUID']")
                u = u_node.get("value") if u_node is not None else None
                if u and u not in existing_desc_uuids:
                    dchildren.append(subelem)
                    existing_desc_uuids.add(u)
                    added_descs += 1
            else:
                if duuid and duuid not in existing_desc_uuids:
                    create_progression_desc_node(dchildren, pd)
                    existing_desc_uuids.add(duuid)
                    added_descs += 1

    ET.indent(dtree, space="    ", level=0)
    dtree.write(PROGRESSION_DESCRIPTIONS_LSX, encoding="utf-8", xml_declaration=True)
    print(f"Added {added_descs} progression descriptions to {PROGRESSION_DESCRIPTIONS_LSX}")

def main() -> None:
    staging_data = {}
    for name in ["martials", "divine", "arcane"]:
        fpath = STAGING_DIR / f"{name}.json"
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                staging_data[name] = json.load(f)
            print(f"Loaded {fpath.name}")
        else:
            print(f"Warning: {fpath} does not exist!")

    merge_localization(staging_data, LOCALIZATION_XML)
    merge_stats(staging_data)
    merge_lsx(staging_data)
    print("Merge complete!")

if __name__ == "__main__":
    main()
