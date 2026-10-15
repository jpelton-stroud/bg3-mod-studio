# Font & Flourish

- **Mod slug:** `font-and-flourish`
- **Module UUID:** `8fd36b9b-2e80-4175-828c-b89095ae0b4e`
- **Larian folder:** `FontAndFlourish_8fd36b9b-2e80-4175-828c-b89095ae0b4e`
- **Version:** `1.0.0.1`
- **Author:** MTGHillGiant

## Overview

Font & Flourish overhauls the Baldur's Gate 3 College of Swords Bard and core Bardic Inspiration mechanics. It restores spell-slot conversion for Bardic Inspiration and replaces the melee Slashing Flourish cone with a precise, target-selected multi-attack.

## Features

### 2024 Font of Inspiration (Spell Slot Conversion)

- **Granted at:** Level 5 via the core `FontOfInspiration` feature.
- **Action cost:** Free Action (0 Action Points and 0 Bonus Action Points); usable during or outside combat.
- **Spell type:** Shout (`Shout_FontOfInspiration`).
- **Upcast scaling:**

  | Spell Slot Level | Bardic Inspiration Restored |
  | :--- | :--- |
  | **1st Level** | **+1** Charge |
  | **2nd Level** | **+2** Charges |
  | **3rd Level** | **+3** Charges |
  | **4th Level** | **+4** Charges |
  | **5th Level** | **+5** Charges (Full Refill) |
  | **6th Level** | **+5** Charges (Full Refill) |

### Precision Melee Slashing Flourish

- **Granted at:** Level 3 upon selecting College of Swords.
- **Spell type:** Target (`Target_BladeFlourish_Slashing`).
- **Target count:** 2 targets within melee range (`MeleeRange`).
- **Targeting rules:** Can strike two distinct melee targets or the same target twice. Explicit cursor selection prevents accidental hits on allies, neutral NPCs, or party summons.
- **Resource cost:** 1 Action Point + 1 Bardic Inspiration charge (consumed only on hit).
- **Legacy zone safety:** The legacy cone flourish (`Zone_BladeFlourish_Slashing`) is also patched with an `Enemy()` filter and an expanded 3.0m/120° cone to safeguard existing save files.

## Dependencies

- **Required:** Baldur's Gate 3 base game module `GustavX`.
- **Progression mods:** The mod documentation states compatibility with UnlockLevelCurve and custom class mods; `FontOfInspiration` is patched through passive boosting rather than class progression node overwrites.

## Compatibility

- **Game version:** Baldur's Gate 3; authored for the Patch 7 / Patch 8 Native Toolkit.
- **Known conflicts:** None documented.
- **Save compatibility:** Documented as safe to install on existing saves or new games.

## Additional Credits

None listed.
