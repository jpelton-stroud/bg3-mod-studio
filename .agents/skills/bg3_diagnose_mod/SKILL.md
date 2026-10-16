---
name: bg3_diagnose_mod
description: Diagnoses BG3 mod issues, missing localization text, load order errors, sync discrepancies, and stat collisions, providing actionable automated fixes (Stage 2 of the mod lifecycle). Triggers on /bg3_diagnose_mod, /diagnose, or when handed off by bg3_create_mod.
---

# BG3 Mod Diagnostics & Toolkit Verification (Stage 2)

This skill acts as the autonomous "AI Doctor" and **Stage 2** verification gate for *Baldur's Gate 3* mods. It follows a two-phase Shift-Left protocol:
- **Phase 2A (Static Pre-Flight & Conflict Triage)**: Audits syntax, localization handles, and community stat collisions in `my_mods/<slug>/` before touching the game directory.
- **Phase 2B (Toolkit Sync & Glasses.exe Log Diagnosis)**: Syncs unpacked assets and compiled binary `.loca` to `<Game>/Data/`, directs Toolkit project verification, and triages `Glasses.exe` runtime log warnings/errors.
- **Progressive Gate Handoff**: Passes verified mods to **Stage 3: In-Game Testing** (`/bg3_test_mod`).

## Discovery & Tooling

Inspect tool arguments, flags, and schema definitions with:

```bash
python3 scripts/tools.py --info validate
python3 scripts/tools.py --info sync-localization
python3 scripts/tools.py --info check-conflicts
python3 scripts/tools.py --info sync-data
python3 scripts/tools.py --info diagnose-logs
```

---

## Workflow Overview

```mermaid
flowchart TD
    Trigger["Trigger: /bg3_diagnose_mod &lt;slug&gt;"] --> Phase2A["Phase 2A: Static Pre-Flight
my_mods/&lt;slug&gt;/ only"]
    
    subgraph Phase 2A Static Triage
        Phase2A --> Val["1. Structural & Handle Integrity
python3 scripts/validate_mod.py --mod &lt;slug&gt; --json"]
        Val --> Loc["2. Localization Handle Audit
python3 scripts/sync_localization.py --mod &lt;slug&gt; --check --json"]
        Loc --> Conf["3. Library Collision Check
python3 scripts/check_mod_conflicts.py --candidate &lt;slug&gt; --against-library --json"]
        Conf --> Fix2A{"Static Issues Found?"}
        Fix2A -- "Yes" --> Patch2A["Propose & Apply Fixes
sync_localization --prune, patch files"]
        Patch2A --> Val
        Fix2A -- "No" --> Phase2B["Phase 2B: Toolkit Sync & Runtime Verification"]
    end
    
    subgraph Phase 2B Toolkit Sync & Logs
        Phase2B --> Sync["1. Sync Assets & Binary .loca to Data/
python3 scripts/sync_to_game_data.py --mods &lt;slug&gt; --json"]
        Sync --> UserToolkit["2. Direct User to Open Project in BG3 Toolkit (Glasses.exe)"]
        UserToolkit --> Logs["3. Triage Glasses Runtime Logs
python3 scripts/diagnose_toolkit_logs.py --mod &lt;slug&gt; --severity warning --json"]
        Logs --> LogFix{"Toolkit Errors Found?"}
        LogFix -- "Yes" --> Patch2B["Fix in my_mods/ and Re-sync"]
        Patch2B --> Sync
        LogFix -- "No" --> Gate["Stage 3 Handoff Gate: ask_question"]
    end
    
    Gate --> TestMod["Proceed to Stage 3: /bg3_test_mod &lt;slug&gt;"]
```

---

## Execution Steps

### Step 1: Target Resolution
Determine the target mod name from the prompt (`for <mod-slug>`, `<mod-slug>`), or inspect `my_mods/`:
- If the user specifies a mod (e.g. `paladins-call`), use it.
- If unspecified and only one mod exists in `my_mods/`, select it.
- If multiple mods exist and no mod was specified, prompt the user to select one.

---

### Step 2A: Static Pre-Flight & Conflict Triage (Repository Workspace)

Run deterministic static checks on `my_mods/<slug>/` before touching game files:

```bash
# 1. Structural, LSX, and XML Integrity Check
python3 scripts/validate_mod.py --mod <mod-slug> --json

# 2. Localization Handle Audit (check for orphaned or missing handles)
python3 scripts/sync_localization.py --mod <mod-slug> --check --json

# 3. Community Conflict & Collision Check
python3 scripts/check_mod_conflicts.py --candidate <mod-slug> --against-library --json
```

#### Remediation for Phase 2A:
- **Missing Localization Handles**: Add missing `<content contentuid="h..." version="1">Text</content>` to `Localization/English/<ModName>.xml`.
- **Orphaned Localization Handles**: Run `python3 scripts/sync_localization.py --mod <mod-slug> --prune --json` after user confirmation.
- **Stat Entry Collisions**: When colliding with a tracked mod in `mods/library.md`, rename the stat prefix or generate a compatibility patch via `python3 scripts/generate_compat_patch.py`.
- Re-run validation to ensure clean status before moving to Phase 2B.

---

### Step 2B: Toolkit Sync & Runtime Log Diagnosis (Glasses.exe)

Once static checks pass cleanly, synchronize the mod's assets and compiled binary `.loca` to the game's `Data/` directory:

```bash
python3 scripts/sync_to_game_data.py --mods <mod-slug> --json
```

> [!NOTE]
> `sync_to_game_data.py` automatically compiles `Localization/English/*.xml` into `Data/Mods/<ModName>_<UUID>/Localization/English/<ModName>.loca` so the BG3 Toolkit loads strings cleanly without crashing.

#### Direct User to Toolkit:
Instruct the user:
1. Launch **Baldur's Gate 3 Toolkit** (`Glasses.exe`).
2. Select **File -> Open Project...** and select `<ModName>`.
3. Verify that stats, root templates, and progressions load cleanly in the editor.

#### Inspect Toolkit Runtime Logs:
Run deterministic log triage to catch any engine warnings or script exceptions:

```bash
# Inspect latest Toolkit session with workspace mod correlation
python3 scripts/diagnose_toolkit_logs.py --mod <mod-slug> --severity warning --json

# Or filter by specific subsystem (e.g. Boosts, Stats, Thoth, Osiris)
python3 scripts/diagnose_toolkit_logs.py --subsystem Boosts --mod <mod-slug> --json

# Or stream active session logs live during user inspection
python3 scripts/diagnose_toolkit_logs.py --follow
```

If log errors occur:
1. Correlate line numbers and IDs back to `my_mods/<mod-slug>/`.
2. Apply the fix in the source files.
3. Re-sync via `python3 scripts/sync_to_game_data.py --mods <mod-slug> --json`.
4. Re-check logs until clean.

---

### Step 3: Progressive Gate Handoff to Stage 3

Once static checks and Toolkit runtime diagnostics are clear, present a concise mod health summary and transition to **Stage 3: In-Game Testing**:

```text
Mod '<ModName>' is clean and verified in the BG3 Toolkit!
- Static validation: PASS (0 errors, 0 orphaned handles)
- Conflict triage: PASS (no collisions)
- Toolkit logs: PASS (0 warnings/errors)
```

Use `ask_question` to transition:
- **Proceed to Stage 3 In-Game Testing**: Run `/bg3_test_mod <mod-slug>` to package a local test `.pak`, activate it in `modsettings.lsx`, and test in-game save loading.
- **Keep diagnosing / refine in Toolkit**: Stay in Stage 2 to adjust mechanics or inspect logs further.
