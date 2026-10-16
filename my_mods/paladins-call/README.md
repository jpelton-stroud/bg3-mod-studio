# Paladin's Call

- **Mod slug:** `paladins-call`
- **Module UUID:** `7f92e4b1-82d3-4a16-9cf8-61d5302e1a90`
- **Larian folder:** `PaladinsCall_7f92e4b1-82d3-4a16-9cf8-61d5302e1a90`
- **Version:** `1.0.0.0`
- **Author:** MTGHillGiant

## Overview

Paladin's Call modernizes the Paladin class in Baldur's Gate 3 by addressing turn economy congestion, mobility limitations, smite resource starvation, and damage scaling. Built natively for Patch 8 and fully compatible with UnlockLevelCurve up to Level 20.

## Features

### Mobility & Tactical Movement

- **Universal Misty Step:** Adds `Target_MistyStep` to the base Paladin 2nd-level spell list (`c1c19892-6f18-40eb-a02b-af8fb251f8b5`). All Paladins, including Oath of Devotion and Oathbreaker, can prepare and cast _Misty Step_ at Level 5.

### Modern Action Economy (D&D 2024 Standards)

- **Sacred Weapon (Oath of Devotion):** Changed from an Action to a Bonus Action (`BonusActionPoint:1;ChannelOath:1`).
- **Nature's Wrath (Oath of the Ancients):** Changed to a Bonus Action with an expanded tactical range (18m).
- **Lay on Hands (all variants):** Converted to a Bonus Action (`Target_LayOnHands`, `SmallHeal`, `BigHeal`, and `Cure`). Heal allies, remove diseases or poisons, or revive downed companions while maintaining offensive momentum.

### Sustained Smite Economy: Divine Abundance (Crit Refund)

- **Free spell slot on critical hits:** Granted at Level 1 (`PaladinsCall_DivineAbundance_CritRefund`). Whenever you score a Critical Hit with a melee weapon, instantly recover an expended 1st-level spell slot.

### Progressive Radiant Weapon Scaling (Elevated Floor)

Melee strikes scale in Radiant damage, improving at-will damage while saving spell slots:

- **Level 5:** +1d6 Radiant damage (_Righteous Strikes Rank 1_).
- **Level 8:** +1d8 Radiant damage (_Righteous Strikes Rank 2_).
- **Level 11:** +1d10 Radiant damage (_Improved Divine Smite_).
- **Level 15:** +1d10 + Charisma Modifier Radiant damage (_Righteous Strikes: Exalted_).
- **Level 20:** +1d12 + Charisma Modifier Radiant damage (_Righteous Strikes: Apex_).

### Expanded Spell Slot Progression (Option A) & Level 20 ULC Synergy

- **Levels 1–12:** Adds one slot at Levels 4, 7, and 10, and introduces 4th-level slots at Levels 11 and 12:
  - **Level 4:** 4 / 0 / 0 / 0
  - **Level 7:** 4 / 4 / 0 / 0
  - **Level 10:** 4 / 4 / 3 / 0
  - **Level 11:** 4 / 4 / 3 / 1
  - **Level 12:** 4 / 4 / 3 / 2
- **Levels 13–20 with UnlockLevelCurve:** Automatically and additively stacks with UnlockLevelCurve's progression nodes:
  - **Level 13:** 4 / 4 / 3 / 3 / 0
  - **Level 15:** 4 / 4 / 3 / 4 / 0 (unlocks +1d10 + CHA Radiant strikes)
  - **Level 17:** 4 / 4 / 3 / 5 / 1
  - **Level 19:** 4 / 4 / 3 / 5 / 2
  - **Level 20:** 4 / 4 / 3 / 5 / 2 (18 slots total; unlocks +1d12 + CHA Radiant strikes)

## Dependencies

- **Required:** Baldur's Gate 3 base game module `GustavX`.
- **Progression mod:** UnlockLevelCurve is required for the Level 13–20 progression synergy; load it before Paladin's Call.

## Compatibility

- **Game version:** Baldur's Gate 3 (Patch 8).
- **Known conflicts:** None documented.

## Additional Credits

None listed.
