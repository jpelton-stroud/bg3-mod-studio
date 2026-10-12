# Mod Creation Workflow Guide

This guide walks through creating, authoring, syncing, and testing a custom Baldur's Gate 3 mod using this project.

---

## 1. Scaffolding a New Mod

Use `scripts/create_mod_scaffold.py` to generate the complete directory layout:

```bash
python3 scripts/create_mod_scaffold.py \
  --name "ArcaneWeapons" \
  --description "Adds intelligent arcane weapons that scale with spellcasting ability." \
  --version "1.0.0.0"
```

If your mod expands character progression up to Level 20, add the `--unlock-level-curve` flag:
```bash
python3 scripts/create_mod_scaffold.py \
  --name "EldritchAscension" \
  --description "Unlocks level 13-20 Eldritch Knight progression." \
  --unlock-level-curve
```

The script produces:
- `my_mods/<ModName>_<UUID>/Projects/<UUID>/meta.lsx`
- `my_mods/<ModName>_<UUID>/Mods/<UUID>/meta.lsx`
- `my_mods/<ModName>_<UUID>/Public/<UUID>/Stats/Generated/Data/`
- `my_mods/<ModName>_<UUID>/Localization/English/<ModName>.xml`
- Clean 512x512 placeholder PNG thumbnail

---

## 2. Authoring Stats & Mechanics

Add standard Larian syntax files to `Public/<UUID>/Stats/Generated/Data/`:

### Example: Custom Weapon (`Weapon.txt`)
```text
new entry "MAG_ArcaneBlade"
type "Weapon"
using "WPN_Longsword_1"
data "RootTemplate" "f489b431-b842-491b-8531-97b7e71da5b8"
data "ValueUUID" "67e415ef-773a-449e-b81b-cc95ceba5b53"
data "Rarity" "Rare"
data "DefaultBoosts" "WeaponEnchantment(2);WeaponProperty(Finesse)"
data "PassivesOnEquip" "MAG_ArcaneBlade_Passive"
data "DisplayName" "h4a70cb6dg5661g4c14g98a0g70b4a45749f9;1"
data "Description" "ha3316e15g6546g48bag9827gc56306e90e78;1"
```

### Example: Passive Feature (`Passive.txt`)
```text
new entry "MAG_ArcaneBlade_Passive"
type "PassiveData"
data "DisplayName" "h4a70cb6dg5661g4c14g98a0g70b4a45749f9;1"
data "Description" "ha3316e15g6546g48bag9827gc56306e90e78;1"
data "Icon" "Spell_Evocation_MagicMissile"
data "Properties" "Highlighted"
data "Boosts" "UnlockSpell(Target_ArcaneStrike)"
```

---

## 3. Localization Handles

Add user-facing text strings to `Localization/English/<ModName>.xml`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<contentList>
  <content contentuid="h4a70cb6dg5661g4c14g98a0g70b4a45749f9" version="1">Blade of the Weave</content>
  <content contentuid="ha3316e15g6546g48bag9827gc56306e90e78" version="1">Attacks with this weapon use your Spellcasting Ability Modifier instead of Strength or Dexterity.</content>
</contentList>
```

---

## 4. Syncing into Baldur's Gate 3

Run the synchronizer to copy files into your game's `Data/` directory:

### Preview Sync Changes
```bash
python3 scripts/sync_to_game_data.py --dry-run
```

### Execute One-Time Sync
```bash
python3 scripts/sync_to_game_data.py
```

### Continuous Live Development (Watcher Mode)
```bash
python3 scripts/sync_to_game_data.py --watch
```
Any changes saved in `my_mods/` will automatically sync to your game's Data directory within seconds.

---

## 5. Testing & Publishing in the BG3 Toolkit

1. Launch the official **Baldur's Gate 3 Toolkit**.
2. Open your project from the Project Manager (it will appear under your mod's name and UUID).
3. Validate stats, root templates, and localizations.
4. Export package and publish directly to mod.io via the Toolkit's publisher window.
