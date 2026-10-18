# Shadow's Call

- **Mod slug:** `shadows-call`
- **Module UUID:** `c570bfb5-705c-45a3-8424-e90ce90d23d7`
- **Larian folder:** `ShadowsCall_c570bfb5-705c-45a3-8424-e90ce90d23d7`
- **Version:** `1.0.0.0`
- **Author:** MTGHillGiant

## Overview

Shadow's Call modernizes the Rogue class along with its iconic **Arcane Trickster** and **Assassin** subclasses in Baldur's Gate 3 according to **D&D 2024 Player's Handbook (5.5e)** standards. It transitions the Rogue from a one-dimensional Sneak Attack delivery system into a versatile, high-agency skirmisher and infiltrator.

Key pillars of this overhaul include:
- **Shared Cunning Strike Engine (2024 PHB):** Forfeit Sneak Attack dice to deliver tactical debuffs—Trip, Withdraw, Poison, and Daze—giving Rogues round-to-round crowd control and repositioning power.
- **2024 Reliable Talent Reschedule:** Shifted from Level 11 to Level 7, establishing early mastery in lockpicking, pickpocketing, stealth, and skill checks.
- **Unbound Arcane Infiltration (Arcane Trickster):** Removes legacy Enchantment/Illusion school locks to unlock the complete Wizard spell library (*Shield*, *Misty Step*, *Mirror Image*, *Shadow Blade*), grants permanent invisible Mage Hand Legerdemain with an Arcane Distraction aura for guaranteed Sneak Attack advantage, and introduces high-level spell theft.
- **Lethal & Dialogue-Resilient Ambushes (Assassin):** Fixes dialogue-spoiled Turn 1 ambushes with flat level-scaling damage on opening rounds, grants +2 Initiative, adds chain-invisibility resets (*Shadow Dance*) on kills and critical hits, bypasses poison immunities, and delivers devastating *Death Strikes*.
- **Level 13–20 UnlockLevelCurve Integration:** Seamlessly authored for Patch 7 and Patch 8 with native UnlockLevelCurve (ULC) progression all the way to Level 20.

---

## Features

### 1. Core Rogue Foundation (D&D 2024 Standards)

- **Level 5 — Cunning Strike:**
  When Sneak Attack conditions are met, sacrifice damage dice to apply tactical status effects:
  - **Trip** (Costs 1d6): Forces a Dexterity saving throw; on failure, knocks the target **Prone**, granting immediate advantage to subsequent melee strikes.
  - **Withdraw** (Costs 1d6): Instantly grants the benefits of **Disengage** and **+3m Movement Speed** for the turn without consuming a Bonus Action.
  - **Poison** (Costs 1d6): Forces a Constitution saving throw; on failure, inflicts **Poisoned** for 1 minute (10 turns), imposing disadvantage on attack rolls and ability checks.
- **Level 7 — Reliable Talent (2024 Shift):**
  Shifted from Level 11 to Level 7. Whenever you make an ability check with a proficient skill or tool, any d20 roll of 9 or lower is treated as a 10, ensuring guaranteed success on core rogue operations.
- **Level 11 — Improved Cunning Strike:**
  - **Daze** (Costs 2d6): Forces a Constitution saving throw; on failure, target loses its Reactions and is restricted to either an Action or a Bonus Action on its next turn.

---

### 2. Arcane Trickster: Unbound Arcane Infiltrator

- **Level 3 — Unbound Arcane Spellbook (2024 PHB):**
  Abolishes vanilla school limitations (previously locked to Enchantment and Illusion). Arcane Tricksters can freely select, prepare, and cast spells across the entire Wizard spell list, enabling staples like *Shield*, *Misty Step*, *Mirror Image*, *Shadow Blade*, *Hold Person*, *Haste*, and *Counterspell*.
- **Level 3 — Mage Hand Legerdemain Mastery:**
  - **Permanent Mage Hand:** Recastable as an out-of-combat ritual; lasts until dismissed, destroyed, or Long Rest (removes the vanilla 10-turn duration and Short Rest cooldown).
  - **Permanent Invisibility:** The Mage Hand remains permanently invisible, enabling undetected scouting and hazard manipulation.
  - **Arcane Distraction Aura:** While within 3m of the Mage Hand, enemies suffer the *Distracted* condition, granting the Arcane Trickster Advantage on attack rolls against them (guaranteeing Sneak Attack readiness).
- **Level 9 — Magical Ambush Enhanced:**
  When casting a spell from stealth or invisibility, hostile targets suffer Disadvantage on all saving throws against the spell.
- **Level 13 (ULC) — Versatile Trickster:**
  Command your Mage Hand using a Bonus Action to channel Cunning Strike riders (*Trip*, *Daze*) directly against distant targets.
- **Level 17 (ULC) — Spell Thief:**
  When targeted by a spell, expend a Reaction to negate the spell's effect and gain a free single cast of that spell until your next Long Rest.

---

### 3. Assassin: Lethal Executioner

- **Level 3 — Assassinate (2024 Standards & Dialogue-Proofing):**
  - **Combat Readiness:** +2 bonus to Initiative (`Initiative(2)`).
  - **Opening Gambit:** Advantage on attack rolls against any target that has not yet taken a turn in combat.
  - **Executioner's Strike:** On Round 1 of combat, your weapon attacks against any target that hasn't taken a turn deal **bonus flat damage equal to your Rogue Level**. (Surprised targets still suffer automatic Critical Hits, multiplying weapon and bonus dice!).
  - **Assassinate Alacrity:** Instantly refreshes your Action and Bonus Action upon entering combat.
- **Level 9 — Shadow Dance & Penetrating Toxins:**
  - **Shadow Dance:** Reducing an enemy to 0 HP with a weapon attack or scoring a Critical Hit immediately turns you **Invisible** for 1 turn and restores your Reaction, enabling fluid hit-and-run kill chains.
  - **Penetrating Toxins:** Attacks and poisons ignore Poison Resistance entirely and treat Poison Immunity as Resistance.
- **Level 13 (ULC) — Envenomed Strike:**
  Inflicting Cunning Strike *Poison* deals an additional **+2d6 unresistable Necrotic damage**.
- **Level 17 (ULC) — Death Strike:**
  Attacking a surprised target or attacking from stealth on Round 1 forces a Constitution saving throw (DC based on Dexterity); on failure, all damage dealt on that hit is doubled.

---

## Progression Summary

### Core Rogue Progression (Levels 1–20)

| Level | Vanilla BG3 | Shadow's Call (2024 Modernized) |
| :---: | :--- | :--- |
| **1** | Sneak Attack (1d6), Expertise, Thieves' Cant | Sneak Attack (1d6), Expertise, Thieves' Cant |
| **2** | Cunning Action (Dash, Disengage, Hide) | Cunning Action (Dash, Disengage, Hide) |
| **3** | Subclass Selection, Sneak Attack (2d6) | Subclass Selection, Sneak Attack (2d6) |
| **4** | Feat / Ability Score Improvement | Feat / Ability Score Improvement |
| **5** | Uncanny Dodge, Sneak Attack (3d6) | Uncanny Dodge, Sneak Attack (3d6)<br>**Cunning Strike** (*Trip*, *Withdraw*, *Poison*) |
| **6** | Expertise | Expertise |
| **7** | Evasion, Sneak Attack (4d6) | Evasion, Sneak Attack (4d6)<br>**Reliable Talent** (Shifted from L11 to L7) |
| **8** | Feat / Ability Score Improvement | Feat / Ability Score Improvement |
| **9** | Subclass Feature, Sneak Attack (5d6) | Subclass Feature, Sneak Attack (5d6) |
| **10** | Feat / Ability Score Improvement | Feat / Ability Score Improvement |
| **11** | Reliable Talent, Sneak Attack (6d6) | **Improved Cunning Strike** (*Daze*), Sneak Attack (6d6) |
| **12** | Feat / Ability Score Improvement | Feat / Ability Score Improvement |
| **13** | *(ULC)* Sneak Attack (7d6) | *(ULC)* Subclass Feature, Sneak Attack (7d6) |
| **14** | *(ULC)* Blindsense | *(ULC)* Blindsense |
| **15** | *(ULC)* Slippery Mind (WIS Save Prof), Sneak Attack (8d6) | *(ULC)* Slippery Mind (WIS Save Prof), Sneak Attack (8d6) |
| **16** | *(ULC)* Feat / Ability Score Improvement | *(ULC)* Feat / Ability Score Improvement |
| **17** | *(ULC)* Sneak Attack (9d6) | *(ULC)* Subclass Feature, Sneak Attack (9d6) |
| **18** | *(ULC)* Elusive | *(ULC)* Elusive (Fixed: Attacks against you cannot have advantage or score crits) |
| **19** | *(ULC)* Feat, Sneak Attack (10d6) | *(ULC)* Feat, Sneak Attack (10d6) |
| **20** | *(ULC)* Stroke of Luck | *(ULC)* Stroke of Luck |

---

### Arcane Trickster Subclass Progression (Levels 1–20)

| Level | Vanilla BG3 | Shadow's Call (2024 Modernized) |
| :---: | :--- | :--- |
| **3** | Spellcasting (Enchantment/Illusion locked)<br>Mage Hand Legerdemain (10 turns, Short Rest) | **Unbound Arcane Spellbook** (Full Wizard spell list access)<br>**Mage Hand Legerdemain Mastery** (Permanent, invisible, Arcane Distraction Aura) |
| **9** | Magical Ambush | **Magical Ambush Enhanced** (Disadvantage on target saves from stealth/invisibility) |
| **13** | *(ULC)* Standard 3rd/4th level spell slots | **Versatile Trickster** (Channel Cunning Strike Trip/Daze through Mage Hand as Bonus Action) |
| **17** | *(ULC)* Standard 4th level spell slots | **Spell Thief** (Negate targeted spell as Reaction and gain a free cast) |

---

### Assassin Subclass Progression (Levels 1–20)

| Level | Vanilla BG3 | Shadow's Call (2024 Modernized) |
| :---: | :--- | :--- |
| **3** | Assassinate: Ambush (Crit on surprised)<br>Assassinate: Initiative (Advantage)<br>Assassin's Alacrity | **Assassinate (2024 Modernized)**<br>• Combat Readiness (+2 Initiative)<br>• Opening Gambit (Advantage vs un-acted targets)<br>• **Executioner's Strike** (Round 1: +Rogue Level flat damage; crits on surprise)<br>• Assassin's Alacrity (Action & Bonus Action refresh) |
| **9** | Infiltration Expertise (Disguise Self) | **Shadow Dance** (Kill or Crit triggers 1-turn Invisibility & Reaction reset)<br>**Penetrating Toxins** (Bypasses Poison Resistance, treats Immunity as Resistance) |
| **13** | *(ULC)* Stat growth | **Envenomed Strike** (Cunning Strike Poison inflicts additional +2d6 Necrotic damage) |
| **17** | *(ULC)* Stat growth | **Death Strike** (Surprise/Stealth Round 1 attack forces CON save or doubles total damage) |

---

## Dependencies

- **Required:** Baldur's Gate 3 base game module `GustavDev` (`28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8`).
- **Progression Mod:** `UnlockLevelCurve - Level 13-20 | Patch 8` (`a2ffd0e4-c407-8642-2611-c934ea0b0a77`). Load UnlockLevelCurve before Shadow's Call.

## Compatibility

- **Game version:** Baldur's Gate 3 (Patch 7 / Patch 8).
- **Save compatibility:** Safe to install on existing saves or new playthroughs. Respec via Withers immediately updates progression nodes and spell lists.
- **Load Order:** Place below `UnlockLevelCurve` in your load order. Compatible with major UI, animation, and equipment mods.

---

## Toolkit Instructions & Developer Verification

To inspect, compile, or build Shadow's Call using the Baldur's Gate 3 Toolkit (`Glasses.exe`) or project CLI tools:

1. **Static Validation & Node Integrity:**
   Run the automated schema and handle validator:
   ```bash
   python3 scripts/validate_mod.py --mod shadows-call --json
   ```

2. **Localization Sync & Compilation:**
   Verify and compile localization text handles into binary `.loca` format:
   ```bash
   python3 scripts/sync_localization.py --mod shadows-call --check --json
   python3 scripts/sync_localization.py --mod shadows-call
   ```

3. **Toolkit Runtime Diagnostics:**
   Open project `ShadowsCall_c570bfb5-705c-45a3-8424-e90ce90d23d7` in the official Toolkit. Analyze any generated engine warnings or asset messages:
   ```bash
   python3 scripts/diagnose_toolkit_logs.py --mod shadows-call
   ```

4. **Local Deployment & Testing:**
   Package the mod into a deployment-ready `.pak` archive:
   ```bash
   python3 scripts/pack_mod_pak.py --mod shadows-call --publish-local
   ```

---

## Additional Credits

- Designed and authored by MTGHillGiant following the D&D 2024 Player's Handbook (5.5e).
- Built with the Baldur's Gate 3 Toolkit and compatible with UnlockLevelCurve by Charis.
