# Eldritch Ascension
**Mod Name**: `PactOfTheBladeUnleashed`
**Module UUID**: `ac007864-dfa8-4b0e-96b3-cc9a173d1c35`
**Folder Name**: `EldritchAscension_ac007864-dfa8-4b0e-96b3-cc9a173d1c35`

---

## How to Import into Baldur's Gate 3 Toolkit

This folder contains the complete, pre-configured source structure for the official **Patch 7 Baldur's Gate 3 Toolkit**.

### Method 1: Direct Toolkit Workspace Import (Recommended)
1. Locate your game's **Data** directory (typically `.../Baldurs Gate 3/Data/`).
2. Copy the folders from this directory directly into `Data/`:
   - `Projects/`
   - `Public/`
   - `Localization/`
3. Launch the **Baldur's Gate 3 Toolkit**.
4. Click **File -> Open Project...** and select **PactOfTheBladeUnleashed**.
5. The Toolkit will automatically load all stats, progressions, and localization strings.
6. Click **Save** and **Publish Mod**!

---

### Method 2: Copying into an Existing Empty Project
If you have already clicked "New Project" in the Toolkit:
1. Open your project folder in `Baldurs Gate 3/Data/Public/<YourProjectFolder>/`.
2. Copy the contents of our `Public/PactOfTheBladeUnleashed_.../` into your project's `Public` folder.
3. Copy `Localization/English/EldritchAscension.xml` into your project's `Localization/English/` folder.
4. Reload/Save in the Toolkit.

---

## Implemented Features
- **Simultaneous Dual-Wield Binding**: `Target_BindPactWeapon` binds both Main Hand and Off-Hand weapons.
- **Pact Weapon Scaling**: +2 Enchantment and scaling Force damage (1d6 at L1, 1d8 at L9, 1d10 at L15, 1d12 at L20).
- **Devouring Blade (3rd & 4th Attacks)**: 3 attacks at Level 12, 4 attacks at Level 20.
- **Eldritch Synergy**: Automatically adds Charisma Modifier to weapon damage rolls (double-Charisma scaling on bound weapons).
- **Eldritch Weaving**: Melee weapon hits unlock *Eldritch Blast* as a Bonus Action for the remainder of your turn.
- **Lifedrinker Overhaul**: Flat Charisma + 1d8 Necrotic damage + vampiric HP healing on hit.
- **Slot-Scaling Hex**: Necrotic damage scales up to 4d6 (1d6 at L1, 2d6 at L5, 3d6 at L11, 4d6 at L17).
