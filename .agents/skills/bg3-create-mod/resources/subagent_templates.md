# Specialist Subagent Launch Templates (`bg3-create-mod`)

Reference definitions for the 4 concurrent subagents dispatched during Stage 1 mod creation.

All subagents must be launched with `"Model": "inherit"` and `"Workspace": "inherit"` in accordance with agentic guidelines.

```json
{
  "Subagents": [
    {
      "TypeName": "self",
      "Role": "Stats & Spells Specialist - <ModName>",
      "Prompt": "Author the BG3 stat entries in <stats_dir>. Mod: <ModName>, UUID: <UUID>.\nTo ensure 100% engine compliance and valid localization handle allocation, use:\n  python3 scripts/authoring/scaffold_stat_entry.py --mod <ModName> --type <weapon|armor|amulet|ring|spell_target|passivedata> --name <Id> --display-name \"<Name>\" --description \"<Desc>\" --props \"<Props>\"\nFor weapons/armor/objects, bind 3D visual models using:\n  python3 scripts/authoring/scaffold_root_template.py --mod <ModName> --item <Id> --visual-preset <greatsword|longsword|staff|plate|robe|amulet|ring|boots|cloak>\nFor custom item container/vendor drops, inject drops using:\n  python3 scripts/bg3.py mod inject-treasure --mod <ModName> --item <ItemName> --container <tutorial_chest|camp_chest|vendor_...>\nRefer to the approved plan for exact mechanics.",
      "Workspace": "inherit",
      "Model": "inherit"
    },
    {
      "TypeName": "self",
      "Role": "Progression & Lists Specialist - <ModName>",
      "Prompt": "Author Progressions.lsx and SpellLists.lsx for Mod: <ModName>, UUID: <UUID>.\nTo scaffold class progression levels without manual UUID errors, use:\n  python3 scripts/authoring/scaffold_progression_node.py --mod <ModName> --class-name <Class> --level <N> --progression-type <0|1> --boosts \"<Boosts>\" --passives \"<Passives>\" --selectors \"<Selectors>\"\nEnsure UnlockLevelCurve compat if level > 12. Refer to the approved plan for exact progression nodes.",
      "Workspace": "inherit",
      "Model": "inherit"
    },
    {
      "TypeName": "self",
      "Role": "Localization Specialist - <ModName>",
      "Prompt": "Audit and synchronize string handles in Localization/English/<ModName>.xml for Mod: <ModName>.\nEnsure all Stat entries, Spells, and Progression nodes have valid UUID handles (h...). Verify handle uniqueness and compile binary loca check:\n  python3 scripts/bg3.py mod sync-localization --mod <ModSlug> --check --json",
      "Workspace": "inherit",
      "Model": "inherit"
    },
    {
      "TypeName": "self",
      "Role": "Documentation Specialist - <ModName>",
      "Prompt": "Draft the root README.md for my_mods/<ModSlug>/README.md adhering to the Rich Feature Schema:\n- Overview & lore context\n- Verified feature tables (Stat ID, Slot/Type, Mechanics, Acquisition)\n- Installation & Xbox Series S compatibility notes\n- Render mod.io description preview: python3 scripts/bg3.py mod render-description --mod <ModSlug> --write --json",
      "Workspace": "inherit",
      "Model": "inherit"
    }
  ]
}
```
