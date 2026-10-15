# Arcane Progression

- **Mod slug:** `arcane-progression`
- **Module UUID:** `cfef8d1a-128b-4b02-b518-4177f162e61a`
- **Larian folder:** `ArcaneProgression_cfef8d1a-128b-4b02-b518-4177f162e61a`
- **Version:** `1.0.0.0`
- **Author:** MTGHillGiant

## Overview

Arcane Progression is a companion patch mod for UnlockLevelCurve (by Charis). While UnlockLevelCurve unlocks character levels up to 20 and integrates high-level spell slots and upcasting, many iconic 5th Edition D&D class and subclass features between levels 13 and 20 were left unimplemented or broken.

This mod implements high-level features that do not require a script editor or other advanced tooling, fixes non-functional entries in the parent mod (such as Rogue's empty `Elusive` passive and Wizard's orphaned `SpellResistance`), and broadens high-tier choices like Wizard Spell Mastery and Warlock Invocations.

## Features

### Base Class Features

| Class | Level | Feature | Mechanics |
| :--- | :---: | :--- | :--- |
| **Fighter** | 17 | **Action Surge (2 Uses)** | Adds a second charge to Action Surge per rest. |
| **Monk** | 14 | **Diamond Soul** | Grants proficiency across all six saving throws (STR, DEX, CON, INT, WIS, CHA) and a reaction that spends 1 Ki point to reroll a failed saving throw. |
| **Monk** | 18 | **Empty Body** | Active shout costing 4 Ki: grants Invisibility and resistance to all damage types except Force for 10 turns. |
| **Paladin** | 14 | **Cleansing Touch** | Active ability removing harmful magical ailments, curses, charms, and conditions from self or allies. |
| **Paladin** | 18 | **Aura Range Improvement** | Expands the radius of Paladin auras to 9m (30ft). |
| **Ranger** | 14 | **Vanish** | Gain the ability to use the Hide action as a Bonus Action. |
| **Ranger** | 18 | **Feral Senses** | Immune to Blinded and permanently detects invisible creatures within 9m. |
| **Ranger** | 20 | **Foe Slayer** | Adds Wisdom Modifier to weapon attack rolls and damage rolls. |
| **Rogue** | 18 | **Elusive (Fixed)** | Fixes the broken parent implementation: attackers cannot land critical hits or roll with advantage against the Rogue while not incapacitated. |
| **Rogue** | 20 | **Stroke of Luck** | Once per Short Rest, turn a missed attack roll into an immediate reroll with advantage to secure a hit. |
| **Wizard** | 18 | **Spell Mastery** | Select one 1st-level and one 2nd-level wizard spell from a curated pool to cast at will without expending spell slots. |
| **Warlock** | 15 & 18 | **High-Tier Invocations** | Level 15 grants _Master of Myriad Forms_ (at-will _Disguise Self_); Level 18 grants _Shroud of Shadows_ (at-will self _Invisibility_). |

### Subclass Features

| Subclass | Parent Class | Level | Feature | Mechanics |
| :--- | :--- | :---: | :--- | :--- |
| **Abjuration School** | Wizard | 14 | **Spell Resistance** | Hooks up the parent mod's orphaned passive: advantage on all spell saving throws and resistance against spell damage. |
| **Conjuration School** | Wizard | 14 | **Focused Conjuration** | Concentration on Conjuration spells cannot be broken by incoming damage. |
| **Oath of Devotion** | Paladin | 15 | **Purity of Spirit** | Permanent immunity to Charmed and Frightened, with permanent _Protection from Evil and Good_. |
| **Oath of the Ancients** | Paladin | 15 | **Undying Sentinel** | Once per Long Rest, when reduced to 0 HP, drop to 1 HP instead. |
| **Oathbreaker** | Paladin | 15 | **Supernatural Resistance** | Resistance to non-magical bludgeoning, piercing, and slashing damage. |
| **Oath of Vengeance** | Paladin | 15 | **Soul of Vengeance** | Reaction melee attack whenever a creature marked with Vow of Enmity makes an attack. |
| **Way of Shadow** | Monk | 17 | **Opportunist** | Reaction melee strike when an ally hits an adjacent hostile creature. |
| **Draconic Bloodline** | Sorcerer | 14 | **Dragon Wings** | Permanent dragon wings granting flight at will and bonus movement speed. |
| **Storm Sorcery** | Sorcerer | 14 | **Storm's Fury** | Reaction when struck by a melee attack: deals 14 Lightning damage to the attacker and pushes them 6m back. |
| **Gloom Stalker** | Ranger | 15 | **Shadowy Dodge** | Reaction when attacked to impose disadvantage on the attacker's roll. |
| **Hunter** | Ranger | 15 | **Superior Hunter's Defense** | Gains Evasion to negate area damage on successful Dexterity saving throws. |

### Wizard Spell Mastery Options

**Level 1:** _Shield, Mage Armor, Magic Missile, Longstrider, Fog Cloud, Grease, Feather Fall, Thunderwave, Burning Hands, Chromatic Orb, Ray of Sickness,_ and _False Life_.

**Level 2:** _Misty Step, Mirror Image, Blur, Web, Darkness, Scorching Ray, Hold Person, Invisibility, Cloud of Daggers, Shatter, Blindness,_ and _Phantasmal Force_.

## Dependencies

- **Required:** Baldur's Gate 3 base game module `GustavX`.
- **Required:** `UnlockLevelCurve` (`a2ffd0e4-c407-8642-2611-c934ea0b0a77`). Load UnlockLevelCurve before Arcane Progression.

## Compatibility

- **Game version:** Baldur's Gate 3; authored for the Patch 7 / Patch 8 Native Toolkit.
- **Known conflicts:** None documented.

## Additional Credits

None listed.
