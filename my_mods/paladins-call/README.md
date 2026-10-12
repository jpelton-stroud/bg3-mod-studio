# Paladin's Call (Patch 8)
**Mod Name**: `PaladinUnbound`
**Module UUID**: `7f92e4b1-82d3-4a16-9cf8-61d5302e1a90`
**Folder Name**: `PaladinsCall_7f92e4b1-82d3-4a16-9cf8-61d5302e1a90`
**Target Game Version**: Baldur's Gate 3 (Patch 8)

---

## Overview

**Paladin's Call** modernizes the Paladin class in Baldur's Gate 3 by addressing turn economy congestion, mobility limitations, smite resource starvation, and damage scaling. Built natively for Patch 8 and fully compatible with `UnlockLevelCurve` up to Level 20.

---

## Features

### 1. Mobility & Tactical Movement
* **Universal Misty Step**: Added `Teleportation_MistyStep` to the base Paladin 2nd-level spell list (`c1c19892-6f18-40eb-a02b-af8fb251f8b5`). All Paladins—including Oath of Devotion and Oathbreaker—can prepare and cast *Misty Step* at Level 5.

### 2. Modern Action Economy (D&D 2024 Standards)
* **Sacred Weapon (Oath of Devotion)**: Changed from an Action to a **Bonus Action** (`BonusActionPoint:1;ChannelOath:1`). Imbue your weapon with holy light on Turn 1 and immediately execute your attacks!
* **Nature's Wrath (Oath of the Ancients)**: Changed to a **Bonus Action** with an expanded tactical range (18m). Restrain enemies from afar without forfeiting your attack action.
* **Lay on Hands (All Variants)**: Converted to a **Bonus Action** (`Target_LayOnHands`, `LesserHealing`, `GreaterHealing`, and `Cure`). Heal allies, remove diseases/poisons, or pick up downed companions on the frontline while maintaining your offensive momentum.

### 3. Sustained Smite Economy: Divine Abundance (Crit Refund)
* **Free Spell Slot on Critical Hits**: Granted at Level 1 (`PaladinsCall_DivineAbundance_CritRefund`). Whenever you score a Critical Hit with a melee weapon, holy energy surges through you, **instantly recovering an expended 1st-level spell slot**. Encourages crit-fishing while preserving your spell slot pool across long adventuring days.

### 4. Progressive Radiant Weapon Scaling (Elevated Floor)
Your melee strikes scale in holy damage, eliminating the feeling of having weak at-will damage when saving spell slots:
* **Level 5**: $+1d6$ Radiant damage (*Righteous Strikes Rank 1*)
* **Level 8**: $+1d8$ Radiant damage (*Righteous Strikes Rank 2*)
* **Level 11**: $+1d10$ Radiant damage (*Improved Divine Smite*)
* **Level 15**: $+1d10 + \text{Charisma Modifier}$ Radiant damage (*Righteous Strikes: Exalted*)
* **Level 20**: $+1d12 + \text{Charisma Modifier}$ Radiant damage (*Righteous Strikes: Apex*)

### 5. Expanded Spell Slot Progression (Option A) & Level 20 ULC Synergy
* **Levels 1–12**: Smooths the half-caster curve by adding $+1$ slot at Levels 4, 7, and 10, plus introducing 4th-level slots at Levels 11 and 12:
  * **Level 4**: 4 $\times$ Level 1
  * **Level 7**: 4 $\times$ Level 1, 4 $\times$ Level 2
  * **Level 10**: 4 $\times$ Level 1, 4 $\times$ Level 2, 3 $\times$ Level 3
  * **Level 11**: 4 $\times$ Level 1, 4 $\times$ Level 2, 3 $\times$ Level 3, 1 $\times$ Level 4
  * **Level 12**: 4 $\times$ Level 1, 4 $\times$ Level 2, 3 $\times$ Level 3, 2 $\times$ Level 4
* **Levels 13–20 with `UnlockLevelCurve`**: Automatically and additively stacks with `UnlockLevelCurve`'s progression nodes:
  * **Level 13**: 4 / 4 / 3 / 3 / 0
  * **Level 15**: 4 / 4 / 3 / 4 / 0 (Unlocks $+1d10 + \text{CHA}$ Radiant strikes)
  * **Level 17**: 4 / 4 / 3 / 5 / 1
  * **Level 19**: 4 / 4 / 3 / 5 / 2
  * **Level 20**: **4 / 4 / 3 / 5 / 2** (18 slots total; Unlocks $+1d12 + \text{CHA}$ Radiant strikes)

---

## How to Import into Baldur's Gate 3 Toolkit

This folder contains the complete, pre-configured source structure for the official **Patch 8 Baldur's Gate 3 Toolkit**.

### Method 1: Direct Toolkit Workspace Import (Recommended)
1. Locate your game's **Data** directory (typically `.../Baldurs Gate 3/Data/`).
2. Copy the folders from this directory directly into `Data/`:
   - `Projects/`
   - `Public/`
   - `Localization/`
   - `Mods/`
3. Launch the **Baldur's Gate 3 Toolkit**.
4. Click **File -> Open Project...** and select **PaladinUnbound**.
5. Click **Save** and **Publish Mod**!
