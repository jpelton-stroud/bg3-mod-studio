# Baldur's Gate 3 Mod Creation Workflow Guide

This guide walks through creating, authoring, diagnosing, testing, and publishing custom *Baldur's Gate 3* mods in this workspace.

---

## 1. Chat-First Development & Shift-Left Architecture

Development in this studio follows two foundational principles:

1. **Chat First**: Rather than manually executing command-line scripts, you drive every stage of mod creation conversationally through specialized slash commands (`/bg3-create-mod`, `/bg3-diagnose-mod`, `/bg3-test-mod`, `/bg3-release-prep`, `/bg3-post-release`). Autonomous agent skills orchestrate subagents, manage progressive review gates, and invoke deterministic Python scripts under the hood.
2. **Shift Left + Loopback**: Potential bugs, XML/LSX structural errors, broken localization handles, and community stat collisions are caught as early as possible—statically in Stage 1 and via BG3 Toolkit runtime logs in Stage 2—long before packaging or loading into a full game campaign. If gameplay anomalies appear during in-game testing, the workflow provides dual-track loopback to authoring patches or toolkit diagnostics.

### 5-Stage Shift-Left & Loopback Lifecycle

```mermaid
flowchart TD
    S1["Stage 1: Creation (/bg3-create-mod)
    • /grill-me interview & specification plan
    • Autonomous scaffolding & parallel subagents
    • Static verification (LSX, string handles, conflict pre-check)"]
    
    S2["Stage 2: Diagnostics & Toolkit Staging (/bg3-diagnose-mod)
    • Toolkit staging (Data/ sync & binary .loca compilation)
    • User-Action Gate 1: Glasses.exe launch & messages.log triage
    • Automated remediation loopback"]
    
    S3["Stage 3: Clean-Room In-Game Testing (/bg3-test-mod)
    • Loose Data purge, local test .pak deploy & load order isolation
    • User-Action Gate 2: bg3.exe launch & gameplay verification
    • Dual-Track Defect Routing"]
    
    S4["Stage 4: Release Preparation (/bg3-release-prep)
    • Atomic Version64 bump & strict lint validation
    • Localization prune/compile & GFM HTML render
    • Data/ staging for User-Action Gate 3: Toolkit publishing
    • Optional standalone dist/<slug>.pak package"]
    
    S5["Stage 5: Post-Release & Teardown (/bg3-post-release)
    • Storefront governance via REST API (tags, permissions, visibility)
    • Mandatory dev teardown (purge Data/, clean .pak, disable load order)
    • Consumer subscriber live verification"]
    
    S1 -->|Stage 1 Gate| S2
    S2 -->|User-Action Gate 1 Passed| S3
    S3 -->|Playtesting Passed| S4
    S3 -.->|Engine Crash / Broken Asset (Stage 2 Loopback)| S2
    S3 -.->|Gameplay / Mechanics Bug (Stage 1 Authoring Patch)| S1
    S4 -->|User-Action Gate 3: Publish in Toolkit| S5
```

> [!NOTE]
> For in-depth CLI options, script arguments, and low-level technical specifications for each automation script, refer to [FEATURES.md](FEATURES.md).

---

## 2. Stage 1: Autonomous Creation (`/bg3-create-mod`)

Trigger mod creation conversationally by describing your concept or invoking the slash command:

```text
/bg3-create-mod "A finesse longsword for Eldritch Knights scaling with INT"
```

The [`bg3-create-mod`](../.agents/skills/bg3-create-mod/SKILL.md) skill orchestrates the entire creation pipeline across five distinct phases:

### Step 1: Design Interview (`grill-me` Protocol)
The orchestrator immediately initiates a structured interview to resolve design branches:
- Progression levels (Standard 1–12 vs. Level 20 UnlockLevelCurve support)
- Weapon/armor rarity, properties, damage dice, and enchantments
- Associated passive features, spells, and resource costs
- Required dependencies (e.g., `CompatibilityFramework`, `CommunityLibrary`)

### Step 2: Mod Specification & Interactive Approval Gate
The agent synthesizes decisions into a technical mod specification plan. **Execution pauses until you explicitly approve the plan** via the interactive UI prompt.

### Step 3: Workspace Scaffolding
Upon approval, the agent generates the standardized directory hierarchy in `my_mods/<ModSlug>/` via `bg3 mod scaffold` (`scripts/authoring/create_mod_scaffold.py`):
- `Projects/<UUID>/meta.lsx` & `Mods/<UUID>/meta.lsx` (with auto-generated deterministic UUIDv4 and Larian `Version64` tags)
- `Public/<UUID>/Stats/Generated/Data/` (for engine stats and spells)
- `Public/<UUID>/RootTemplates/_merged.lsx` (for 3D GameObject templates)
- `Localization/English/<ModName>.xml` (for localized text handles)
- `.test_deps.json` (optional manifest for test-only prerequisite dependencies)
- `my_mods/<ModSlug>/README.md` (rich mod specification document)

### Step 4: Parallel Subagent Dispatch
The orchestrator launches specialized background subagents concurrently to author components in parallel using domain tooling:
- **Stats & Spells Specialist**: Authors stat definitions, passives, and spell entries via `bg3 scaffold stat` (`scripts/authoring/scaffold_stat_entry.py`).
- **Progression Specialist**: Configures `Progressions.lsx` and `SpellLists.lsx` for class levels or spells via `bg3 scaffold progression` (`scripts/authoring/scaffold_progression_node.py`).
- **RootTemplate Specialist**: Binds stats to visual meshes and collision via `bg3 scaffold root-template` (`scripts/authoring/scaffold_root_template.py`).
- **World Drop Specialist**: Injects items into world drop containers via `bg3 mod inject-treasure` (`scripts/authoring/inject_treasure_table.py`).
- **Dependency Specialist**: Injects community or test dependencies via `bg3 mod add-dependency` (`scripts/authoring/add_mod_dependency.py`).
- **Localization Specialist**: Generates unique `h...;1` string handles in `Localization/English/<ModName>.xml`.
- **Documentation Specialist**: Compiles feature matrices and tables in the mod's `README.md`.

#### Subagent Output Snippets

```text
// Public/<UUID>/Stats/Generated/Data/Weapon.txt
new entry "MAG_ArcaneBlade"
type "Weapon"
using "WPN_Longsword_1"
data "Rarity" "VeryRare"
data "DefaultBoosts" "WeaponEnchantment(2);WeaponProperty(Finesse)"
data "PassivesOnEquip" "MAG_ArcaneBlade_Passive"
data "DisplayName" "h4a70cb6dg5661g4c14g98a0g70b4a45749f9;1"
data "Description" "ha3316e15g6546g48bag9827gc56306e90e78;1"
```

```xml
<!-- Localization/English/<ModName>.xml -->
<?xml version="1.0" encoding="utf-8"?>
<contentList>
  <content contentuid="h4a70cb6dg5661g4c14g98a0g70b4a45749f9" version="1">Blade of the Weave</content>
  <content contentuid="ha3316e15g6546g48bag9827gc56306e90e78" version="1">Attacks with this weapon use your Spellcasting Ability Modifier instead of Strength or Dexterity.</content>
</contentList>
```

### Step 5: Comprehensive Workspace Static Verification Gate
The orchestrator awaits completion from all parallel subagents and executes comprehensive read-only static verification strictly within `my_mods/<ModSlug>/` without modifying game `Data/` or `AppData/`:
1. **LSX & XML Integrity**: Verifies well-formedness and schema compliance via `bg3 mod validate <slug>` (`scripts/diagnostics/validate_mod.py`).
2. **Metadata Parity**: Asserts identical UUID, author, and `Version64` tags between `Projects/<UUID>/meta.lsx` and `Mods/<UUID>/meta.lsx`.
3. **String Handle Parity**: Verifies that every `DisplayName` and `Description` handle referenced across stat entries exists in `Localization/English/<ModName>.xml` via `bg3 mod sync-localization --mod <slug> --check` (`scripts/diagnostics/sync_localization.py`).
4. **Spell List Parity**: Confirms spell identifiers referenced in `SpellLists.lsx` match declared spell definitions.
5. **Library Conflict Pre-Check**: Checks candidate stats and RootTemplates against over 2,200 cataloged community mods in `mods/library.md` via `bg3 mod conflict <slug> --against-library` (`scripts/diagnostics/check_mod_conflicts.py`).
6. **Visual Assets**: Ensures compliant 512×512 PNG thumbnails and logos exist in project folders.

If any missing handles or syntax errors are detected, the orchestrator directs the subagents to repair the issues in `my_mods/<ModSlug>/` before proceeding.

### Step 6: Progressive Gate Handoff to Stage 2
Stage 1 maintains strict workspace isolation: it does not touch `<Game>/Data/` or build `.pak` archives. Because workspace static verification is 100% clean, the orchestrator presents an interactive `ask_question` gate prompting you to transition into **Stage 2: Diagnostics & Toolkit Staging** (`/bg3-diagnose-mod <slug>`).

---

## 3. Stage 2: Diagnostics & Toolkit Staging (`/bg3-diagnose-mod`)

Stage 2 acts as the autonomous mod doctor and governs **User-Action Gate 1 (Toolkit Diagnostics)**:

```text
/bg3-diagnose-mod arcane-blade
```

The [`bg3-diagnose-mod`](../.agents/skills/bg3-diagnose-mod/SKILL.md) skill operates in two synchronized phases:

### Phase 2A: Workspace Assertion, Game Sync & Toolkit Launch Gate
1. **Workspace Static Assertion**: Runs a rapid deterministic validation check (`bg3 mod validate <slug>`) to assert that workspace files in `my_mods/<ModSlug>/` remain structurally sound.
2. **Toolkit Staging (Data/ Sync & Binary .loca Compilation)**: Synchronizes unpacked mod source trees (`Editor/Mods/`, `Projects/`, `Public/`) and compiles `Localization/English/<ModName>.xml` into a binary `.loca` directly within `<Game>/Data/` via `bg3 mod sync-data --mods <slug>` (`scripts/packaging/sync_game_data.py`).
3. **User-Action Gate 1 (Toolkit Launch)**: Prompts you to launch the official Baldur's Gate 3 Toolkit (`Glasses.exe`), open your mod project, and allow the engine to load assets and generate runtime log entries in `messages.log`.

### Phase 2B: Runtime Log Triage & Automated Remediation Loop
Once you confirm via `ask_question` that `Glasses.exe` has loaded the mod:
1. **Engine Log Diagnosis**: Triages runtime warnings, asset loading errors, or stat inheritance flaws from `Glasses.exe` logs (`messages.log`) via `bg3 mod diagnose-logs --mod <slug>` (`scripts/diagnostics/diagnose_toolkit_logs.py`).
2. **Automated Source Remediation**: Proposes and applies targeted patches directly to the source files in `my_mods/<ModSlug>/`.
3. **Automated Re-Sync Loop**: The skill loops back to Phase 2A, re-syncing patched files to `<Game>/Data/` and re-verifying until logs are clean (or user override / circuit breaker triggers).
4. **Stage 3 Handoff**: Once Toolkit logs report zero unresolved errors, the skill prompts you to advance to Stage 3 In-Game Testing.

---

## 4. Stage 3: In-Game Testing & Verification (`/bg3-test-mod`)

Deploy and test your mod in an actual game session:

```text
/bg3-test-mod arcane-blade
```

The [`bg3-test-mod`](../.agents/skills/bg3-test-mod/SKILL.md) skill governs **User-Action Gate 2 (In-Game Playtesting)** with a progressive two-tier testing protocol:

### Phase 3A: Clean-Room / Smoke Testing (Default Fast Path)
1. **Loose Data Purge & Local .pak Deployment**: Purges loose development files from `<Game>/Data/` using `bg3 mod sync-data --clean-mod <slug>` (`scripts/packaging/sync_game_data.py`) to prevent Larian Virtual File System (VFS) loose-file shadowing and engine locks, then builds an uncorrupted test `.pak` archive deployed directly to `AppData/Mods/` via `bg3 mod pack --mod <slug> --publish-local` (`scripts/packaging/pack_mod_pak.py`).
2. **Clean-Room Load Order Isolation**: Resolves dependencies from `meta.lsx` and `.test_deps.json`, then activates the target mod and its closure in `modsettings.lsx` while temporarily disabling unrelated mods via `bg3 loadorder --enable <slug> --with-deps --isolate` (`scripts/management/manage_load_order.py`).
3. **User-Action Gate 2 (In-Game Playtesting)**: You launch Baldur's Gate 3 (`bg3.exe`), start a new game or load a clean minimal test save, and verify:
   - **Acquisition**: Container drops (Nautiloid Tutorial Chest, Camp Chest) or vendor inventory.
   - **Tooltips**: Accurate names and descriptions without `Not Found` or raw string handles.
   - **Mechanics**: Spell casting, passive triggers, action economy, and level-up progression screens.
   - **Persistence**: Save the game, reload, and verify state persistence.

### Phase 3B: Multi-Mod Integration & Save Audit (Optional Gate)
For complex mods, class overhauls, or campaign validation:
- Validates profile load order compatibility against active third-party mods via `bg3 loadorder --enable <slug> --validate`.
- Audits existing campaign save games via `bg3 mod inspect-save --audit` (`scripts/diagnostics/inspect_save_game.py`) to confirm safe loading without missing template errors.
- Optionally simulates build synergy matrices via `bg3 build simulate`.
- Verifies post-test save integrity via `bg3 mod inspect-save`.

### Dual-Track Defect Routing
If issues emerge during playtesting, the workflow routes defects along two specialized tracks rather than a generic loopback:
1. **Track 1: Engine Crash, Missing Asset, or Broken Script**:
   Routes back to **Stage 2: Diagnostics (`/bg3-diagnose-mod <slug>`)**. The skill re-syncs source files to `<Game>/Data/`, directs you to launch `Glasses.exe` (User-Action Gate 1) to inspect engine crash diagnostics and `messages.log`, applies fixes, and re-syncs.
2. **Track 2: Gameplay Mechanics, Balance, or Stat Calculation Bug**:
   Routes to **Stage 1 Authoring Patch**: The agent applies targeted patches directly to source files in `my_mods/<ModSlug>/`, executes Step 1 loose file purge and local `.pak` re-packaging (`bg3 mod sync-data --clean-mod` + `bg3 mod pack --publish-local`), and prompts you to resume in-game testing immediately without an unnecessary Toolkit staging cycle.

---

## 5. Stage 4: Release Preparation (`/bg3-release-prep`)

When in-game testing is complete and verified, prepare the mod for publication:

```text
/bg3-release-prep arcane-blade
```

The [`bg3-release-prep`](../.agents/skills/bg3-release-prep/SKILL.md) skill automates all release checks and prepares staging for **User-Action Gate 3 (Toolkit Publishing)**:

1. **Atomic Semantic Version64 Bumping**: Increments version numbers and atomically encodes the 64-bit integer across `Mods/<UUID>/meta.lsx`, `Projects/<UUID>/meta.lsx`, and synchronizes the version in `my_mods/<slug>/README.md` via `bg3 mod bump-version --mod <slug> --patch` (`scripts/management/bump_mod_version.py`).
2. **Localization Pruning & Binary Compilation**: Prunes unused string handles and compiles `English/<ModName>.xml` into a binary `.loca` file via `bg3 mod sync-localization --mod <slug> --prune --compile` (`scripts/diagnostics/sync_localization.py`).
3. **Strict Linting & Conflict Gate**: Runs zero-tolerance validation (`bg3 mod validate --mod <slug> --strict`) and library collision audits (`bg3 mod conflict --candidate <slug> --against-library`).
4. **mod.io HTML Description Rendering**: Converts `my_mods/<ModSlug>/README.md` into GitHub-Flavored Markdown HTML via `bg3 mod render-description --mod <slug> --write` (`scripts/management/render_modio_description.py`), generating `modio_description.html` formatted for storefront display.
5. **Data/ Staging for User-Action Gate 3 & Optional Standalone Package**:
   - Stages loose development files and compiled binary `.loca` into `<Game>/Data/` via `bg3 mod sync-data --mods <slug>` (`scripts/packaging/sync_game_data.py`).
   - Official mod.io publication in the Baldur's Gate 3 Toolkit (`Glasses.exe`) directly consumes loose development files staged in `<Game>/Data/` (`Data/Editor/Mods/<ModName>/`, `Data/Projects/<ModName>/`, and `Data/Public/<ModName>/`)—it does not consume `.pak` archives.
   - Optionally packages a standalone LSPK v18 release `.pak` in `dist/<ModSlug>.pak` via `bg3 mod pack --mod <slug> --out dist/<slug>.pak` strictly for Nexus Mods or manual archive sharing.
6. **User-Action Gate 3 (Toolkit Publishing) & Stage 5 Handoff**:
   Guides the author through the manual publishing steps in `Glasses.exe` (Mod Project Manager -> paste `modio_description.html` -> click Publish Mod). Once publication is confirmed on mod.io, transitions to **Stage 5: Post-Release** (`/bg3-post-release <slug>`).

---

## 6. Stage 5: Post-Release Profile Management & Environment Teardown (`/bg3-post-release`)

After publishing through the Toolkit (**User-Action Gate 3**), manage storefront governance and transition the workspace to consumer subscriber mode:

```text
/bg3-post-release arcane-blade
```

The [`bg3-post-release`](../.agents/skills/bg3-post-release/SKILL.md) skill governs post-release operations across two critical phases:

### Phase 5A: Storefront Governance via REST API
1. **Pre-Flight Publication Check**: Asserts that the mod has been published via `Glasses.exe` (User-Action Gate 3) before making API calls, as the mod.io REST API updates metadata for existing profiles but cannot create new mod entries or upload `.pak` binaries.
2. **Tag Inspection & Suggestion**: Fetches official game-approved tags from mod.io and inspects `my_mods/<ModSlug>/README.md` to recommend relevant tags (e.g. `Equipment`, `Weapons`, `Classes`).
3. **Interactive 2-Stage Preview Gate**: Displays proposed metadata changes, tags to add, community options (comments, dependents, collections), non-commercial credit permissions, and public visibility (`visible=1`). **No writes occur without explicit confirmation.**
4. **REST API Synchronization**: Updates the live profile on mod.io via `bg3 modio update-metadata --mod <slug> --tags "..." --confirm` (`scripts/management/modio_update_metadata.py`) and provides direct links to the public profile and admin settings.

### Phase 5B: Mandatory Development Environment Teardown & Subscriber Verification
Switching from developer authoring mode to consumer subscriber mode is essential to prevent Patch 7 UUID conflicts, third-party mod warnings, and multiplayer checksum mismatches:
1. **Mandatory Local Teardown**:
   - Purge loose development files from `<Game>/Data/`:
     ```bash
     python3 scripts/bg3.py mod sync-data --clean-mod <slug> --json
     ```
   - Delete local test `.pak` from `AppData/Mods/`:
     ```bash
     python3 scripts/bg3.py mod pack --mod <slug> --clean-local --json
     ```
   - Disable local mod entry in `modsettings.lsx`:
     ```bash
     python3 scripts/bg3.py loadorder --disable <slug> --json
     ```
2. **Consumer Subscriber Live Verification**:
   The author launches Baldur's Gate 3, opens the in-game Mod Manager, subscribes to the live published mod on mod.io, enables it in load order, and verifies clean download and game launch as an official subscriber.

---

## 7. Skill-to-Script Reference Mapping

The autonomous agent skills invoke deterministic Python automation scripts from `scripts/` to execute low-level operations.

| Lifecycle Stage | Autonomous Skill | Underlying Script Library & CLI Command | Documentation |
| :--- | :--- | :--- | :--- |
| **Stage 1: Creation** | [`bg3-create-mod`](../.agents/skills/bg3-create-mod/SKILL.md) | `scripts/authoring/create_mod_scaffold.py` (`bg3 mod create`)<br>`scripts/authoring/scaffold_stat_entry.py` (`bg3 scaffold stat`)<br>`scripts/authoring/scaffold_progression_node.py` (`bg3 scaffold progression`)<br>`scripts/authoring/scaffold_root_template.py` (`bg3 scaffold root-template`)<br>`scripts/authoring/inject_treasure_table.py` (`bg3 mod inject-treasure`)<br>`scripts/authoring/add_mod_dependency.py` (`bg3 mod add-dependency`)<br>`scripts/diagnostics/validate_mod.py` (`bg3 mod validate`)<br>`scripts/diagnostics/sync_localization.py` (`bg3 mod sync-localization --check`)<br>`scripts/diagnostics/check_mod_conflicts.py` (`bg3 mod conflict --against-library`) | [FEATURES.md § 3.2](FEATURES.md#32-authoring--scaffolding-tools-scriptsauthoring) |
| **Stage 2: Diagnostics & Toolkit Staging** | [`bg3-diagnose-mod`](../.agents/skills/bg3-diagnose-mod/SKILL.md) | `scripts/diagnostics/validate_mod.py` (`bg3 mod validate`)<br>`scripts/packaging/sync_game_data.py` (`bg3 mod sync-data`)<br>`scripts/diagnostics/diagnose_toolkit_logs.py` (`bg3 mod diagnose-logs`) | [FEATURES.md § 3.3](FEATURES.md#33-diagnostics--auditing-tools-scriptsdiagnostics) |
| **Stage 3: Testing** | [`bg3-test-mod`](../.agents/skills/bg3-test-mod/SKILL.md) | `scripts/packaging/sync_game_data.py` (`bg3 mod sync-data --clean-mod`)<br>`scripts/packaging/pack_mod_pak.py` (`bg3 mod pack --publish-local`)<br>`scripts/management/manage_load_order.py` (`bg3 loadorder --enable --with-deps --isolate`)<br>`scripts/diagnostics/inspect_save_game.py` (`bg3 mod inspect-save`) | [FEATURES.md § 3.4–3.5](FEATURES.md#34-packaging--deployment-tools-scriptspackaging) |
| **Stage 4: Release Prep** | [`bg3-release-prep`](../.agents/skills/bg3-release-prep/SKILL.md) | `scripts/management/bump_mod_version.py` (`bg3 mod bump-version`)<br>`scripts/diagnostics/sync_localization.py` (`bg3 mod sync-localization --prune --compile`)<br>`scripts/diagnostics/validate_mod.py` (`bg3 mod validate --strict`)<br>`scripts/diagnostics/check_mod_conflicts.py` (`bg3 mod conflict --against-library`)<br>`scripts/management/render_modio_description.py` (`bg3 mod render-description`)<br>`scripts/packaging/sync_game_data.py` (`bg3 mod sync-data`)<br>`scripts/packaging/pack_mod_pak.py` (`bg3 mod pack --out dist/<slug>.pak`) | [FEATURES.md § 3.3–3.5](FEATURES.md#35-management--load-order-tools-scriptsmanagement) |
| **Stage 5: Post-Release & Teardown** | [`bg3-post-release`](../.agents/skills/bg3-post-release/SKILL.md) | `scripts/management/modio_update_metadata.py` (`bg3 modio update-metadata`)<br>`scripts/management/render_modio_description.py` (`bg3 mod render-description`)<br>`scripts/packaging/sync_game_data.py` (`bg3 mod sync-data --clean-mod`)<br>`scripts/packaging/pack_mod_pak.py` (`bg3 mod pack --clean-local`)<br>`scripts/management/manage_load_order.py` (`bg3 loadorder --disable`) | [FEATURES.md § 3.5](FEATURES.md#35-management--load-order-tools-scriptsmanagement) |

