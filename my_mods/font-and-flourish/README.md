# Font & Flourish (FontAndFlourish)
**Module UUID**: `8fd36b9b-2e80-4175-828c-b89095ae0b4e`  
**Mod Slug**: `font-and-flourish`  
**Larian Folder**: `FontAndFlourish_8fd36b9b-2e80-4175-828c-b89095ae0b4e`  
**Author**: `MTGHillGiant`  
**Toolkit Target**: Patch 7 / Patch 8 Native Toolkit Drag-and-Drop Structure

---

## Overview
**Font & Flourish** overhauls the Baldur's Gate 3 **College of Swords Bard** and core **Bardic Inspiration** mechanics to address the subclass's two biggest melee limitations:
1. **Severe Inspiration Drought**: Restores the resource conversion introduced in the **D&D 2024 Player's Handbook**, allowing Bards to expend spell slots as a **Free Action** to replenish Bardic Inspiration charges, featuring upcast scaling for higher-level spell slots.
2. **Clunky Melee Slashing Flourish**: Completely replaces the awkward, friendly-fire-prone 2-meter cone with a precision **Target-Selected Multi-Attack**. Just like Ranged Slashing Flourish, you can now designate two separate melee enemies or strike the **exact same enemy twice**, completely eliminating friendly fire on allies and summons.

---

## Features & Mechanics Breakdown

### 1. 2024 Font of Inspiration (Spell Slot Conversion)
* **Granted At**: Level 5 via the core `FontOfInspiration` feature.
* **Action Cost**: **Free Action** (Consumes 0 Action Points, 0 Bonus Action Points). Can be used anytime during your turn in combat or outside combat.
* **Spell Type**: Shout (`Shout_FontOfInspiration`).
* **Upcast Scaling**:
  | Spell Slot Level | Bardic Inspiration Restored |
  | :--- | :--- |
  | **1st Level** | **+1** Charge |
  | **2nd Level** | **+2** Charges |
  | **3rd Level** | **+3** Charges |
  | **4th Level** | **+4** Charges |
  | **5th Level** | **+5** Charges (Full Refill) |
  | **6th Level** | **+5** Charges (Full Refill) |

### 2. Precision Melee Slashing Flourish
* **Granted At**: Level 3 upon selecting **College of Swords**.
* **Spell Type**: Target (`Target_BladeFlourish_Slashing`).
* **Target Count**: **2 Targets** within melee range (`MeleeRange`).
* **Targeting Rules**:
  * Can strike two distinct melee targets within reach.
  * Can strike the **same target twice** for devastating single-target burst, mirroring Ranged Slashing Flourish.
  * Explicit cursor selection prevents any accidental collateral hits on allies, neutral NPCs, or party summons.
* **Resource Cost**: 1 Action Point + 1 Bardic Inspiration charge (consumed only on hit).
* **Legacy Zone Flourish Safety Patch**: Legacy cone flourish (`Zone_BladeFlourish_Slashing`) is also safely patched with `Enemy()` filter and an expanded 3.0m/120° cone to safeguard existing save files.

---

## Dependencies & Compatibility
* **Dependencies**: `GustavDev` (vanilla base game).
* **Progression Mods**: 100% compatible with `UnlockLevelCurve` and custom class mods. `FontOfInspiration` is patched cleanly via passive boosting rather than fragile class progression node overwrites.
* **Save Game Compatibility**: Safe to install on existing saves or new games.

---

## Installation & Toolkit Import

### Automatic Sync (Recommended)
```bash
python3 scripts/sync_to_game_data.py --mods FontAndFlourish_8fd36b9b-2e80-4175-828c-b89095ae0b4e
```

### Manual Toolkit Workspace Import
1. Copy `Projects/`, `Mods/`, `Public/`, and `Localization/` from this mod folder directly into your game's `Data/` folder.
2. Launch the **Baldur's Gate 3 Toolkit**.
3. Select **File -> Open Project...** and choose **FontAndFlourish**.
4. Save and Publish to local profile or mod.io!
