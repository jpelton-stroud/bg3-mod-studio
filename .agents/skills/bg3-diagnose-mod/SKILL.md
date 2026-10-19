---
name: bg3-diagnose-mod
description: Diagnoses BG3 mod issues, missing localization text, load order errors, sync discrepancies, and stat collisions, providing actionable automated fixes (Stage 2 of the mod lifecycle). Triggers on /bg3-diagnose-mod, /diagnose, or when handed off by bg3-create-mod.
---

# BG3 Mod Diagnostics & Toolkit Verification (Stage 2) (`bg3-diagnose-mod`)

This skill acts as the autonomous "AI Doctor" and **Stage 2** verification gate for *Baldur's Gate 3* mods. It manages **User-Action Gate 1 (Toolkit Diagnostics)**:
- **Phase 2A (Workspace Assertion, Game Sync & Toolkit Launch Gate)**: Asserts clean static workspace state, synchronizes unpacked mod assets and compiled binary `.loca` to `<Game>/Data/`, and directs the user to load the mod in the BG3 Toolkit (`Glasses.exe`) to generate engine runtime logs.
- **Phase 2B (Toolkit Runtime Log Diagnosis & Automated Remediation Loop)**: Upon user confirmation that logs are generated, triages `Glasses.exe` runtime log warnings/errors (`diagnose_toolkit_logs.py`), applies targeted fixes in `my_mods/<slug>/`, re-syncs, and loops until logs are clean before offering Stage 3 testing.
- **Progressive Gate Handoff**: Passes verified mods to **Stage 3: In-Game Testing** ([`bg3-test-mod`](../bg3-test-mod/SKILL.md)).

## Discovery & Tooling

Inspect tool arguments, flags, and schema definitions with:

```bash
python3 scripts/bg3.py tools info validate
python3 scripts/bg3.py tools info sync-loca
python3 scripts/bg3.py tools info check-conflicts
python3 scripts/bg3.py tools info sync-game
python3 scripts/bg3.py tools info toolkit-logs
```

---

## Workflow Overview

```mermaid
flowchart TD
    Trigger["Trigger: /bg3-diagnose-mod &lt;slug&gt;"] --> Phase2A["Phase 2A: Workspace Assertion &amp; Game Sync"]
    
    subgraph Phase 2A Workspace Assertion &amp; Game Sync
        Phase2A --> Assert["1. Workspace Assertion (verify clean static checks)
python3 scripts/bg3.py mod validate &lt;slug&gt; --json"]
        Assert --> Sync["2. Sync Assets &amp; Binary .loca to Data/
python3 scripts/bg3.py mod sync-data --mods &lt;slug&gt; --json"]
        Sync --> PromptUser["3. Direct User to Load Mod in Toolkit (Glasses.exe) [User-Action Gate 1]
Prompt: Logs generated?"]
    end
    
    PromptUser --> UserGate{"User Confirmation (ask_question)"}
    UserGate -- "Logs Generated" --> Phase2B["Phase 2B: Runtime Log Diagnosis"]
    UserGate -- "Skip Log Triage" --> Gate["Stage 3 Handoff Gate: ask_question"]
    
    subgraph Phase 2B Runtime Log Triage &amp; Fixes
        Phase2B --> Logs["1. Triage Glasses Runtime Logs
python3 scripts/bg3.py mod diagnose-logs --mod &lt;slug&gt; --severity warning --json"]
        Logs --> LogFix{"Toolkit Errors Found?"}
        LogFix -- "Yes (≤3 cycles)" --> Patch2B["Fix in my_mods/ and Loop to 2A"]
        LogFix -- "Circuit Breaker / Override" --> Gate
        LogFix -- "No" --> Gate
    end
    
    Patch2B --> Phase2A
    Gate --> TestMod["Proceed to Stage 3: /bg3-test-mod &lt;slug&gt;"]
```

---

## Execution Steps

### Step 1: Target Resolution
Determine the target mod name from the prompt (`for <mod-slug>`, `<mod-slug>`), or inspect `my_mods/`:
- If the user specifies a mod (e.g. `paladins-call`), use it.
- If unspecified and only one mod exists in `my_mods/`, select it.
- If multiple mods exist and no mod was specified, prompt the user to select one.

---

### Step 2A: Workspace Assertion, Game Sync & Toolkit Launch Gate

#### 1. Pre-Flight Workspace Assertion
Stage 1 guarantees static cleanliness, so Step 1 runs a rapid deterministic pre-flight assertion on `my_mods/<slug>/` before touching game files:

```bash
# Structural, LSX, XML, and Handle Integrity Assertion
python3 scripts/bg3.py mod validate <mod-slug> --json
```

If assertion fails unexpectedly, resolve the discrepancy or re-run validation before proceeding. When clean, immediately proceed to game data synchronization.

#### 2. Synchronize Assets & Binary `.loca` to Game Data
Synchronize unpacked mod assets and compile localization strings to `<Game>/Data/`:

```bash
python3 scripts/bg3.py mod sync-data --mods <mod-slug> --json
```

> [!NOTE]
> `sync_game_data.py` automatically compiles `Localization/English/*.xml` into `Data/Mods/<ModName>_<UUID>/Localization/English/<ModName>.loca` so the BG3 Toolkit loads strings cleanly without crashing.

#### 3. Direct User to Load Mod in BG3 Toolkit (Glasses.exe) [User-Action Gate 1]
Instruct the user:
1. Launch **Baldur's Gate 3 Toolkit** (`Glasses.exe`).
2. Select **File -> Open Project...** and open `<ModName>`.
3. Verify that stats, root templates, and progressions load in the editor, allowing the game engine to generate fresh runtime log entries.

Prompt the user using `ask_question`:
- **(Recommended) Logs generated (proceed to Phase 2B diagnostics)**
- **Skip log triage (proceed directly to Phase 3 testing)**

---

### Step 2B: Toolkit Runtime Log Diagnosis & Automated Remediation Loop

Upon receiving confirmation that logs have been generated:

#### 1. Inspect Toolkit Runtime Logs
Run deterministic log triage to catch any engine warnings or script exceptions:

```bash
# Inspect latest Toolkit session with workspace mod correlation
python3 scripts/bg3.py mod diagnose-logs --mod <mod-slug> --severity warning --json

# Or filter by specific subsystem (e.g. Boosts, Stats, Thoth, Osiris)
python3 scripts/bg3.py mod diagnose-logs --subsystem Boosts --mod <mod-slug> --json

# Or stream active session logs live during user inspection
python3 scripts/bg3.py mod diagnose-logs --follow
```

#### 2. Remediate & Loop to Phase 2A
If log warnings/errors are detected:
1. Correlate line numbers, missing references, and IDs back to `my_mods/<mod-slug>/`.
2. Apply targeted fixes directly to source files in `my_mods/<mod-slug>/`.
3. **Loop Prevention Guardrail**:
   - Limit full 2A <-> 2B diagnostic cycles to **3 iterations**.
   - If identical log error signatures persist after a patch, trip the circuit breaker and escalate to user via `ask_question`.
4. **Automatically loop back to Step 2A**:
   - Re-run rapid pre-flight assertion (`validate_mod.py`).
   - Re-sync to game data (`sync_game_data.py`).
   - Prompt the user to reload the project in `Glasses.exe` to generate fresh logs.

Repeat until logs are clean (0 warnings/errors) or the user opts to proceed.

---

### Step 3: Progressive Gate Handoff to Stage 3

Once static checks and Toolkit runtime diagnostics are clear (or skipped by user), present a concise mod health summary and transition to **Stage 3: In-Game Testing**:

```text
Mod '<ModName>' is clean and verified in the BG3 Toolkit!
- Static validation: PASS (0 errors, 0 orphaned handles)
- Conflict triage: PASS (no collisions)
- Toolkit logs: PASS (0 warnings/errors)
```

Use `ask_question` to transition:
- **Proceed to Stage 3 In-Game Testing**: Run `/bg3-test-mod <mod-slug>` to package a local test `.pak`, activate it in `modsettings.lsx`, and test in-game save loading.
- **Keep diagnosing / refine in Toolkit**: Stay in Stage 2 to adjust mechanics or inspect logs further.
