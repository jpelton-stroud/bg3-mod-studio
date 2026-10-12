# Mod Specification: UnlockLevelCurveExtended (Level 13-20 5e Feature Expansion)

**Category**: Classes, Progression & Bugfixes | **Author**: jpstroud | **Parent Dependency**: `UnlockLevelCurve` (`a2ffd0e4-c407-8642-2611-c934ea0b0a77`)  
**Toolkit Target**: Patch 7 / Patch 8 Native Toolkit Drag-and-Drop Structure

---

## Overview

**UnlockLevelCurveExtended** is a companion patch mod designed to load after **UnlockLevelCurve** (by Charis). While *UnlockLevelCurve* unlocks character levels up to 20 and integrates high-level spell slots and upcasting, many iconic 5th Edition D&D class and subclass features between levels 13 and 20 were left unimplemented or broken.

This mod addresses all **Simple** and **Moderate** complexity gaps from 5e D&D, fixes non-functional entries in the parent mod (such as Rogue's empty `Elusive` passive and Wizard's orphaned `SpellResistance`), and broadens high-tier choices like Wizard Spell Mastery and Warlock Invocations.

---

## Dependency & Load Order

In BG3 Mod Manager or the in-game mod loader, ensure the following load order:
1. `GustavDev` (Base Game)
2. `UnlockLevelCurve` (by Charis)
3. **`UnlockLevelCurveExtended`** (This mod)

---

## Implemented Features

### 1. Base Class Features

| Class | Level | Feature | Mechanics |
| :--- | :---: | :--- | :--- |
| **Fighter** | 17 | **Action Surge (2 Uses)** | Adds a second charge to Action Surge per rest. |
| **Monk** | 14 | **Diamond Soul** | Grants proficiency across **all 6 saving throws** (STR, DEX, CON, INT, WIS, CHA) + reaction interrupt spending 1 Ki point to reroll failed saving throws. |
| **Monk** | 18 | **Empty Body** | Active shout costing 4 Ki: grants Invisibility and resistance to all damage types except Force for 10 turns. |
| **Paladin** | 14 | **Cleansing Touch** | Active ability removing harmful magical ailments, curses, charms, and conditions from self or allies. |
| **Paladin** | 18 | **Aura Range Improvement** | Expands the radius of Paladin auras to 9m (30ft). |
| **Ranger** | 14 | **Vanish** | Gain the ability to use the Hide action as a Bonus Action. |
| **Ranger** | 18 | **Feral Senses** | Immune to Blinded and permanently detects invisible creatures within 9m. |
| **Ranger** | 20 | **Foe Slayer** | Adds Wisdom Modifier to weapon attack rolls and damage rolls. |
| **Rogue** | 18 | **Elusive (Fixed)** | Fixes the broken parent implementation: attackers cannot land critical hits or roll with advantage against the Rogue while not incapacitated. |
| **Rogue** | 20 | **Stroke of Luck** | Once per Short Rest, turn a missed attack roll into an immediate reroll with advantage to secure a hit. |
| **Wizard** | 18 | **Spell Mastery** | Select one 1st-level and one 2nd-level wizard spell from a broad curated pool to cast **at will without expending spell slots**. |
| **Warlock** | 15 & 18 | **High-Tier Invocations** | Level 15 grants *Master of Myriad Forms* (at-will *Disguise Self*); Level 18 grants *Shroud of Shadows* (at-will self *Invisibility*). |

---

### 2. Subclass Features

| Subclass | Parent Class | Level | Feature | Mechanics |
| :--- | :--- | :---: | :--- | :--- |
| **Abjuration School** | Wizard | 14 | **Spell Resistance** | Hooks up the parent mod's orphaned passive: advantage on all spell saving throws and resistance against spell damage. |
| **Conjuration School** | Wizard | 14 | **Focused Conjuration** | Concentration on Conjuration spells cannot be broken by incoming damage. |
| **Oath of Devotion** | Paladin | 15 | **Purity of Spirit** | Permanent immunity to Charmed and Frightened, with permanent *Protection from Evil and Good*. |
| **Oath of the Ancients** | Paladin | 15 | **Undying Sentinel** | Once per Long Rest, when reduced to 0 HP, drop to 1 HP instead. |
| **Oathbreaker** | Paladin | 15 | **Supernatural Resistance** | Resistance to non-magical bludgeoning, piercing, and slashing damage. |
| **Oath of Vengeance** | Paladin | 15 | **Soul of Vengeance** | Reaction melee attack whenever a creature marked with Vow of Enmity makes an attack. |
| **Way of Shadow** | Monk | 17 | **Opportunist** | Reaction melee strike when an ally hits an adjacent hostile creature. |
| **Draconic Bloodline** | Sorcerer | 14 | **Dragon Wings** | Permanent dragon wings granting flight at will and bonus movement speed. |
| **Storm Sorcery** | Sorcerer | 14 | **Storm's Fury** | Reaction when struck by a melee attack: deals 14 Lightning damage to the attacker and pushes them 6m back. |
| **Gloom Stalker** | Ranger | 15 | **Shadowy Dodge** | Reaction when attacked to impose disadvantage on the attacker's roll. |
| **Hunter** | Ranger | 15 | **Superior Hunter's Defense** | Gains Evasion to negate area damage on successful Dexterity saving throws. |

---

### 3. Wizard Spell Mastery Options

#### Level 1 Selection:
* *Shield, Mage Armor, Magic Missile, Longstrider, Fog Cloud, Grease, Feather Fall, Thunderwave, Burning Hands, Chromatic Orb, Ray of Sickness, False Life*

#### Level 2 Selection:
* *Misty Step, Mirror Image, Blur, Web, Darkness, Scorching Ray, Hold Person, Invisibility, Cloud of Daggers, Shatter, Blindness, Phantasmal Force*

---

### 4. Complex Features (Level 20 Avatars, Capstones & Multi-Stage Transformations)

| Class / Subclass | Level | Feature | Mechanics |
| :--- | :---: | :--- | :--- |
| **Paladin (Oath of the Ancients)** | 20 | **Elder Champion** | 10-turn transformation: 10 HP/turn regeneration, bonus action spellcasting, and 3m aura giving enemies disadvantage on saves vs your spells. |
| **Paladin (Oath of Devotion)** | 20 | **Holy Nimbus** | 10-turn transformation: dazzling 9m daylight aura dealing 10 radiant damage/turn to fiends and undead, with advantage on saving throws vs spells. |
| **Paladin (Oath of Vengeance)** | 20 | **Avenging Angel** | 10-turn transformation: angelic flight (+6m speed) and 9m terror aura that frightens foes and grants advantage on attack rolls against frightened targets. |
| **Paladin (Oathbreaker)** | 20 | **Dread Lord** | 10-turn transformation: 9m gloom aura frightening foes, dealing 4d10 psychic damage/turn to frightened enemies, and unlocking bonus action 3d10 necrotic Shadow Attack. |
| **Monk (Way of the Open Hand)** | 17 | **Quivering Palm** | Spend 3 Ki to impart vibrations lasting 100 turns. Detonate at will: target makes a Constitution save, taking 100 necrotic damage on failure or 10d10 necrotic damage on success. |
| **Warlock (The Fiend)** | 14 | **Hurl Through Hell** | Banishes target to the lower planes for 1 turn upon hit; target takes 10d10 psychic damage upon return (1/Long Rest). |
| **Rogue (Assassin)** | 17 | **Death Strike** | Doubles all damage dealt when striking a Surprised enemy. |
| **Rogue (Thief)** | 17 | **Thief's Reflexes** | On Turn 1 of any combat, gain an additional Action and an additional Bonus Action. |
| **Cleric (Life Domain)** | 17 | **Supreme Healing** | Maximizes all dice rolled when casting healing spells or receiving healing. |
| **Wizard (Evocation School)** | 14 | **Overchannel** | Maximize spell damage on your next cast. Consecutive uses before rest deal escalating necrotic damage to self. |
| **Bard (College of Swords)** | 14 | **Master's Flourish** | At-will 1d6 variants of Slashing, Defensive, and Mobile Flourishes costing zero Bardic Inspiration charges. |
| **Druid (All Circles)** | 18 | **Beast Spells** | Eliminates Wild Shape polymorph mute restrictions, allowing spellcasting while wildshaped. |
| **Druid (Circle of the Moon)** | 16 | **Wild Shape Epic Scaling** | Epic scaling boost granting +1 Wild Shape charge, +1 attack roll bonus, and +1d6 bonus damage. |

