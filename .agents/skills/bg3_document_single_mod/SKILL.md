---
name: bg3_document_single_mod
description: Fetches, unpacks, validates, and documents a single Baldur's Gate 3 mod from mod.io into mods/<mod_name>/README.md using the rich feature schema and static in-game validation. Triggers on /bg3_document_single_mod or when delegated by the bg3_document_mods orchestrator.
---

# BG3 Single Mod Documenter (`bg3_document_single_mod`)

This skill defines the worker procedure for fetching, extracting, validating, and generating specifications for an individual *Baldur's Gate 3* mod from `https://mod.io/g/baldursgate3`.

It can be triggered directly via `/bg3_document_single_mod <mod>` or invoked inside concurrent subagents dispatched by the [`bg3_document_mods`](file:///home/jpstroud/projects/BaldursGate3/.agents/skills/bg3_document_mods/SKILL.md) orchestrator.

---

## Workflow Overview

1. **Intake Mod Query**: Extract mod name, slug, numerical ID, or mod.io URL from the prompt.
2. **Execute Extractor Engine**: Run [`scripts/modio_extract.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/modio_extract.py) to download the `.pak` and decompress Larian LSPK v18 assets into `mods/<slug>/data/`.
3. **Validate In-Game Implementation**: Cross-check extracted definitions to ensure every logged feature is actually implemented in-game (discarding stubs, draft entries, and orphaned assets).
4. **Verify Rich Feature Spec**: Confirm [`mods/<slug>/README.md`](file:///home/jpstroud/projects/BaldursGate3/mods) contains full details on base stats and detailed mechanics for what granted spells/abilities/passives actually do.
5. **Report Status**: Return the standardized success or failure message to the caller/orchestrator.

---

## Step 1: Verification & Environment Check

Before running extraction:
1. Ensure `MODIO_API_KEY` is available in the shell environment:
   ```bash
   . ~/.profile
   ```
   *(The key is also auto-detected from project `.env` if not in active environment).*
2. **Security Rule**: Never print, echo, or log raw API keys in bash commands, chat messages, or spec files.

---

## Step 2: Extraction & Data Unpacking

Execute the extraction engine with the mod query:

```bash
python3 scripts/modio_extract.py --query "<MOD_QUERY>" --write-spec --json
```

The script will:
1. Query the mod.io REST API (`g-6715.modapi.io`) to resolve metadata, category, and download URL.
2. Download the `.zip` or `.pak` archive.
3. Unpack the LSPK v18 archive using pure-Python LZ4 block decompression.
4. Extract raw data files (`.txt` stats, `meta.lsx`, `english.xml`) to [`mods/<mod_slug>/data/`](file:///home/jpstroud/projects/BaldursGate3/mods).
5. Generate an initial spec at [`mods/<mod_slug>/README.md`](file:///home/jpstroud/projects/BaldursGate3/mods).
6. Output structured JSON to stdout summarizing the mod and parsed features.

If the command fails (e.g., mod not found on mod.io or network failure), formulate a clear error message and proceed to **Step 5 (Failure Reporting)**.

> [!TIP]
> **Tool Discovery & Schema Inspection**:
> To inspect extraction flags or discover related cataloging tools:
> ```bash
> python3 scripts/tools.py --info modio-extract --json
> python3 scripts/tools.py --search "extract" --json
> ```

---

## Step 3: In-Game Implementation Validation

Inspect the parsed features in the JSON output and the raw files in `mods/<mod_slug>/data/`:

### Static Implementation Rules
* **Implemented in Game (Include)**:
  - Has a valid, non-empty entry in `Stats/Generated/Data/*.txt` (Weapons, Armor, Spells, Passives).
  - Has resolved or valid display name handles in `english.xml`.
  - Functional stat boosts, damage formulae, or action economy costs.
* **Not Implemented (Exclude/Ignore)**:
  - Entries marked with `IsDummy "1"` or `IsDummy "Yes"`.
  - Placeholder stubs with no stats, empty names, or `// WIP` comments.
  - Abstract base templates (e.g. `_Base_Weapon`) that are never directly equipable or castable and only serve as internal code inheritance anchors.

---

## Step 4: Rich Schema Verification in `mods/<mod_slug>/README.md`

Verify that the generated [`mods/<mod_slug>/README.md`](file:///home/jpstroud/projects/BaldursGate3/mods) adheres to the **Rich Schema Table**:

```markdown
# Mod Specification: [Mod Name]
**Category**: [Gear | Spells | Classes & Subclasses | Progression & Rules | Utilities & Cheats]
**Author**: [Author] | **Version**: [Version] | **mod.io ID**: `[ID]`
**Mod Slug**: `[slug]` | **Features Documented**: `[count] implemented`
**URL**: `https://mod.io/g/baldursgate3/m/[slug]`

---

## Overview
[1-2 paragraph description of the mod, its purpose, and synergies]

---

## Implemented In-Game Features

| Feature Name & Type | In-Game Identifier | Base Stats & Modifiers | Granted Abilities, Spells & Passives (Full Mechanics) | Acquisition & Usage |
| :--- | :--- | :--- | :--- | :--- |
| **[Item / Spell Name]**<br>*[Weapon / Armor / Cantrip / Passive]* | `[Technical_ID]` | Base weapon damage, AC, crit range, or stat boosts | Detailed explanation of what the granted passives/spells actually do (damage roll, save DC, effect formula, cooldown) | Camp chest, merchant, or class progression unlock |
```

The catalog updater reads the mod.io ID, README title and overview, implemented-feature count, and containing directory name to populate Mod Id, Mod Name, Description, Features Documented, and Mod Slug. The Spec Link is generated from that slug. Never invent an unverified ID; leave it blank in the catalog until the ID is confirmed.

> [!IMPORTANT]
> If a weapon or piece of gear grants a passive or spell (e.g. `PassivesOnEquip` or `UnlockSpell`), the table MUST NOT just list the name of the passive. It must explain **what that passive actually does** (e.g., *"Adds +1d6 Force damage to every beam"* or *"Grants Advantage on Constitution Saving Throws"*).

---

## Step 5: Standardized Return Message

Once all steps are complete, output the final message:

### On Success
```markdown
mod '<Mod Name>' successfully added to library — <Brief 1-2 sentence description of what the mod does>
```

**Example**:
> `mod 'Elemental Eldritch Blast' successfully added to library — this mod alters the Warlock's 'Eldritch Blast' cantrip to allow choosing between 10 elemental damage types, fully compatible with Agonizing and Repelling Blast.`

### On Failure
If any unrecoverable error occurs (mod not found, malformed pak archive, missing API access, or no game features implemented):
```markdown
mod '<Mod Name>' failed: <Brief explanation of the failure reason>
```

**Example**:
> `mod 'InvalidModName' failed: No mod found on mod.io matching query 'InvalidModName'.`
