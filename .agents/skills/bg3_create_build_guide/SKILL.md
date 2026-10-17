---
name: bg3_create_build_guide
description: Generates high-end Level 20 Baldur's Gate 3 build guides with Best-in-Slot (BiS) modded gear, Level 1–20 progression tables, and Turn 1 combat sequences based on the workspace templates. Triggers on /bg3_create_build_guide or requests to create a BG3 build guide.
---

# BG3 Level 20 Build Guide Creator

This skill guides the creation of comprehensive Level 20 *Baldur's Gate 3* build guides following the established format and quality standards in [`build_guides/party__eldritch_blaster/`](file:///home/jpstroud/projects/BaldursGate3/build_guides/party__eldritch_blaster).

Guides generated with this skill combine **Level 20 multiclass progression** (`UnlockLevelCurve`), **Best-in-Slot (BiS) gear analysis** utilizing any mod documentation found in [`mods/`](file:///home/jpstroud/projects/BaldursGate3/mods), optimized feat selection (`Choose Your Stats`), and tactical Turn 1 combat rotations.

---

## Workflow Overview

When invoked via `/bg3_create_build_guide` or when asked to create a build guide:

1. **Gather Build Parameters**: Inspect the user's prompt or ask for missing details (classes, subclass split, primary combat role, theme).
2. **Scan Mod Documentation**: Inspect [`mods/`](file:///home/jpstroud/projects/BaldursGate3/mods) for mod catalogues, readmes, and item/spell sheets.
3. **Classify Build Role**: Determine whether the build is **Caster**, **Hybrid**, or **Pure Melee**.
4. **Generate Guide Sections**: Produce all 5 standardized sections following the reference template.
5. **Save Build Guide**: Write the finished markdown file into [`build_guides/<category>/build_guide_<classes>.md`](file:///home/jpstroud/projects/BaldursGate3/build_guides).

---

## Step 1: Gathering Build Parameters & Classification

If the user invoked `/bg3_create_build_guide` with a full description (e.g., `/bg3_create_build_guide Warlock 2 / Fighter 2 / Sorcerer 16 aerial blaster`), extract the details directly. If details are missing, clarify:
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
   - Inspect [`mods/`](file:///home/jpstroud/projects/BaldursGate3/mods) for markdown (`.md`), text (`.txt`), or documentation files detailing mod equipment, spells, and set bonuses (e.g., *Sets of Faerun*, custom weapons, armor, rings).
2. **Hybrid BiS Selection Principle**:
   - **Prioritize Modded Items**: If documentation in [`mods/`](file:///home/jpstroud/projects/BaldursGate3/mods) describes items, sets, or passives that elevate the build (such as *Sets of Faerun* Thalindra Set, custom weapons, or specialized gear), place them in the BiS table.
   - **Vanilla Fallbacks**: Where no superior mod item exists or [`mods/`](file:///home/jpstroud/projects/BaldursGate3/mods) is empty, populate slots with top-tier vanilla BG3 endgame gear (e.g., *Helm of Balduran*, *Armour of Persistence*, *Helldusk Boots*, *Viconia's Walking Fortress*, *Amulet of Greater Health*, *Phalar Aluve*, *Rhapsody*, *Markoheshkir*).
   - In the **Mod / Vanilla Source** column, explicitly state whether each item is from a specific mod (e.g., `*Sets of Faerun*`, `*UnlockLevelCurve*`) or vanilla (e.g., `*Vanilla (House of Hope)*`, `*Vanilla (Act 3 Dammon)*`).
3. **Simulate Build Synergies & Turn 1 DPR**:
   - Run [`scripts/theorycrafting/simulate_build_synergy.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/theorycrafting/simulate_build_synergy.py) to calculate exact Turn 1 DPR, Spell Save DC ceilings, and spell slot matrices:
     ```bash
     bg3 build simulate \
       --classes "<Class=Level,...>" \
       --stats "<Str=N,Dex=N,Con=N,Int=N,Wis=N,Cha=N>" \
       --gear "<Item1,Item2,...>" \
       --dpr-sequence <melee_burst|eldritch_blast> \
       --json
     ```
   - Use the simulated metrics to populate Section 5 (Turn 1 Combat Sequence) with verified damage numbers.

> [!TIP]
> **Tool Discovery & Schema Inspection**:
> To inspect simulator parameters or discover gear search tools, query the studio registry:
> ```bash
> bg3 tools info simulate-build --json
> bg3 tools search "gear database" --json
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
**MANDATORY RULE**: Strictly omit the `Cantrips Gained` and `Vanilla Spells Learned / Prepared` columns. Use:
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

Every generated guide must adhere strictly to the following 5-section schema:

```markdown
# Build Guide: [Build Title / Name]
### [Class 1] [Level] / [Class 2] [Level] ...
**Platform**: Xbox Series S & PC | **Max Level**: 20 (*UnlockLevelCurve*) | **Role**: [Role Description]

---

## 1. Build Archetype & Concept

[2-3 paragraphs explaining the core concept, mechanics, and party role]

* **[Key Synergy 1]**: [Description]
* **[Key Synergy 2]**: [Description]
* **[Key Synergy 3]**: [Description]
* **Zero Gear Contention with Party**: [Explanation of gear compatibility]

### Required Mods (Xbox Series S Verified)
1. **`UnlockLevelCurve - Level 13-20`** (mod.io ID: `4166963`) — Unlocks progression to Level 20.
2. **`Sets of Faerun`** (mod.io ID: `4467214`) — [If mod items are equipped].
3. **`Choose Your Stats`** (slug: `chooseyourstats_modio`) — Used to set starting ability scores, freeing all Feat slots from ASIs.
4. **`Fade's Camp Chest`** (mod.io ID: `4838986`) — Spawns gear bags cleanly at camp.
[Include any additional mods referenced from /mods]

---

## 2. Character Creation & Starting Stats

### Optimal Starting Class
* **[Class Name (Level 1)]**: **MANDATORY starting class**. [Rationale: saving throws, proficiencies, armor/shields].

### Optimal Starting Race
1. **[Top Race]**: [Racial traits and rationale].
2. **[Second Race]**: [Racial traits and rationale].
3. **[Third Race]**: [Racial traits and rationale].

### Starting Ability Scores
If setting stats with **Choose Your Stats**:
* **[Primary Stat]**: 20 (scales with gear/Mirror of Loss)
* **[Secondary Stat]**: 16
* **[Tertiary Stat]**: 16
* **[Other Stats]**: ...

*Point Buy Default (if not using stat editor)*:
* STR: [x] | DEX: [x] | CON: [x] | INT: [x] | WIS: [x] | CHA: [x]

---

## 3. Best-in-Slot (BiS) Gear Loadout

[Introductory paragraph explaining gear synergy, set bonuses, or defense ratings]

| Equipment Slot | Item Name | Mod / Vanilla Source | Key Passives & Stats | Role in Build |
| :--- | :--- | :--- | :--- | :--- |
| **Main Hand** | ... | ... | ... | ... |
| **Off Hand** | ... | ... | ... | ... |
| **Chest** | ... | ... | ... | ... |
| **Head** | ... | ... | ... | ... |
| **Cloak** | ... | ... | ... | ... |
| **Gloves** | ... | ... | ... | ... |
| **Boots** | ... | ... | ... | ... |
| **Amulet** | ... | ... | ... | ... |
| **Ring 1** | ... | ... | ... | ... |
| **Ring 2** | ... | ... | ... | ... |
| **[Set Bonus / Extra Slot]** | ... | ... | ... | ... |

---

## 4. Level 1–20 Progression Table (Vanilla BG3 Spells)

[Note explaining spell rules, upcasting, and feat choices]

[Insert the 5-column table for Caster/Hybrid or 4-column table for Pure Melee as defined in Step 4]

---

## 5. Turn 1 Combat Sequence Example

### Setup Before Combat
1. [Pre-buffs, stances, elixir/weapon coat recommendations].
2. [Positioning notes].

### Round 1 Execution: [Sequence Name]

```
[COMBAT INITIATIVE]
[Initiative breakdown and positioning]

Step 1: Standard Action
- [Action taken, spells/attacks, modifiers, synergies]

Step 2: Bonus Action
- [Bonus action taken, mobility, quickened spells, or buffs]

Step 3: Extra Actions / Reactions (Action Surge, Fast Hands, etc.)
- [Additional steps]

[ROUND 1 RESULT]:
- [Summary of damage, status effects, party buffs, and defensive state]
```

[Follow-up turns / rotation notes]
```

---

## Step 6: Artifact-First Output & Streaming Delivery

To minimize chat context bloat and avoid excessive token usage, build guides must follow the **Artifact-First** delivery pattern:

1. **Write Complete Guide to File First**:
   - Determine target file path:
     - If a party or category is specified: [`build_guides/<party_name>/build_guide_<classes>.md`](file:///home/jpstroud/projects/BaldursGate3/build_guides).
     - Otherwise: [`build_guides/build_guide_<classes>.md`](file:///home/jpstroud/projects/BaldursGate3/build_guides).
   - Format the filename using lowercase class names and level counts (e.g., `build_guide_sorcerer16_fighter2_warlock2.md` or `build_guide_barbarian12_fighter8.md`).
   - Ensure parent directories are created automatically if they do not exist.
   - Use `write_to_file` to save the complete document containing all 5 core sections (Core Concept, Progression Split & Stats, Complete BiS Gear Loadout, Full 1–20 Progression Table, and Turn 1 Combat Sequence).

2. **Present Executive Summary in Chat**:
   - **DO NOT** dump the full 20-level progression table or exhaustive item descriptions into the chat response.
   - Instead, stream a concise **Executive Summary**:
     - **Build Link**: Provide a direct link to the saved guide file, e.g., [`build_guide_<classes>.md`](file:///home/jpstroud/projects/BaldursGate3/build_guides/...).
     - **Class Split & Core Synergies**: Summary of the mechanical concept in 2–3 sentences.
     - **BiS Gear Highlights**: Condensed table or bullet list of 3–4 linchpin equipment pieces.
     - **Turn 1 Combat Rotation**: The setup and Round 1 action sequence with expected DPR / crowd control impact.
     - Clear direction to inspect the markdown file for the full level-by-level choices.
