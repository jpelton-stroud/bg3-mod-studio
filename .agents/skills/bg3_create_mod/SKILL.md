---
name: bg3_create_mod
description: Orchestrates concurrent subagents to grill, plan, scaffold, author, and validate Baldur's Gate 3 mods in my_mods/<ModSlug> (Stage 1 of the mod lifecycle). Triggers on /bg3_create_mod or requests to create a new BG3 mod.
---

# BG3 Mod Creation Orchestrator (Stage 1)

This skill defines the **Stage 1 (Creation)** orchestrator and automated parallel subagent pipeline for designing, scaffolding, authoring, and smoke-validating custom *Baldur's Gate 3* mods in `my_mods/<ModSlug>`.

Stage 1 is strictly scoped to the repository workspace:
1. Conducts an interactive **`grill-me`** interview to resolve all design branches.
2. Drafts a technical mod plan and pauses for **interactive user approval**.
3. Scaffolds `my_mods/<ModSlug>` with internal `<ModName>_<UUID>` Larian subdirectories via [`scripts/authoring/create_mod_scaffold.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/authoring/create_mod_scaffold.py).
4. Dispatches specialized **concurrent subagents in parallel** to author stats, progressions, localization, and documentation.
5. Runs read-only smoke checks (`validate_mod.py`, `sync_localization.py --check`) without modifying external game directories or `AppData/`.
6. Executes a **Progressive Gate Handoff** to **Stage 2: Diagnostics & Toolkit Sync** (`/bg3_diagnose_mod`).

## Discovery & Tooling

Inspect tool arguments, flags, and schema definitions with:

```bash
bg3 tools info mod-create
bg3 tools info scaffold-stat
bg3 tools info scaffold-progression
bg3 tools info scaffold-template
bg3 tools info inject-treasure
bg3 tools info validate
```

---

## Workflow Overview

```mermaid
flowchart TD
    A["Trigger: /bg3_create_mod or mod request"] --> B["Step 1: Unconditional Grill-Me Protocol
(.agents/skills/grill-me/SKILL.md)"]
    B --> C["ask_question Modals down Design Tree:
Scope, Class Progression, Spells, Stats, Dependencies"]
    C --> D["Step 2: Formulate Mod Specification & Implementation Plan"]
    D --> E{"Interactive User Approval Pause"}
    E -- "Changes Requested" --> C
    E -- "Approved" --> F["Step 3: Execute Workspace Scaffolding
bg3 mod create &lt;ModName&gt; --json"]
    F --> G["Scaffolded: my_mods/&lt;ModSlug&gt;/
- Projects/ & Mods/ meta.lsx
- Directory trees & placeholder icons"]
    G --> H["Step 4: Dispatch Concurrent Subagents via invoke_subagent"]
    
    subgraph Parallel Subagents
        H --> I1["Subagent 1: Stats & Spells Specialist
Stats/Generated/Data/*.txt, RootTemplates, Treasure"]
        H --> I2["Subagent 2: Progression & Lists Specialist
Progressions.lsx, SpellLists.lsx"]
        H --> I3["Subagent 3: Localization Specialist
English/&lt;ModName&gt;.xml & string handles"]
        H --> I4["Subagent 4: Documentation Specialist
README.md & mod spec tables"]
    end
    
    I1 --> J["Subagents complete & report reactively"]
    I2 --> J
    I3 --> J
    I4 --> J
    
    J --> K["Step 5: Read-Only Validation Gate
bg3 mod validate --mod &lt;slug&gt; --json
bg3 mod sync-localization --mod &lt;slug&gt; --check --json"]
    K --> L["Step 6: Progressive Gate Handoff
ask_question -> Proceed to Stage 2: /bg3_diagnose_mod &lt;slug&gt;"]
```

---

## Step 1: Mandatory Preliminary `grill-me` Protocol

Before drafting any plan or generating UUIDs/folders, the Orchestrator **MUST unconditionally execute the local `grill-me` protocol** defined in [`.agents/skills/grill-me/SKILL.md`](file:///home/jpstroud/projects/BaldursGate3/.agents/skills/grill-me/SKILL.md).

### Interview Execution Rules
1. **Analyze Context First**: Extract any mod names, classes, spells, or mechanics mentioned in earlier conversation.
2. **Interactive `ask_question` Modals**: Walk down each branch of the mod design tree one question at a time.
   - **Branch A (Mod Identity & Theme)**: Name (PascalCase, e.g. `ArcaneProgression`, `EldritchAscension`), summary, and character fantasy.
   - **Branch B (Classes & Progression)**: Target classes/subclasses, level bounds (e.g. 1-12 vanilla vs. 13-20 `UnlockLevelCurve`), and progression unlock levels.
   - **Branch C (Spells, Passives & Abilities)**: Action economy (Action, Bonus Action, Reaction), resource costs (Ki, Spell Slots, Action Surge), and damage/status effects.
   - **Branch D (Parent Dependencies)**: Base game only (`GustavDev`), companion frameworks like `UnlockLevelCurve` (`a2ffd0e4-c407-8642-2611-c934ea0b0a77`), or any community mod cataloged in `mods/library.md` (or on mod.io).
   - **Branch E (In-Game Acquisition & Item Drops)**: For equipment or item mods, identify container drop locations (Tutorial Chest on Nautiloid, Camp Chest, or Act 1-3 vendors like Arron or Dammon) for `scripts/authoring/inject_treasure_table.py`.
3. **Format Options**: Prefix the recommended option with `(Recommended)` and list it first. Format all options as direct user responses.

---

## Step 2: Mod Specification & Interactive User Approval

Once the interview reaches shared understanding, the Orchestrator synthesizes the results into a structured **Mod Implementation Plan**:

```markdown
# Mod Specification: <ModName>
- **Mod Name**: `<ModName>`
- **Category**: <Category>
- **Dependencies**: `GustavDev` [, `UnlockLevelCurve`]

### Mechanics Breakdown
| Feature | Class/Level | Type | Cost | Effect |
| :--- | :--- | :--- | :--- | :--- |
| ... | ... | ... | ... | ... |

### Target Files to Author
- `Projects/<ModName>_<UUID>/meta.lsx`
- `Mods/<ModName>_<UUID>/meta.lsx`
- `Public/<ModName>_<UUID>/Stats/Generated/Data/Spell_*.txt`
- `Public/<ModName>_<UUID>/Stats/Generated/Data/Passive.txt`
- `Public/<ModName>_<UUID>/Progressions/Progressions.lsx`
- `Public/<ModName>_<UUID>/Lists/SpellLists.lsx`
- `Localization/English/<ModName>.xml`
- `README.md`
```

> [!CAUTION]
> **Approval Gate**: Stop and yield control to the user. Do NOT scaffold directories or write mod code until the user gives explicit confirmation on the plan.

---

## Step 3: Workspace Scaffolding

After user approval, run [`scripts/authoring/create_mod_scaffold.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/authoring/create_mod_scaffold.py) to establish the directory layout, metadata, and pre-allocated string handles:

```bash
bg3 mod create "<ModName>" \
  [--slug "<mod-slug>"] \
  --author "MTGHillGiant" \
  --description "<Description>" \
  [--unlock-level-curve] \
  [--dependency "<CommunityModNameOrSlug>"] \
  --json
```

Capture the JSON response containing:
- `mod_slug`: Main workspace folder under `my_mods/<mod-slug>`
- `larian_folder` / `folder_name`: Larian module directory `<ModName>_<UUID>`
- `uuid`: Module UUID
- `stats_dir`, `progressions_dir`, `lists_dir`
- `localization_file`
- `allocated_handles`: Pre-generated localization UUID handles (`h...`)

---

## Step 4: Dispatch Concurrent Subagents (`invoke_subagent`)

The Orchestrator launches specialized subagents in parallel to author the mod's components concurrently:

```json
{
  "Subagents": [
    {
      "TypeName": "self",
      "Role": "Stats & Spells Specialist - <ModName>",
      "Prompt": "Author the BG3 stat entries in <stats_dir>. Mod: <ModName>, UUID: <UUID>.\nTo ensure 100% engine compliance and valid localization handle allocation, use:\n  python3 scripts/authoring/scaffold_stat_entry.py --mod <ModName> --type <weapon|armor|amulet|ring|spell_target|passivedata> --name <Id> --display-name \"<Name>\" --description \"<Desc>\" --props \"<Props>\"\nFor weapons/armor/objects, bind 3D visual models using:\n  python3 scripts/authoring/scaffold_root_template.py --mod <ModName> --item <Id> --visual-preset <greatsword|longsword|staff|plate|robe|amulet|ring|boots|cloak>\nFor custom item container/vendor drops, inject drops using:\n  bg3 mod inject-treasure --mod <ModName> --item <ItemName> --container <tutorial_chest|camp_chest|vendor_...>\nRefer to the approved plan for exact mechanics.",
      "Workspace": "inherit",
      "Model": "flash"
    },
    {
      "TypeName": "self",
      "Role": "Progression & Lists Specialist - <ModName>",
      "Prompt": "Author progression and spell list LSX files in <public_dir>. Mod: <ModName>, UUID: <UUID>.\nTo ensure valid Larian v4.8 XML schema without crashing the level-up screen, use:\n  python3 scripts/authoring/scaffold_progression_node.py --mod <ModName> --class <Class> --level <Level> [--subclass <Subclass>] [--passives <Passives>] [--boosts <Boosts>] [--spells <Spells>] [--feat]\nEnsure valid Larian v4.8 LSX schema with proper UUIDs.\nRefer to the approved plan for exact progression assignments.",
      "Workspace": "inherit",
      "Model": "flash"
    },
    {
      "TypeName": "self",
      "Role": "Localization Specialist - <ModName>",
      "Prompt": "Author the localization XML file at <localization_file> for mod <ModName>.\nPopulate with all DisplayName and Description handles referenced by the Stats and Progressions specialists:\n<content contentuid=\"<Handle>\" version=\"1\">Text</content>\nEnsure valid XML syntax with utf-8 encoding.",
      "Workspace": "inherit",
      "Model": "flash"
    },
    {
      "TypeName": "self",
      "Role": "Documentation Specialist - <ModName>",
      "Prompt": "Update and enrich the mod documentation at <readme_file> for mod <ModName>.\nInclude:\n- Mod overview and author info\n- Level-by-level feature tables and mechanics\n- Dependencies and recommended load order\n- Toolkit import and sync instructions\nFollow the rich spec format used across the workspace.",
      "Workspace": "inherit",
      "Model": "flash"
    }
  ]
}
```

> [!TIP]
> **Subagent Tool Discovery**:
> Subagents can query and inspect the studio tooling registry dynamically at any time:
> ```bash
> bg3 tools search "<intent>" --json
> bg3 tools info <tool_name> --json
> ```

---

## Step 5: Orchestrator Reactive Validation Smoke Check

The Orchestrator halts tool execution and waits for reactive completion messages from all subagents.

Once all subagents have reported success, run read-only validation on the workspace files without touching game `Data/` or `AppData/`:

```bash
bg3 mod validate --mod <mod-slug> --json
bg3 mod sync-localization --mod <mod-slug> --check --json
```

Verify:
- XML and LSX well-formedness
- Metadata parity between `Projects/` and `Mods/` `meta.lsx`
- Localization handle references (`h...;1`) against `English/<ModName>.xml`
- Spell references in `SpellLists.lsx` against local stats
- Compliance of 512×512 PNG thumbnails and logos

If any errors or missing handles are found, prompt the subagents to repair them in `my_mods/<mod-slug>`.

---

## Step 6: Progressive Gate Handoff to Stage 2

Do not synchronize files to `<Game>/Data/` or build `.pak` archives in Stage 1. Instead, present a concise status report of scaffolded and authored files, then hand off to **Stage 2: Diagnostics & Toolkit Sync**:

```text
Mod '<ModName>' successfully authored and verified in my_mods/<mod-slug>!
```

Use `ask_question` to transition:
- **Proceed to Stage 2 Diagnostics**: Run `/bg3_diagnose_mod <mod-slug>` to perform Phase 2A static checks and game sync, load into the BG3 Toolkit (`Glasses.exe`), and execute Phase 2B runtime log triage.
- **Review Workspace Files**: Keep working in `my_mods/<mod-slug>` before proceeding to diagnostics.

