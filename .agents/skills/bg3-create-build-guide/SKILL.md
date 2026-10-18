---
name: bg3-create-build-guide
description: Generates high-end Level 20 Baldur's Gate 3 build guides with Best-in-Slot (BiS) modded gear, Level 1–20 progression tables, and Turn 1 combat sequences based on the workspace templates. Triggers on /bg3-create-build-guide, /build_guide, or requests to create a BG3 build guide.
---

# BG3 Level 20 Build Guide Creator (`bg3-create-build-guide`)

This skill guides the creation of comprehensive Level 20 *Baldur's Gate 3* build guides following the established format and quality standards in [`build_guides/party_eldritch_blaster/`](../../../build_guides/party_eldritch_blaster).

Guides generated with this skill combine **Level 20 multiclass progression** (`UnlockLevelCurve`), **Best-in-Slot (BiS) gear analysis** utilizing mod documentation found in [`mods/`](../../../mods), optimized feat selection (`Choose Your Stats`), and tactical Turn 1 combat rotations.

---

## Workflow Overview

When invoked via `/bg3-create-build-guide` or when asked to create a build guide:

1. **Gather Build Parameters**: Inspect the user's prompt or ask for missing details (classes, subclass split, primary combat role, theme).
2. **Scan Mod Documentation**: Inspect [`mods/`](../../../mods) for mod catalogues, readmes, and item/spell sheets.
3. **Classify Build Role**: Determine whether the build is **Caster**, **Hybrid**, or **Pure Melee**.
4. **Generate Guide Sections**: Produce all 5 standardized sections following the [Build Guide Template](./resources/build_guide_template.md).
5. **Save Build Guide**: Write the finished markdown file into [`build_guides/`](../../../build_guides) (e.g. `build_guides/<category>/build_guide_<classes>.md`).

---

## Step 1: Gathering Build Parameters & Classification

If the user invoked `/bg3-create-build-guide` with a full description (e.g., `/bg3-create-build-guide Warlock 2 / Fighter 2 / Sorcerer 16 aerial blaster`), extract the details directly. If details are missing, clarify:
- **Class Breakdown**: Levels per class totaling exactly 20 (e.g., 12 Paladin / 8 Fighter).
- **Subclasses & Starting Class**: Mandatory starting class (for optimal saving throws, e.g., Fighter for CON saves, Paladin for WIS/CHA saves).
- **Role & Party Synergies**: Main carry, burst nuker, frontline tank, aura support, summoner, control.
- **Archetype Classification**:
  - **Caster**: Full spellcaster progression (e.g., Sorcerer, Wizard, Cleric, Druid, Warlock, Lore Bard).
  - **Hybrid**: Martial + spellcasting combination (e.g., Paladin, Eldritch Knight, Arcane Trickster, Ranger, Swords/Valour Bard, Gish multiclasses).
  - **Pure Melee**: Zero spellcasting / cantrips (e.g., Fighter Battle Master/Champion, Barbarian, Rogue Thief/Assassin, Monk Open Hand).

---

## Step 2: Mod Inspection & BiS Gear Selection

1. **Check Workspace Mods**:
   - Inspect [`mods/`](../../../mods) for markdown (`.md`), text (`.txt`), or documentation files detailing mod equipment, spells, and set bonuses (e.g., *Sets of Faerun*, custom weapons, armor, rings).
2. **Hybrid BiS Selection Principle**:
   - **Prioritize Modded Items**: If documentation in [`mods/`](../../../mods) describes items, sets, or passives that elevate the build (such as *Sets of Faerun* Thalindra Set, custom weapons, or specialized gear), place them in the BiS table.
   - **Vanilla Fallbacks**: Where no superior mod item exists or [`mods/`](../../../mods) is empty, populate slots with top-tier vanilla BG3 endgame gear (e.g., *Helm of Balduran*, *Armour of Persistence*, *Helldusk Boots*, *Viconia's Walking Fortress*, *Amulet of Greater Health*, *Phalar Aluve*, *Rhapsody*, *Markoheshkir*).
   - In the **Mod / Vanilla Source** column, explicitly state whether each item is from a specific mod (e.g., `*Sets of Faerun*`, `*UnlockLevelCurve*`) or vanilla (e.g., `*Vanilla (House of Hope)*`, `*Vanilla (Act 3 Dammon)*`).
3. **Simulate Build Synergies & Turn 1 DPR**:
   - Run `python3 scripts/theorycrafting/simulate_build_synergy.py` to calculate exact Turn 1 DPR, Spell Save DC ceilings, and spell slot matrices:
     ```bash
     python3 scripts/bg3.py build simulate \
       --classes "<Class=Level,...>" \
       --stats "<Str=N,Dex=N,Con=N,Int=N,Wis=N,Cha=N>" \
       --gear "<Item1,Item2,...>" \
       --dpr-sequence <melee_burst|eldritch_blast> \
       --json
     ```
   - Use the simulated metrics to populate Section 5 (Turn 1 Combat Sequence) with verified damage numbers.

> [!TIP]
> **Tool Discovery & Schema Inspection (bg3 tools)**:
> To inspect simulator parameters or discover gear search tools, query the studio registry:
> ```bash
> python3 scripts/bg3.py tools info simulate-build --json
> python3 scripts/bg3.py tools search "gear database" --json
> ```

---

## Step 3: Feat Strategy & Stat Conventions

As established in the reference guides:
1. **Ability Scores**:
   - Primary recommendations assume the **`Choose Your Stats`** mod is used to set initial ability scores (e.g., primary stat 20), freeing all Feat slots from ASIs to take top-tier combat, mobility, and survivability passives.
   - Always also include a **Point Buy Default** fallback for unmodded stat progression.
2. **Feat Selection**:
   - Maximize high-impact passives: **Alert** (guarantees acting first), **War Caster** (Advantage on concentration saves), **Spell Sniper** (crit range reduction), **Savage Attacker** (rerolls melee damage), **Sentinel** (frontline lockdown), **Dual Wielder**, **Resilient (Wisdom)** (+save modifier against control spells).
   - Standard 5e feat progression at class levels 4, 8, 12, 16, 19 (plus Fighter 6 & 14, Rogue 10).

---

## Step 4: Level 1–20 Progression Table Rules

Construct a 20-row table detailing choices at each level from 1 to 20:

### For Caster & Hybrid Builds (5 Columns)
Include both cantrips and spells:
```markdown
| Total Level | Class & Level | Cantrips Gained | Vanilla Spells Learned / Prepared | Feats & Key Features |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Fighter 1** | — | — | **Fighting Style**: Defense (+1 AC); Second Wind; **CON Save Proficiency** |
...
```
*(Use `—` in cantrip or spell cells if none are gained at that specific level).*

### For Pure Melee Builds (4 Columns)
**MANDATORY RULE**: Strictly omit the `Cantrips Gained` and `Vanilla Spells Learned / Prepared` columns:
```markdown
| Total Level | Class & Level | Class Features & Maneuvers | Feats & Key Features |
| :---: | :--- | :--- | :--- |
| **1** | **Fighter 1** | Fighting Style: Great Weapon Fighting; Second Wind | **STR & CON Save Proficiency**; All Armor & Weapons |
...
```

### Level 13–20 Mechanics (`UnlockLevelCurve`)
- Levels 13–20 unlock 7th and 8th level spell slots for full casters (used for 7th/8th level upcasts or mod spells).
- Cantrips naturally scale to 4 damage dice / beams at Level 17.
- Mention subclass capstones or extended class benefits where appropriate.

---

## Step 5: Document Structure & Formatting Template

Every generated guide must adhere strictly to the standardized 5-section schema defined in the modular resource:

📄 **[Level 20 Build Guide Template](./resources/build_guide_template.md)**

The template enforces:
- **Section 1**: Build Archetype, Concept, Synergies & Required Mods
- **Section 2**: Character Creation, Starting Class, Race & Starting Ability Scores
- **Section 3**: Best-in-Slot (BiS) Equipment Loadout table
- **Section 4**: Full Level 1–20 Progression Table
- **Section 5**: Turn 1 Tactical Combat Rotation with damage calculations

---

## Step 6: Artifact-First Output & Streaming Delivery

To minimize chat context bloat and avoid excessive token usage, build guides must follow the **Artifact-First** delivery pattern:

1. **Write Complete Guide to File First**:
   - Determine target file path:
     - If a party or category is specified: `build_guides/<party_name>/build_guide_<classes>.md` (under [`build_guides/`](../../../build_guides)).
     - Otherwise: `build_guides/build_guide_<classes>.md`.
   - Format the filename using lowercase class names and level counts (e.g., `build_guide_sorcerer16_fighter2_warlock2.md` or `build_guide_barbarian12_fighter8.md`).
   - Ensure parent directories are created automatically if they do not exist.
   - Use `write_to_file` to save the complete document containing all 5 core sections.

2. **Verify Generated Guide**:
   - Confirm all 20 levels are accounted for in the progression table.
   - Verify all referenced equipment slots are populated.
   - Ensure literal dollar signs are escaped as `\$` if present.

3. **Present Executive Summary in Chat**:
   - **DO NOT** dump the full 20-level progression table or exhaustive item descriptions into the chat response.
   - Instead, stream a concise **Executive Summary**:
     - **Build Link**: Provide a direct relative link to the saved guide file.
     - **Class Split & Core Synergies**: Summary of the mechanical concept in 2–3 sentences.
     - **BiS Gear Highlights**: Condensed table or bullet list of 3–4 linchpin equipment pieces.
     - **Turn 1 Combat Rotation**: The setup and Round 1 action sequence with expected DPR / crowd control impact.
     - Clear direction to inspect the markdown file for the full level-by-level choices.
