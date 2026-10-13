# Task List: ArcaneProgression Patch Mod

- [x] Task 1: Initialize Mod Architecture & Metadata <!-- id: 0 -->
  - > Context: Create directory `my_mods/arcane-progression` with official toolkit structure (`Public/`, `Mods/`, `Projects/`, `Localization/`) and `meta.lsx` declaring dependency on `UnlockLevelCurve` (`a2ffd0e4-c407-8642-2611-c934ea0b0a77`) and `GustavDev`.
  - > Completed: Initialized official toolkit layout under `my_mods/arcane-progression` with dual `meta.lsx` files declaring GustavDev and UnlockLevelCurve dependencies.
- [x] Task 2: Implement Simple Category Base & Subclass Fixes <!-- id: 1 -->
  - > Context: Implement Fighter Action Surge 2 (Lvl 17), hook orphaned Abjuration Spell Resistance (Lvl 14), Ranger Vanish (Lvl 14), Paladin Purity of Spirit (Lvl 15 Devotion), Paladin Supernatural Resistance (Lvl 15 Oathbreaker), Paladin Undying Sentinel (Lvl 15 Ancients), Hunter Superior Hunter's Defense (Lvl 15), fix broken Rogue Elusive (Lvl 18), and Draconic Sorcerer Dragon Wings (Lvl 14).
  - > Completed: Authored passives, boosts, and progression injections for all simple fixes.
- [x] Task 3: Implement Moderate Category Class Features (Monk, Rogue, Paladin, Wizard, Ranger) <!-- id: 2 -->
  - > Context: Implement Monk Diamond Soul (Lvl 14 save proficiencies + Ki reroll interrupt) & Empty Body (Lvl 18 4-Ki invisibility + resistance shout), Paladin Cleansing Touch (Lvl 14 spell purge) & 30ft Auras (Lvl 18), Rogue Stroke of Luck (Lvl 20 interrupt), Wizard Focused Conjuration (Lvl 14) & Spell Mastery (Lvl 18 free 1st/2nd lvl spells), Ranger Feral Senses (Lvl 18) & Foe Slayer (Lvl 20).
  - > Completed: Implemented all core moderate base class features with dedicated shout/target spells, statuses, and reaction interrupts.
- [x] Task 4: Implement Moderate Category Subclass Features (Monk, Ranger, Sorcerer, Paladin) <!-- id: 3 -->
  - > Context: Implement Shadow Monk Opportunist (Lvl 17 reaction attack on ally damage), Gloom Stalker Shadowy Dodge (Lvl 15 reaction disadvantage), Storm Sorcerer Storm's Fury (Lvl 14 reaction lightning + push), and Vengeance Paladin Soul of Vengeance (Lvl 15 reaction attack).
  - > Completed: Implemented reaction interrupts and retaliation functors for all moderate subclass milestones.
- [x] Task 5: Implement High-Tier Warlock Invocations & Broad Spell Mastery Selection <!-- id: 4 -->
  - > Context: Add Shroud of Shadows (at-will Invisibility), Master of Myriad Forms (at-will Disguise Self), and broad 1st/2nd level Spell Mastery spell lists and definitions.
  - > Completed: Created 24 at-will Spell Mastery variants across 1st and 2nd level spells with dedicated SpellLists and ProgressionDescriptions, and integrated high-level Warlock invocations.
- [x] Task 6: Localization, Verification & Documentation <!-- id: 5 -->
  - > Context: Write `english.xml` / `ProgressionDescriptions.lsx` for new display names and descriptions, validate XML syntax across all `.lsx` files, ensure schema conformance, and generate `README.md`.
  - > Completed: Authored `Localization/English/ArcaneProgression.xml`, validated all 7 XML/LSX files and all TXT data files, confirmed progression cross-references, and generated comprehensive `README.md`.
