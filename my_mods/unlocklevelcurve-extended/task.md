# Task List: UnlockLevelCurveExtended Patch Mod

- [x] Task 1: Initialize Mod Architecture & Metadata <!-- id: 0 -->
  - > Context: Create directory `my_mods/unlocklevelcurve-extended` with official toolkit structure (`Public/`, `Mods/`, `Projects/`, `Localization/`) and `meta.lsx` declaring dependency on `UnlockLevelCurve` (`a2ffd0e4-c407-8642-2611-c934ea0b0a77`) and `GustavDev`.
  - > Completed: Initialized official toolkit layout under `my_mods/unlocklevelcurve-extended` with dual `meta.lsx` files declaring GustavDev and UnlockLevelCurve dependencies.
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
  - > Completed: Authored `Localization/English/UnlockLevelCurveExtended.xml`, validated all 7 XML/LSX files and all TXT data files, confirmed progression cross-references, and generated comprehensive `README.md`.
- [x] Task 7: Implement Paladin Level 20 Sacred Oath Avatars <!-- id: 6 -->
  - > Context: Implement Elder Champion (Ancients), Holy Nimbus (Devotion), Avenging Angel (Vengeance), and Dread Lord (Oathbreaker) with custom transformations, auras, and sub-spells.
  - > Completed: Created 4 Level 20 avatar transformations with custom auras, stat boosts, damage pulses, fly speed, and sub-spells using native BG3 VFX and assets.
- [x] Task 8: Implement Monk Quivering Palm & Warlock Hurl Through Hell <!-- id: 7 -->
  - > Context: Implement Open Hand Monk Quivering Palm (2-stage hit & detonate) and Fiend Warlock Hurl Through Hell (banishment + 10d10 psychic on return).
  - > Completed: Built Quivering Palm 2-stage vibration application and detonation spells with Constitution save, and authored Hurl Through Hell banishment with delayed 10d10 psychic return explosion.
- [x] Task 9: Implement Rogue Death Strike & Thief's Reflexes <!-- id: 8 -->
  - > Context: Implement Assassin Death Strike (double damage on surprised targets) and Thief's Reflexes (extra Action and Bonus Action on Turn 1).
  - > Completed: Implemented Assassin Death Strike with double damage on surprised enemies and Thief's Reflexes Round 1 extra Action and Bonus Action surge.
- [x] Task 10: Implement Cleric Supreme Healing & Wizard Overchannel <!-- id: 9 -->
  - > Context: Implement Life Cleric Supreme Healing (max healing dice) and Evocation Wizard Overchannel (max spell damage with cascading exhaustion).
  - > Completed: Built Supreme Healing maximizing all incoming and outgoing healing dice, and created Overchannel maximizing spell damage with escalating self-necrotic exhaustion.
- [x] Task 11: Implement Bard Master's Flourish & Druid Beast Spells <!-- id: 10 -->
  - > Context: Implement Swords Bard at-will 1d6 Blade Flourishes and Druid Beast Spells (spellcasting enablement in Wild Shape).
  - > Completed: Created at-will 1d6 variants across all three Blade Flourishes (melee and ranged) costing 0 inspiration, and authored Druid Beast Spells and Moon Druid epic scaling.
- [x] Task 12: Update Progressions, Localization, Verification & Documentation <!-- id: 11 -->
  - > Context: Hook all new features into `Progressions.lsx`, update `UnlockLevelCurveExtended.xml`, run validation suite, and update `README.md` and walkthrough.
  - > Completed: Injected 11 progression nodes across class and subclass tables, mapped 74 localized strings, validated 100% clean test suite, and updated README and walkthrough.


