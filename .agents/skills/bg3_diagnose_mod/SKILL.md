---
name: bg3_diagnose_mod
description: Diagnoses BG3 mod issues, missing localization text, load order errors, sync discrepancies, and stat collisions, providing actionable automated fixes. Triggers on /bg3_diagnose_mod or when asked to debug or health-check a mod.
---

# BG3 Mod Diagnostic & Doctor Skill (`bg3_diagnose_mod`)

This skill acts as the autonomous "AI Doctor" for *Baldur's Gate 3* mods. It executes deterministic diagnostic scripts across 4 layers of mod health, analyzes the output, and interactively proposes and applies automated fixes.

---

## Trigger Conditions

Activate this skill when:
- The user runs `/bg3_diagnose_mod` or `/diagnose`.
- The user runs `/bg3_diagnose_mod logs` (or includes `logs`, e.g. `/bg3_diagnose_mod logs for <mod-slug>` / `check toolkit logs`).
- The user reports in-game or Toolkit issues:
  - *"Why is my mod throwing errors in the Toolkit / Glasses?"*
  - *"Check the latest Glasses message log."*
  - *"Why is my mod not showing up in-game?"*
  - *"My mod items have 'Not Found' / missing text."*
  - *"Check if my mod has any errors or conflicts."*
  - *"Why did the game crash or fail to load my spells?"*

---

## Diagnostic Pipeline

```mermaid
flowchart TD
    Trigger["User Request / /bg3_diagnose_mod"] --> CheckLogs{"Prompt includes 'logs' or Toolkit issue?"}
    CheckLogs -- "Yes" --> ToolkitLogMode["Run diagnose_toolkit_logs.py"]
    ToolkitLogMode --> Correlate["Correlate Log Errors to my_mods/"]
    Correlate --> SynthesizeLogs["Synthesize Log Findings & Propose Fixes"]
    CheckLogs -- "No" --> Identify["1. Identify Mod in my_mods/"]
    Identify --> RunVal["2. Run validate_mod.py --json"]
    RunVal --> RunLO["3. Run manage_load_order.py --json"]
    RunLO --> RunSync["4. Run sync_to_game_data.py --dry-run"]
    RunSync --> RunConf["5. Run check_mod_conflicts.py --json"]
    RunConf --> Synthesize["6. Synthesize Findings & Severity"]
    Synthesize --> ProposeFix["7. Propose Automated Remediation"]
```

---

## Execution Steps

### Step 1: Mode & Target Resolution
1. **Mode Check**:
   - If the user prompt includes `logs` (e.g. `/bg3_diagnose_mod logs`, `/bg3_diagnose_mod logs for <mod-slug>`, or requests to check Toolkit / Glasses message logs):
     - Proceed directly to **Step 2B: BG3 Toolkit Log Diagnostic Battery**.
   - Otherwise, proceed to **Step 2A: Full Mod Health Diagnostic Battery**.

2. **Target Resolution**:
   - Determine the target mod name from the prompt (`for <mod-slug>`, `<mod-slug>`), or inspect `my_mods/`:
     - If the user specifies a mod (e.g. `arcane-progression`), use it.
     - If unspecified and only one mod exists in `my_mods/`, select it.
     - If multiple mods exist and no mod was specified, run across workspace or prompt for clarification.

### Step 2A: Full Mod Health Diagnostic Battery (Static Linter Suite)
Run the deterministic diagnostic suite:

```bash
# 1. Structural & Handle Integrity Check
python3 scripts/validate_mod.py --mod <mod_slug> --json

# 2. In-Game Load Order Status Check
python3 scripts/manage_load_order.py --json

# 3. Game Data Synchronization Status Check
python3 scripts/sync_to_game_data.py --dry-run

# 4. Community Conflict & Collision Check
python3 scripts/check_mod_conflicts.py --candidate <mod_slug> --against-library --json

# 5. Localization Handle Orphan Audit
python3 scripts/sync_localization.py --mod <mod_slug> --check --json

# 6. Save Game & Load Order Compatibility Audit (Optional/On Request)
python3 scripts/inspect_save_game.py --audit --json
```

### Step 2B: BG3 Toolkit Log Diagnostic Battery (Glasses Runtime Suite)
When triggered with `logs` or when investigating Toolkit runtime errors:

```bash
# 1. Inspect Latest Toolkit Session (with workspace mod correlation)
python3 scripts/diagnose_toolkit_logs.py --mod <mod_slug> --json

# 2. Filter by Specific Subsystem (e.g. Boosts, Stats, Thoth, Osiris)
python3 scripts/diagnose_toolkit_logs.py --subsystem Boosts --mod <mod_slug> --json

# 3. Inspect Specific Log Type (engine, osiris, thoth, personal)
python3 scripts/diagnose_toolkit_logs.py --type thoth --limit 25

# 4. Stream Active Session Logs in Real-Time (during live mod testing)
python3 scripts/diagnose_toolkit_logs.py --follow
```

> [!TIP]
> **Tool Discovery & Schema Inspection**:
> To discover additional automation tools or inspect CLI flags dynamically, run:
> ```bash
> python3 scripts/tools.py --search "<intent or issue>" --json
> python3 scripts/tools.py --info <tool_name> --json
> ```

### Step 3: Synthesis & Problem Categorization

Map discovered issues to standard root causes:

| Symptom / Error | Root Cause | Automated Remediation |
| :--- | :--- | :--- |
| `Missing localization handle 'h...'` | String handle referenced in stat file not declared in `Localization/English/*.xml`. Results in `Not Found` in-game. | Add missing `<content contentuid="h..." version="1">Text</content>` to XML. |
| Mod missing from active load order | `modsettings.lsx` lacks `<node id="ModuleShortDesc">` for mod UUID. Mod will not load in-game. | `python3 scripts/manage_load_order.py --activate <UUID> <Name>` |
| Stale game Data files | Local changes in `my_mods/` not synced to `<Game>/Data`. | `python3 scripts/sync_to_game_data.py --bump-build` |
| `Version64` mismatch between Projects and Mods | `meta.lsx` desynchronization causing Toolkit load errors. | `python3 scripts/bump_mod_version.py --mod <mod_slug> --build` |
| Stat entry name collision | Community mod in `mods/` defines identical entry name in `Weapon.txt` or `Spell_*.txt`. | Rename entry prefix or use Compatibility Framework override. |

### Step 4: Presentation to User

Present diagnostics in a clear, formatted report:

```markdown
### 🩺 Mod Health Diagnosis: <Mod Name>

**Overall Health**: 🔴 Issues Detected | 🟡 Warnings Found | 🟢 Healthy

#### 1. Integrity & Localization
- [Status]: <Details on syntax, handles, and assets>

#### 2. Load Order & In-Game Activation
- [Status]: <Active / Inactive in modsettings.lsx>

#### 3. Game Data Deployment
- [Status]: <In sync / Stale files detected>

#### 4. Compatibility & Collisions
- [Status]: <Clean / Identified collisions>

---

### 🔧 Recommended Fixes:
1. **[Fix 1]**: <Description>
2. **[Fix 2]**: <Description>
```

Prompt the user to approve applying the recommended fixes automatically.
