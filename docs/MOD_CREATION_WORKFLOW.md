# Baldur's Gate 3 Mod Creation Workflow Guide

This guide walks through creating, authoring, diagnosing, testing, and publishing custom *Baldur's Gate 3* mods in this workspace.

---

## 1. Chat-First Development & Shift-Left Architecture

Development in this studio follows two foundational principles:

1. **Chat First**: Rather than manually executing command-line scripts, you drive every stage of mod creation conversationally through specialized slash commands (`/bg3_create_mod`, `/bg3_diagnose_mod`, `/bg3_test_mod`, `/bg3_release_prep`, `/bg3_post_release`). Autonomous agent skills orchestrate subagents, manage progressive review gates, and invoke deterministic Python scripts under the hood.
2. **Shift Left + Loopback**: Potential bugs, XML/LSX structural errors, broken localization handles, and community stat collisions are caught as early as possible—statically in Phase 2A and via BG3 Toolkit runtime logs in Phase 2B—long before packaging or loading into a full game campaign. If gameplay anomalies appear during in-game testing, the workflow provides an instant loopback to diagnostics.

### 5-Stage Shift-Left & Loopback Lifecycle

```mermaid
flowchart TD
    S1["Stage 1: Creation (/bg3_create_mod)
    • /grill-me interview & specification plan
    • Scaffolding & parallel subagents
    • Read-only smoke check on my_mods/<slug>/"]
    
    S2["Stage 2: Diagnostics (/bg3_diagnose_mod)
    • Phase 2A: Static pre-flight, Data/ sync & Toolkit launch
    • Phase 2B: Runtime log triage, auto-fixes & verification loop"]
    
    S3["Stage 3: In-Game Testing (/bg3_test_mod)
    • Phase 3A: Clean-room test with dependency isolation
    • Phase 3B: Multi-mod campaign integration & save audit (optional)
    • User in-game verification & loopback/release gate"]
    
    S4["Stage 4: Release Preparation (/bg3_release_prep)
    • Semantic version bump & README sync
    • Localization prune & binary .loca compilation
    • Strict linting & mod.io HTML description render
    • Final Data/ sync & dist/<slug>.pak build"]
    
    S5["Stage 5: Post-Release (/bg3_post_release)
    • mod.io REST API profile metadata sync
    • 2-stage tag preview + confirmation"]
    
    S1 -->|Stage 1 Gate| S2
    S2 -->|Stage 2 Gate| S3
    S3 -->|Testing Passed| S4
    S3 -.->|Issues Found (Loopback)| S2
    S4 -->|Publish in Toolkit| S5
```

> [!NOTE]
> For in-depth CLI options, script arguments, and low-level technical specifications for each automation script, refer to [FEATURES.md](FEATURES.md).

---

## 2. Stage 1: Autonomous Creation (`/bg3_create_mod`)

Trigger mod creation conversationally by describing your concept or invoking the slash command:

```text
/bg3_create_mod "A finesse longsword for Eldritch Knights scaling with INT"
```

The [`bg3_create_mod`](../.agents/skills/bg3_create_mod/SKILL.md) skill orchestrates the entire creation pipeline across five distinct phases:

### Step 1: Design Interview (`grill-me` Protocol)
The orchestrator immediately initiates a structured interview to resolve design branches:
- Progression levels (Standard 1–12 vs. Level 20 UnlockLevelCurve support)
- Weapon/armor rarity, properties, damage dice, and enchantments
- Associated passive features, spells, and resource costs
- Required dependencies (e.g., `CompatibilityFramework`, `CommunityLibrary`)

### Step 2: Mod Specification & Interactive Approval Gate
The agent synthesizes decisions into a technical mod specification plan. **Execution pauses until you explicitly approve the plan** via the interactive UI prompt.

### Step 3: Workspace Scaffolding
Upon approval, the agent generates the standardized directory hierarchy in `my_mods/<ModSlug>/`:
- `Projects/<UUID>/meta.lsx` & `Mods/<UUID>/meta.lsx` (with auto-generated deterministic UUIDv4 and Larian `Version64` tags)
- `Public/<UUID>/Stats/Generated/Data/` (for engine stats and spells)
- `Public/<UUID>/RootTemplates/_merged.lsx` (for 3D GameObject templates)
- `Localization/English/<ModName>.xml` (for localized text handles)
- `my_mods/<ModSlug>/README.md` (rich mod specification document)

### Step 4: Parallel Subagent Dispatch
The orchestrator launches specialized background subagents concurrently to author components in parallel:
- **Stats & Spells Specialist**: Authors stat definitions, passives, and spell entries.
- **Progression Specialist**: Configures `Progressions.lsx` and `SpellLists.lsx` if class levels or spells are added.
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

### Step 5 & 6: Smoke Gate & Progressive Handoff
A read-only validation check verifies syntax and handle consistency without altering external directories. Once verified, the agent presents a **Progressive Gate Handoff** prompting you to transition into Stage 2.

---

## 3. Stage 2: Diagnostics & Toolkit Verification (`/bg3_diagnose_mod`)

Stage 2 acts as the autonomous mod doctor, ensuring full stability before runtime testing:

```text
/bg3_diagnose_mod arcane-blade
```

The [`bg3_diagnose_mod`](../.agents/skills/bg3_diagnose_mod/SKILL.md) skill operates in two synchronized phases:

### Phase 2A: Static Pre-Flight & Game Sync
1. **Structural & Handle Audit**: Verifies that every `DisplayName` and `Description` handle referenced in stat files exists in `Localization/English/<ModName>.xml`.
2. **Library Collision Check**: Scans your candidate mod's stat entries against over 2,200 cataloged community mods in `mods/library.md` to prevent overwriting existing game or mod data.
3. **Automated Pre-Flight Fixes**: Automatically prunes orphaned localization handles and normalizes syntax errors.
4. **Idempotent Data Sync**: Synchronizes unpacked mod assets and compiled binary `.loca` files directly into your game's `Data/` directory.
5. **Toolkit Launch Prompt**: Directs you to open the mod in the official Baldur's Gate 3 Toolkit (`Glasses.exe`) to generate engine log output.

### Phase 2B: Runtime Log Diagnosis & Automated Remediation Loop
Once you confirm logs have been generated in the Toolkit:
1. The skill analyzes `Glasses.exe` diagnostic logs (`diagnose_toolkit_logs.py`), identifying missing textures, duplicate stats, or invalid boost syntax.
2. The agent proposes and applies targeted patches directly to files in `my_mods/<ModSlug>/`.
3. The skill automatically **loops back to Phase 2A** to re-verify fixes statically, repeating the cycle until logs are clean.
4. Once verified, the agent offers a handoff to Stage 3 In-Game Testing.

---

## 4. Stage 3: In-Game Testing & Verification (`/bg3_test_mod`)

Deploy and test your mod in an actual game session:

```text
/bg3_test_mod arcane-blade
```

The [`bg3_test_mod`](../.agents/skills/bg3_test_mod/SKILL.md) skill uses a progressive two-tier testing protocol:

### Phase 3A: Clean-Room / Smoke Testing (Default Fast Path)
1. **Loose File Cleanup & Local Packaging**: Cleans loose source files from `Data/` to avoid engine file locks and builds an uncorrupted test `.pak` archive (`pack_mod_pak.py --publish-local`).
2. **Isolated Load Order Activation**: Injects your mod alongside its declared dependencies into `modsettings.lsx` with clean-room isolation (`manage_load_order.py --enable <slug> --with-deps --isolate`).
3. **In-Game Verification**: You launch Baldur's Gate 3 and verify mechanics, drop rates, and tooltips on a clean save.

### Phase 3B: Multi-Mod Integration & Save Audit (Optional Gate)
For complex mods or character class overhauls:
- Validates profile load order compatibility against active third-party mods.
- Audits existing campaign save games (`inspect_save_game.py`) to confirm safe loading without missing template errors.

### The Shift Left + Loopback Trigger
If you encounter missing icons, broken passives, or unexpected interactions while playing in-game, you do not need to manually troubleshoot. Simply alert the assistant:

> *"The weapon's passive isn't applying the spellcasting modifier during combat."*

The assistant immediately **loops back to Stage 2 (`/bg3_diagnose_mod`)**, analyzes the stat inheritance, applies a fix, re-syncs, and presents a freshly packaged test `.pak` for verification.

---

## 5. Stage 4: Release Preparation (`/bg3_release_prep`)

When in-game testing is complete and verified, prepare the mod for publication:

```text
/bg3_release_prep arcane-blade
```

The [`bg3_release_prep`](../.agents/skills/bg3_release_prep/SKILL.md) skill automates all release checks:

1. **Atomic Semantic Version Bumping**: Increments version numbers in `Mods/<UUID>/meta.lsx`, `Projects/<UUID>/meta.lsx`, and `README.md` (`bump_mod_version.py --patch`).
2. **Localization Prune & Binary Compilation**: Prunes unused string handles and compiles `English/<ModName>.xml` into a binary `.loca` file.
3. **Strict Linting & Conflict Gate**: Runs zero-tolerance validation (`validate_mod.py --strict`) and library collision audits.
4. **mod.io HTML Description Rendering**: Converts `my_mods/<ModSlug>/README.md` into GitHub-Flavored Markdown HTML (`render_modio_description.py`), generating `modio_description.html` ready for storefront display.
5. **Final Game Data Sync & Distribution Archive**: Syncs final assets to `<Game>/Data/` and builds an LSPK v18 release `.pak` in `dist/<ModSlug>.pak`.

At this point, your mod can be loaded into the official Baldur's Gate 3 Toolkit and published to mod.io with one click.

---

## 6. Stage 5: Post-Release Profile Management (`/bg3_post_release`)

After uploading your `.pak` through the Toolkit, update and synchronize the public mod.io storefront profile:

```text
/bg3_post_release arcane-blade
```

The [`bg3_post_release`](../.agents/skills/bg3_post_release/SKILL.md) skill provides a 2-stage preview and approval workflow:

1. **Tag & Metadata Inspection**:
   - Fetches official mod.io allowed tags for Baldur's Gate 3.
   - Evaluates the mod's `README.md` to recommend relevant tags (e.g., `Equipment`, `Weapons`, `Classes`).
2. **Interactive Preview Gate**:
   - Displays the exact proposed changes (title, summary, tags, and rendered HTML description).
   - **No writes occur without explicit confirmation.**
3. **API Synchronization**:
   - Updates the live mod profile on mod.io via the REST API.
   - Provides a direct link to the mod profile and admin dashboard.

---

## 7. Skill-to-Script Reference Mapping

The autonomous agent skills invoke deterministic Python automation scripts from `scripts/` to execute low-level operations.

| Lifecycle Stage | Autonomous Skill | Underlying Script Library | Documentation |
| :--- | :--- | :--- | :--- |
| **Stage 1: Creation** | [`bg3_create_mod`](../.agents/skills/bg3_create_mod/SKILL.md) | `create_mod_scaffold.py`<br>`scaffold_stat_entry.py`<br>`scaffold_progression.py`<br>`scaffold_root_template.py`<br>`inject_treasure_table.py` | [FEATURES.md § 3.1–3.4](FEATURES.md#3-automation-scripts-reference-scripts--setupsh) |
| **Stage 2: Diagnostics** | [`bg3_diagnose_mod`](../.agents/skills/bg3_diagnose_mod/SKILL.md) | `validate_mod.py`<br>`sync_localization.py`<br>`check_mod_conflicts.py`<br>`sync_game_data.py`<br>`diagnose_toolkit_logs.py` | [FEATURES.md § 3.5–3.9](FEATURES.md#3-automation-scripts-reference-scripts--setupsh) |
| **Stage 3: Testing** | [`bg3_test_mod`](../.agents/skills/bg3_test_mod/SKILL.md) | `pack_mod_pak.py`<br>`manage_load_order.py`<br>`inspect_save_game.py` | [FEATURES.md § 3.10–3.12](FEATURES.md#3-automation-scripts-reference-scripts--setupsh) |
| **Stage 4: Release Prep** | [`bg3_release_prep`](../.agents/skills/bg3_release_prep/SKILL.md) | `bump_mod_version.py`<br>`sync_localization.py`<br>`validate_mod.py`<br>`render_modio_description.py`<br>`pack_mod_pak.py` | [FEATURES.md § 3.13–3.17](FEATURES.md#3-automation-scripts-reference-scripts--setupsh) |
| **Stage 5: Post-Release** | [`bg3_post_release`](../.agents/skills/bg3_post_release/SKILL.md) | `modio_update_metadata.py`<br>`render_modio_description.py` | [FEATURES.md § 3.18–3.20](FEATURES.md#3-automation-scripts-reference-scripts--setupsh) |
