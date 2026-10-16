# Features & Functionality Guide

This document details the core technical features, autonomous agent skills, and deterministic automation tooling available in the **Baldur's Gate 3 Mod Studio & Mod.io Toolkit**.

---

## 1. Technical Features & Architecture Overview

The workspace combines autonomous AI orchestration with deterministic Python automation to streamline every stage of the _Baldur's Gate 3_ modding lifecycle—from documenting the community you have installed to authoring custom subclasses, gear, and spells.

### Key Technical Capabilities

- **Zero-Dependency Automation Engine**:
  All 27 studio tools are implemented strictly using the **Python 3.10+ Standard Library** (`zlib`, `struct`, `xml.etree.ElementTree`, `urllib.request`). They require zero virtual environments, third-party packages (`pip`), or external compilers.
- **Pure-Python LSPK v18 Binary Packaging (`pack_mod_pak.py`)**:
  Builds uncorrupted Larian LSPK v18 package archives with custom zlib compression and binary headers directly on Linux, WSL, or Windows—bypassing the need for Windows-exclusive `LSLib` or `wine`.
- **Larian 64-bit Version Encoding (`Version64`)**:
  Calculates and updates Larian-compliant 64-bit unsigned integer version tags across `meta.lsx` and game profiles:
  $$\text{Version64} = (\text{major} \ll 55) \mid (\text{minor} \ll 47) \mid (\text{revision} \ll 31) \mid \text{build}$$
- **Larian XML Structure Engine (`*.lsx` & `*.xml`)**:
  Generates and parses standard Larian v4.8 XML structures, handles deterministic UUIDv4 generation, automatically allocates localization string handles in `Localization/English/*.xml`, and scaffolds `_merged.lsx` RootTemplates with valid 3D presets.
- **Sub-10ms Mod Database Query Engine (`query_mod_database.py`)**:
  Indexes over 2,200 cataloged community mod items, passives, spells, and boosts. Provides fuzzy search, slot filtering, and handle lookups in milliseconds.
- **Idempotent Differential Game Synchronization (`sync_game_data.py`)**:
  Selectively mirrors source mod files from `my_mods/<ModSlug>/` to your `Baldurs Gate 3/.../Data/` directory. Features SHA/timestamp caching to prevent redundant disk I/O and an optional file watcher (`--watch`) for instant hot-reloading during Toolkit authoring.
- **Mod.io REST Integration Suite**:
  Automates mod discovery, platform-tag filtering (`windows`, `mac`, `playstation_5`, `xboxseries`), archive extraction, and catalog synchronization using personal mod.io API keys and access tokens.
- **Cost & Token Optimization Protocols**:
  - Background subagent workers run on lightweight models (`"Model": "flash"`) to reduce token costs by 80%–90%.
  - High-speed discovery hub (`scripts/tools.py`) emits compact manifests (`--json`) saving up to 83.5% tokens during automated AI routing.
  - Theorycrafting generators follow an **Artifact-First** protocol, streaming high-volume progression matrices directly to disk (`build_guides/`) to avoid context clutter.

---

## 2. Autonomous Agent Skills (Slash Commands)

Autonomous skills residing in [`.agents/skills/`](.agents/skills/) allow developers to trigger end-to-end workflows via natural language slash commands.

| Slash Command                   | Skill                                                                                  | Category       | Primary Function                                                           |
| :------------------------------ | :------------------------------------------------------------------------------------- | :------------- | :------------------------------------------------------------------------- |
| `/bg3_create_mod`               | [`bg3_create_mod`](.agents/skills/bg3_create_mod/SKILL.md)                             | Stage 1        | Mod creation orchestrator: scaffolding, authoring, and read-only validation.|
| `/bg3_diagnose_mod`             | [`bg3_diagnose_mod`](.agents/skills/bg3_diagnose_mod/SKILL.md)                         | Stage 2        | Two-phase diagnostics: 2A static checks + 2B game sync & Toolkit logs.      |
| `/bg3_test_mod`                 | [`bg3_test_mod`](.agents/skills/bg3_test_mod/SKILL.md)                                 | Stage 3        | In-game testing: local `.pak` deploy, load order activation, save audits.  |
| `/bg3_release_prep`             | [`bg3_release_prep`](.agents/skills/bg3_release_prep/SKILL.md)                         | Stage 4        | Release prep: atomic version bump, strict lint, HTML render, dist `.pak`.  |
| `/bg3_post_release`             | [`bg3_post_release`](.agents/skills/bg3_post_release/SKILL.md)                         | Stage 5        | Post-release: mod.io API metadata, tag preview, permissions, visibility.  |
| `/bg3_manage_load_order`        | [`bg3_manage_load_order`](.agents/skills/bg3_manage_load_order/SKILL.md)               | Management     | Natural language inspection, ordering, and activation in `modsettings.lsx`.|
| `/bg3_check_mod_conflicts`      | [`bg3_check_mod_conflicts`](.agents/skills/bg3_check_mod_conflicts/SKILL.md)           | Compatibility  | Evaluates stat collisions and console load order compatibility.            |
| `/bg3_create_modio_collection`  | [`bg3_create_modio_collection`](.agents/skills/bg3_create_modio_collection/SKILL.md)   | Community      | Creates or updates public mod.io collections from `mods/library.md`.       |
| `/bg3_query_gear`               | [`bg3_query_gear`](.agents/skills/bg3_query_gear/SKILL.md)                             | Library        | Interactive advisor querying cataloged BiS mod items and spells.           |
| `/bg3_search_mods`              | [`bg3_search_mods`](.agents/skills/bg3_search_mods/SKILL.md)                           | Discovery      | Searches mod.io with platform filters and checks for conflicts.            |
| `/bg3_document_mods`            | [`bg3_document_mods`](.agents/skills/bg3_document_mods/SKILL.md)                       | Documentation  | Concurrently downloads, unpacks, and catalogs mod batches.                 |
| `/bg3_document_single_mod`      | [`bg3_document_single_mod`](.agents/skills/bg3_document_single_mod/SKILL.md)           | Documentation  | Extracts, inspects, and catalogs a single mod archive.                     |
| `/bg3_update_mod_documentation` | [`bg3_update_mod_documentation`](.agents/skills/bg3_update_mod_documentation/SKILL.md) | Maintenance    | Checks tracked mods for upstream updates and refreshes specs.              |
| `/bg3_update_single_mod`        | [`bg3_update_single_mod`](.agents/skills/bg3_update_single_mod/SKILL.md)               | Maintenance    | Updates documentation and assets for an individual mod.                    |
| `/bg3_create_build_guide`       | [`bg3_create_build_guide`](.agents/skills/bg3_create_build_guide/SKILL.md)             | Theorycrafting | Builds high-end Level 20 build guides pairing mod items with vanilla gear. |
| `/grill-me`                     | [`grill-me`](.agents/skills/grill-me/SKILL.md)                                         | Interview      | Interactive design-tree clarification interview before planning/coding.    |

---

### Detailed Skill Descriptions & Example Prompts

#### 1. `/bg3_create_mod` (Stage 1: Creation)

Orchestrates mod authoring in `my_mods/<ModSlug>/`. Conducts an interactive `/grill-me` interview, generates directories, creates UUIDs and `Version64` tags, allocates localization handles, authors stats and RootTemplates, and executes read-only validation without touching game directories.

- **Example Prompt**:
  ```text
  /bg3_create_mod Create a rogue subclass named Shadowblade with psychic sneak attack bonuses and a custom dagger.
  ```

#### 2. `/bg3_diagnose_mod` (Stage 2: Diagnostics & Toolkit Sync)

Acts as an autonomous mod doctor with a two-phase protocol: Phase 2A runs static pre-flight checks, syncs assets and compiled binary `.loca` to `<Game>/Data/`, and directs Toolkit (`Glasses.exe`) log generation; Phase 2B triages runtime logs, applies automated fixes, and loops back to Phase 2A until clean before offering Stage 3 testing.

- **Example Prompt**:
  ```text
  /bg3_diagnose_mod Diagnose my_mods/shadowblade and check for any Toolkit log errors.
  ```

#### 3. `/bg3_test_mod` (Stage 3: In-Game Testing)

Features a two-tier progressive gating architecture: Phase 3A builds a local test `.pak` (`pack_mod_pak.py --publish-local`), activates the mod alongside declared prerequisites (`manage_load_order.py --enable <slug> --with-deps`), and guides clean-room in-game functional verification. Phase 3B is an opt-in gate for multi-mod load order optimization (`--validate`) and campaign save-game audits (`inspect_save_game.py`) before handing off to Stage 4.

- **Example Prompt**:
  ```text
  /bg3_test_mod shadowblade
  ```

#### 4. `/bg3_release_prep` (Stage 4: Release Preparation)

Automates pre-publication verification: executes atomic semantic version bumping across `meta.lsx` and `README.md`, strict validation, localization pruning/compiling, GFM HTML description rendering (`render_modio_description.py`), final `Data/` sync, and distribution `.pak` packaging.

- **Example Prompt**:
  ```text
  /bg3_release_prep shadowblade
  ```

#### 5. `/bg3_post_release` (Stage 5: Post-Release Publishing)

Updates a published mod's mod.io profile metadata via the REST API. Features a 2-stage preview + explicit approval workflow, fetches approved tags, validates descriptions, updates non-commercial permissions and visibility, and provides direct admin links.

- **Example Prompt**:
  ```text
  /bg3_post_release shadowblade
  ```

#### 6. `/bg3_manage_load_order`

Inspects, activates, disables, or reorders mods within the player's active profile `modsettings.lsx` via natural language, verifying base game root integrity (`GustavDev` / `GustavX`).

- **Example Prompt**:
  ```text
  /bg3_manage_load_order Check my current load order and enable shadowblade after UnlockLevelCurve.
  ```

#### 7. `/bg3_check_mod_conflicts`

Performs static conflict and collision analysis between candidate mods and existing library mods, identifying overlapping stat entries, root templates, or unsupported native DLLs.

- **Example Prompt**:
  ```text
  /bg3_check_mod_conflicts Check if candidate mod 51234 conflicts with any of my installed mods in mods/library.md.
  ```

#### 8. `/bg3_create_modio_collection`

Creates or updates public mod.io collections from cataloged mods in `mods/library.md`, verifying numeric mod IDs and game ID `6715` with dry-run previews before writing.

- **Example Prompt**:
  ```text
  /bg3_create_modio_collection Create a public collection of essential level 13-20 mods.
  ```

#### 9. `/bg3_query_gear`

Advises on Best-in-Slot (BiS) gear, stat boosts, spells, and passives across the local community catalog. Translates natural language requests into instant database queries.

- **Example Prompt**:
  ```text
  /bg3_query_gear Find the best modded rings and cloaks for an Arcane Trickster focusing on Spell Save DC and critical hits.
  ```

#### 10. `/bg3_search_mods`

Searches mod.io with natural language and platform filters (PC, PlayStation 5, Xbox Series X|S). Pre-filters already tracked mods and evaluates candidates for potential collisions.

- **Example Prompt**:
  ```text
  /bg3_search_mods inventory management mods compatible with console
  ```

#### 9. `/bg3_check_mod_conflicts`

Performs static conflict and collision analysis between candidate mods and existing library mods, identifying overlapping stat entries, root templates, or unsupported native DLLs.

- **Example Prompt**:
  ```text
  /bg3_check_mod_conflicts Check if candidate mod 51234 conflicts with any of my installed mods in mods/library.md.
  ```

#### 10. `/bg3_update_mod_documentation`

Checks tracked community mods against remote mod.io releases and dispatches concurrent workers to refresh outdated documentation and database indexes.

- **Example Prompt**:
  ```text
  /bg3_update_mod_documentation ancient-armory
  ```

#### 11. `/bg3_update_single_mod`

Worker skill that fetches the latest release details for an individual mod, re-extracts the `.pak` archive if a new version is detected, and updates the local spec.

- **Example Prompt**:
  ```text
  /bg3_update_single_mod 50421
  ```

#### 12. `/bg3_create_build_guide`

Designs Level 1–20 theorycrafted character builds combining `UnlockLevelCurve`, modded BiS gear, feat selections, and mathematical Turn 1 combat sequences (DPR calculation).

- **Example Prompt**:
  ```text
  /bg3_create_build_guide Create a Level 20 Warlock/Sorcerer focused on maximizing Eldritch Blast usage and damage riders
  ```

#### 13. `/grill-me`

Conducts an interactive, branching interview using multiple-choice prompts to clarify design intent, balance constraints, and dependencies before authoring code or plans.

- **Example Prompt**:
  ```text
  /grill-me Grill me on the mechanics and balance constraints before we start authoring the Spellsword class.
  ```

---

## 3. Automation Scripts Reference (`scripts/` & `setup.sh`)

All studio scripts are located in [`scripts/`](scripts/) and registered in [`scripts/registry.json`](scripts/registry.json). They support command-line arguments and `--json` output for automated tooling pipelines.

### Setup & Discovery Hub

#### `setup.sh`

- **Location**: `setup.sh`
- **Purpose**: POSIX bootstrap script. Validates that Python 3.10+ is present in the system `$PATH` and delegates execution to `scripts/setup_environment.py`.
- **Usage**: `./setup.sh [--non-interactive] [--skip-steam]`

#### `scripts/tools.py`

- **Command Alias**: `tools`
- **Category**: Hub
- **Purpose**: Centralized discovery, search, info inspection, verification, and dispatch router for all 27 studio tools.
- **Key Flags**:
  - `--search <query>`: Natural language semantic and keyword search across tools.
  - `--info <alias>`: Emits full CLI schema, arguments, and options for a tool.
  - `--list`: Lists all registered tools (supports `--category <name>` and compact `--json`).
  - `--verify`: Runs automated integrity verification across registry, scripts, and skills.
  - `run <alias> [args...]`: Dispatches execution of any tool via its alias.
- **Usage**: `python3 scripts/tools.py --search "stat handles"`

---

### Authoring & Scaffolding Tools

#### `scripts/create_mod_scaffold.py`

- **Command Alias**: `scaffold-mod`
- **Purpose**: Generates the complete Larian directory tree (`Mods/`, `Projects/`, `Public/`, `Localization/`), calculates `Version64`, allocates UUIDs, and creates a default 512x512 project thumbnail.
- **Usage**: `python3 scripts/create_mod_scaffold.py --name <ModName> [--slug <slug>] [--unlock-level-curve] [--json]`

#### `scripts/scaffold_stat_entry.py`

- **Command Alias**: `scaffold-stat`
- **Purpose**: Appends new stats (`Weapon`, `Armor`, `SpellData`, `PassiveData`, `StatusData`) to `Public/<Mod>/Stats/Generated/Data/*.txt` and registers localized DisplayName and Description handles in `Localization/English/*.xml`.
- **Usage**: `python3 scripts/scaffold_stat_entry.py --mod <ModName> --type Weapon --name MAG_ShadowDagger --display-name "Shadow Dagger" --description "A blade that strikes from shadows"`

#### `scripts/scaffold_progression_node.py`

- **Command Alias**: `scaffold-progression`
- **Purpose**: Scaffolds and merges Larian v4.8 XML Progression and `SpellLists.lsx` nodes for class or subclass leveling, automatically resolving `TableUUID` associations.
- **Usage**: `python3 scripts/scaffold_progression_node.py --mod <ModName> --class Rogue --subclass Shadowblade --level 3`

#### `scripts/scaffold_root_template.py`

- **Command Alias**: `scaffold-template`
- **Purpose**: Binds a stat entry to a 3D GameObject RootTemplate in `Public/<Mod>/RootTemplates/_merged.lsx`, linking collision, visual meshes, and physics presets.
- **Usage**: `python3 scripts/scaffold_root_template.py --mod <ModName> --item MAG_ShadowDagger --visual-preset greatsword`

#### `scripts/inject_treasure_table.py`

- **Command Alias**: `inject-drop`
- **Purpose**: Injects custom items into world drop containers (Tutorial Chest, Camp Chest, or early Act 1 vendors) via `TreasureTable.txt` without modifying base game story files.
- **Usage**: `python3 scripts/inject_treasure_table.py --mod <ModName> --item MAG_ShadowDagger --container tutorial_chest`

#### `scripts/scaffold_icon_uvs.py`

- **Command Alias**: `scaffold-icons`
- **Purpose**: Computes normalized UV texture atlas coordinates and generates `GUI/Icons.lsx` entries for custom ability or item icons.
- **Usage**: `python3 scripts/scaffold_icon_uvs.py --mod <ModName> --atlas-size 2048 --icon-size 64`

#### `scripts/generate_compat_patch.py`

- **Command Alias**: `compat-patch`
- **Purpose**: Generates standalone compatibility patches or Compatibility Framework (`CF`) JSON/LSX configurations between two mods that modify colliding tables.
- **Usage**: `python3 scripts/generate_compat_patch.py --mod1 <ModA> --mod2 <ModB> --output my_mods/Patch_ModA_ModB`

---

### Packaging & Deployment Tools

#### `scripts/pack_mod_pak.py`

- **Command Alias**: `pack-pak`
- **Purpose**: Pure-Python LSPK v18 packager. Compresses mod files using zlib and writes binary headers directly to `.pak` format without third-party dependencies.
- **Usage**: `python3 scripts/pack_mod_pak.py --mod my_mods/Shadowblade --output dist/Shadowblade.pak`

#### `scripts/sync_game_data.py`

- **Command Alias**: `sync-game`
- **Purpose**: Performs idempotent synchronization of mod source trees from `my_mods/` to Steam `Baldurs Gate 3/Data/`. Supports continuous file watching with `--watch` and targeted loose data cleanup with `--clean-mod`.
- **Usage**: `python3 scripts/sync_game_data.py --mod Shadowblade [--watch]`

---

### Diagnostics & Validation Tools

#### `scripts/validate_mod.py`

- **Command Alias**: `validate`
- **Purpose**: Static linter and validator. Verifies LSX XML well-formedness, checks UUID formats, detects missing localization string handles, and validates directory structures.
- **Usage**: `python3 scripts/validate_mod.py --mod my_mods/Shadowblade`

#### `scripts/check_mod_conflicts.py`

- **Command Alias**: `check-conflicts`
- **Purpose**: Analyzes mod packages for entry collisions (duplicate stats, identical RootTemplate names) and flags console-incompatible files (such as native `.dll` files).
- **Usage**: `python3 scripts/check_mod_conflicts.py --candidate <ModSlug> --against-library`

#### `scripts/sync_localization.py`

- **Command Alias**: `sync-loca`
- **Purpose**: Audits localization XML files, prunes orphaned string handles, compiles binary `.loca` tables, and syncs multi-language XMLs.
- **Usage**: `python3 scripts/sync_localization.py --mod <ModSlug> [--prune] [--compile] [--json]`

#### `scripts/diagnose_toolkit_logs.py`

- **Command Alias**: `diagnose-logs`
- **Purpose**: Parses BG3 Toolkit (`Glasses.exe`) message logs, filters by subsystem (Boosts, Stats, Thoth, Osiris), correlates errors to workspace mods, or streams active sessions with `--follow`.
- **Usage**: `python3 scripts/diagnose_toolkit_logs.py --mod <ModSlug> --severity warning --json`

#### `scripts/inspect_save_game.py`

- **Command Alias**: `inspect-save`
- **Purpose**: Extracts active mod UUIDs and load orders from `.lsv` save files (Zstandard and LSOF v7 LZ4-frame decoding) and audits them against the player's active `modsettings.lsx`.
- **Usage**: `python3 scripts/inspect_save_game.py --audit --json`

---

### Management & Publication Tools

#### `scripts/manage_load_order.py`

- **Command Alias**: `load-order`
- **Purpose**: Parses, modifies, and validates the player's `modsettings.lsx`. Enables, disables, orders, and audits active mods.
- **Usage**: `python3 scripts/manage_load_order.py --enable <ModSlug> [--order <idx>] --validate --json`

#### `scripts/bump_mod_version.py`

- **Command Alias**: `bump-version`
- **Purpose**: Increments semantic versions (`--major`, `--minor`, `--patch`) and re-encodes 64-bit uint `Version64` across all `meta.lsx` instances while updating `README.md`.
- **Usage**: `python3 scripts/bump_mod_version.py --mod <ModSlug> --patch --json`

#### `scripts/render_modio_description.py`

- **Command Alias**: `render-description`
- **Purpose**: Renders the mod's root `README.md` as GFM-table-formatted `modio_description.html` for publishing.
- **Usage**: `python3 scripts/render_modio_description.py --mod <ModSlug> --write --json`

#### `scripts/modio_update_metadata.py`

- **Command Alias**: `post-release`
- **Purpose**: Previews and applies approved mod.io metadata, tags, non-commercial permissions, and public visibility via REST API; writes require explicit `--confirm`.
- **Usage**: `python3 scripts/modio_update_metadata.py --mod <ModSlug> --tags "Classes,Spells" --confirm --json`

#### `scripts/modio_create_collection.py`

- **Command Alias**: `modio-collection`
- **Purpose**: Creates or updates public mod.io collections from cataloged mods in `mods/library.md`, checking numeric mod IDs and game ID `6715`.
- **Usage**: `python3 scripts/modio_create_collection.py --dry-run`

#### `scripts/setup_environment.py`

- **Command Alias**: `setup-env`
- **Purpose**: Interactive/non-interactive configuration wizard. Validates Steam installation paths, Larian AppData directories, and mod.io API keys in `.env`.
- **Usage**: `python3 scripts/setup_environment.py [--non-interactive] [--json]`

---

### Library & Mod.io Search Tools

#### `scripts/query_mod_database.py`

- **Command Alias**: `query-db`
- **Purpose**: High-speed database engine searching cataloged items, spells, passives, and boosts. Supports filtering by equipment slot, rarity, and keywords.
- **Usage**: `python3 scripts/query_mod_database.py --slot Ring --search "Spell Save DC" --compact`

#### `scripts/update_library_catalog.py`

- **Command Alias**: `update-catalog`
- **Purpose**: Aggregates individual mod specs in `mods/*/README.md` into the master index at `mods/library.md`.
- **Usage**: `python3 scripts/update_library_catalog.py`

#### `scripts/modio_search.py`

- **Command Alias**: `modio-search`
- **Purpose**: Queries the mod.io REST API with platform tags (`windows`, `mac`, `playstation_5`, `xboxseries`) and natural language terms.
- **Usage**: `python3 scripts/modio_search.py --query "transmog" --platform windows`

#### `scripts/modio_sync.py`

- **Command Alias**: `modio-sync`
- **Purpose**: Connects via user PAT to synchronize all subscribed mods from mod.io into the local `mods/` directory.
- **Usage**: `python3 scripts/modio_sync.py`

#### `scripts/modio_update.py`

- **Command Alias**: `modio-update`
- **Purpose**: Compares local mod versions against remote mod.io releases and reports or triggers updates.
- **Usage**: `python3 scripts/modio_update.py [--all | --mod <slug>]`

#### `scripts/modio_extract.py`

- **Command Alias**: `modio-extract`
- **Purpose**: Unpacks mod archives (`.pak` or `.zip`), extracts Larian XML/TXT files, and outputs structured markdown documentation for `mods/<slug>/README.md`.
- **Usage**: `python3 scripts/modio_extract.py --pak <PathToPak> --slug <mod-slug>`

---

### Theorycrafting Tools

#### `scripts/simulate_build_synergy.py`

- **Command Alias**: `simulate-build`
- **Purpose**: Simulates multiclass progression, spell slot matrices, Spell Save DC ceilings, and Turn 1 combat damage per round (DPR) sequences.
- **Usage**: `python3 scripts/simulate_build_synergy.py --classes "Warlock=2,Sorcerer=18" --iterations 1000`
