# Features & Functionality Guide

This document details the core technical features, autonomous agent skills, and deterministic automation tooling available in the **Baldur's Gate 3 Mod Studio & Mod.io Toolkit**.

---

## 1. Technical Features & Architecture Overview

The workspace combines autonomous AI orchestration with deterministic Python automation to streamline every stage of the _Baldur's Gate 3_ modding lifecycle—from documenting the community you have installed to authoring custom subclasses, gear, and spells.

### Key Technical Capabilities

- **Zero-Dependency Automation Engine (59 Tools across 3 Workspace Packages)**:
  All studio automation tools (and the unified `bg3` CLI entrypoint) are implemented strictly using the **Python 3.10+ Standard Library** (`zlib`, `struct`, `xml.etree.ElementTree`, `urllib.request`, `hashlib`). They require zero virtual environments, third-party packages (`pip`), or external compilers for standard runtime operation.
- **Unified 2026 CLI Suite (`bg3`)**:
  The primary entrypoint is installed to `~/.local/bin/bg3` by `setup.sh`. It exposes structured domain commands (`mod`, `loadorder`, `modio`, `scaffold`, `query`, `build`, `tools`, `env`, `run`), standardizes POSIX exit codes, and provides modern **Dual-Channel Stream Discipline**: rich, styled output on interactive terminals, and pristine, machine-parsable JSON on `stdout` when `--json` is supplied or piped.
- **XDG Base Directory Specification Compliance**:
  Adheres strictly to the XDG standard via `bg3_core.env_paths`. Secrets and configurations are stored in `$XDG_CONFIG_HOME/bg3/env` (mode `0600`), and caches resolve to `$XDG_CACHE_HOME/bg3/`. In-repo `.env` and `.cache` directories are completely eliminated. Introspectable via `bg3 env paths` and `bg3 env check`.
- **Pure-Python LSPK v18 Binary Packaging (`bg3 mod pack` / `bg3_core.lspk`)**:
  Builds uncorrupted Larian LSPK v18 package archives with custom zlib compression and binary headers directly on Linux, WSL, or Windows—bypassing the need for Windows-exclusive `LSLib` or `wine`.
- **Larian 64-bit Version Encoding (`Version64`)**:
  Calculates and updates Larian-compliant 64-bit unsigned integer version tags across `meta.lsx` and game profiles:
  $$\text{Version64} = (\text{major} \ll 55) \mid (\text{minor} \ll 47) \mid (\text{revision} \ll 31) \mid \text{build}$$
- **Larian XML Structure Engine (`*.lsx` & `*.xml`)**:
  Generates and parses standard Larian v4.8 XML structures, handles deterministic UUIDv4 generation, automatically allocates localization string handles in `Localization/English/*.xml`, and scaffolds `_merged.lsx` RootTemplates with valid 3D presets.
- **Sub-10ms Mod Database Query Engine (`bg3 query`)**:
  Indexes over 2,200 cataloged community mod items, passives, spells, and boosts. Provides fuzzy search, slot filtering, and handle lookups in milliseconds (`bg3 query`).
- **Idempotent Differential Game Synchronization (`bg3 mod sync-game`)**:
  Selectively mirrors source mod files from `my_mods/<ModSlug>/` to your `Baldurs Gate 3/.../Data/` directory. Features SHA/timestamp caching to prevent redundant disk I/O, an optional file watcher (`--watch`), and clean-up modes (`--clean-mod`).
- **Mod.io REST Integration Suite (`bg3 modio`)**:
  Automates mod discovery, platform-tag filtering (`windows`, `mac`, `playstation_5`, `xboxseries`), archive extraction, collection creation, and catalog synchronization using personal mod.io API keys and access tokens (`bg3 modio`).
- **Safe Sandboxing & Clean-Room Testing**:
  - Test dependencies are declared cleanly in `.test_deps.json` without contaminating production `meta.lsx` (`bg3 mod add-dependency <slug> --test`).
  - Clean-room load order isolation (`bg3 loadorder isolate <slug>`) temporarily disables unrelated mods in `modsettings.lsx` during verification.
  - Theorycrafting generators stream progression matrices directly to disk (`build_guides/`) outside Git.
- **Cost & Token Optimization Protocols**:
  - Background subagent workers strictly inherit the parent model (`"Model": "inherit"`) preserving complete tool and reasoning compatibility across complex workflows.
  - High-speed discovery hub (`bg3 tools`) emits compact manifests (`--json`) saving up to 83.5% tokens during automated AI routing.

---

## 2. Autonomous Agent Skills (Slash Commands)

Autonomous skills residing in [`.agents/skills/`](../.agents/skills/) allow developers to trigger end-to-end workflows via natural language slash commands.

| Slash Command                   | Skill                                                                                  | Category       | Primary Function                                                           |
| :------------------------------ | :------------------------------------------------------------------------------------- | :------------- | :------------------------------------------------------------------------- |
| `/bg3-create-mod`               | [`bg3-create-mod`](../.agents/skills/bg3-create-mod/SKILL.md)                             | Stage 1        | Autonomous creation: interview, scaffolding, concurrent subagents, static validation. |
| `/bg3-diagnose-mod`             | [`bg3-diagnose-mod`](../.agents/skills/bg3-diagnose-mod/SKILL.md)                         | Stage 2        | Toolkit staging & diagnostics: Data/ sync & .loca, User-Action Gate 1 runtime triage. |
| `/bg3-test-mod`                 | [`bg3-test-mod`](../.agents/skills/bg3-test-mod/SKILL.md)                                 | Stage 3        | Clean-room testing: Data purge, local .pak deploy, User-Action Gate 2, Dual-Track routing. |
| `/bg3-release-prep`             | [`bg3-release-prep`](../.agents/skills/bg3-release-prep/SKILL.md)                         | Stage 4        | Release staging: Version64 bump, strict lint, GFM HTML render, Data/ staging for Gate 3. |
| `/bg3-post-release`             | [`bg3-post-release`](../.agents/skills/bg3-post-release/SKILL.md)                         | Stage 5        | Storefront governance: mod.io REST API metadata/tags, dev teardown, subscriber test. |
| `/bg3-manage-load-order`        | [`bg3-manage-load-order`](../.agents/skills/bg3-manage-load-order/SKILL.md)               | Management     | Natural language inspection, ordering, and activation in `modsettings.lsx`.|
| `/bg3-check-mod-conflicts`      | [`bg3-check-mod-conflicts`](../.agents/skills/bg3-check-mod-conflicts/SKILL.md)           | Compatibility  | Evaluates stat collisions and console load order compatibility.            |
| `/bg3-create-modio-collection`  | [`bg3-create-modio-collection`](../.agents/skills/bg3-create-modio-collection/SKILL.md)   | Community      | Creates or updates public mod.io collections from `mods/library.md`.       |
| `/bg3-query-gear`               | [`bg3-query-gear`](../.agents/skills/bg3-query-gear/SKILL.md)                             | Library        | Interactive advisor querying cataloged BiS mod items and spells.           |
| `/bg3-search-mods`              | [`bg3-search-mods`](../.agents/skills/bg3-search-mods/SKILL.md)                           | Discovery      | Searches mod.io with platform filters and checks for conflicts.            |
| `/bg3-document-mods`            | [`bg3-document-mods`](../.agents/skills/bg3-document-mods/SKILL.md)                       | Documentation  | Concurrently downloads, unpacks, and catalogs mod batches.                 |
| `/bg3-document-single-mod`      | [`bg3-document-single-mod`](../.agents/skills/bg3-document-single-mod/SKILL.md)           | Documentation  | Extracts, inspects, and catalogs a single mod archive.                     |
| `/bg3-update-mod-documentation` | [`bg3-update-mod-documentation`](../.agents/skills/bg3-update-mod-documentation/SKILL.md) | Maintenance    | Checks tracked mods for upstream updates and refreshes specs.              |
| `/bg3-update-single-mod`        | [`bg3-update-single-mod`](../.agents/skills/bg3-update-single-mod/SKILL.md)               | Maintenance    | Updates documentation and assets for an individual mod.                    |
| `/bg3-create-build-guide`       | [`bg3-create-build-guide`](../.agents/skills/bg3-create-build-guide/SKILL.md)             | Theorycrafting | Builds high-end Level 20 build guides pairing mod items with vanilla gear. |
| `/grill-me`                     | `grill-me`                                                                             | Interview      | Interactive design-tree clarification interview before planning/coding.    |

---

### Detailed Skill Descriptions & Example Prompts

#### 1. `/bg3-create-mod` (Stage 1: Creation)

Orchestrates mod authoring in `my_mods/<ModSlug>/`. Conducts an interactive `/grill-me` interview to resolve design decisions, generates directories and metadata (`Version64`, UUIDv4), dispatches specialized concurrent subagents to author stats, progressions, and RootTemplates, and executes comprehensive read-only static verification (LSX/XML schema integrity, string handle parity, and library conflict pre-check) without touching external game directories or `AppData/`.

- **Example Prompt**:
  ```text
  /bg3-create-mod Create a rogue subclass named Shadowblade with psychic sneak attack bonuses and a custom dagger.
  ```

#### 2. `/bg3-diagnose-mod` (Stage 2: Diagnostics & Toolkit Staging)

Acts as an autonomous mod doctor managing **User-Action Gate 1 (Toolkit Diagnostics)**: Phase 2A asserts static workspace cleanliness, stages unpacked assets and compiled binary `.loca` into `<Game>/Data/`, and directs the author to launch the official Baldur's Gate 3 Toolkit (`Glasses.exe`); Phase 2B triages runtime logs (`messages.log`), applies targeted source fixes to `my_mods/<ModSlug>/`, and loops back to Phase 2A until clean before offering Stage 3 testing.

- **Example Prompt**:
  ```text
  /bg3-diagnose-mod Diagnose my_mods/shadowblade and check for any Toolkit log errors.
  ```

#### 3. `/bg3-test-mod` (Stage 3: Clean-Room In-Game Testing)

Governs **User-Action Gate 2 (In-Game Playtesting)** with a two-tier architecture: Phase 3A purges loose development files from `<Game>/Data/` (preventing VFS loose-file shadowing), deploys a clean local test `.pak` (`pack_mod_pak.py --publish-local`), isolates load order with declared prerequisites (`manage_load_order.py --enable <slug> --with-deps --isolate`), and guides playtesting in `bg3.exe` with **Dual-Track Defect Routing** (engine crashes route to Stage 2 diagnostics; gameplay/mechanics bugs route to Stage 1 authoring patches). Phase 3B is an opt-in gate for multi-mod load order optimization (`--validate`) and campaign save-game audits (`inspect_save_game.py`) before handing off to Stage 4.

- **Example Prompt**:
  ```text
  /bg3-test-mod shadowblade
  ```

#### 4. `/bg3-release-prep` (Stage 4: Release Preparation)

Automates pre-publication verification and staging for **User-Action Gate 3 (Toolkit Publishing)**: executes atomic semantic `Version64` bumping across `meta.lsx` and `README.md`, strict lint validation, localization pruning/compiling, GFM HTML description rendering (`render_modio_description.py`), and `<Game>/Data/` staging (where the official Toolkit directly consumes loose files for mod.io publication), with optional standalone distribution `.pak` packaging (`dist/<ModSlug>.pak`).

- **Example Prompt**:
  ```text
  /bg3-release-prep shadowblade
  ```

#### 5. `/bg3-post-release` (Stage 5: Post-Release Governance & Environment Teardown)

Governs post-publication operations following **User-Action Gate 3 (Toolkit Publishing)**: updates remote mod.io profile metadata via the REST API using a 2-stage preview and explicit approval workflow (allowed tags, non-commercial permissions, public visibility), and coordinates mandatory development environment teardown (purging loose `Data/` files, deleting local test `.pak`, disabling load order entry) to transition the developer into a clean consumer subscriber.

- **Example Prompt**:
  ```text
  /bg3-post-release shadowblade
  ```

#### 6. `/bg3-manage-load-order`

Inspects, activates, disables, or reorders mods within the player's active profile `modsettings.lsx` via natural language, verifying base game root integrity (`GustavDev` / `GustavX`).

- **Example Prompt**:
  ```text
  /bg3-manage-load-order Check my current load order and enable shadowblade after UnlockLevelCurve.
  ```

#### 7. `/bg3-check-mod-conflicts`

Performs static conflict and collision analysis between candidate mods and existing library mods, identifying overlapping stat entries, root templates, or unsupported native DLLs.

- **Example Prompt**:
  ```text
  /bg3-check-mod-conflicts Check if candidate mod 51234 conflicts with any of my installed mods in mods/library.md.
  ```

#### 8. `/bg3-create-modio-collection`

Creates or updates public mod.io collections from cataloged mods in `mods/library.md`, verifying numeric mod IDs and game ID `6715` with dry-run previews before writing.

- **Example Prompt**:
  ```text
  /bg3-create-modio-collection Create a public collection of essential level 13-20 mods.
  ```

#### 9. `/bg3-query-gear`

Advises on Best-in-Slot (BiS) gear, stat boosts, spells, and passives across the local community catalog. Translates natural language requests into instant database queries.

- **Example Prompt**:
  ```text
  /bg3-query-gear Find the best modded rings and cloaks for an Arcane Trickster focusing on Spell Save DC and critical hits.
  ```

#### 10. `/bg3-search-mods`

Searches mod.io with natural language and platform filters (PC, PlayStation 5, Xbox Series X|S). Pre-filters already tracked mods and evaluates candidates for potential collisions.

- **Example Prompt**:
  ```text
  /bg3-search-mods inventory management mods compatible with console
  ```

#### 11. `/bg3-document-mods`

Orchestrates concurrent subagents to download, unpack, validate, and document a batch of community mods from mod.io into `mods/<mod_name>/README.md` and updates `mods/library.md`.

- **Example Prompt**:
  ```text
  /bg3-document-mods 5e-spells unlocklevelcurve extra-gear
  ```

#### 12. `/bg3-document-single-mod`

Worker skill that fetches, unpacks, validates, and documents a single Baldur's Gate 3 mod from mod.io into `mods/<mod_name>/README.md` using the rich feature schema and static in-game validation.

- **Example Prompt**:
  ```text
  /bg3-document-single-mod 4166963
  ```

#### 13. `/bg3-update-mod-documentation`

Checks tracked community mods against remote mod.io releases and dispatches concurrent workers to refresh outdated documentation and database indexes.

- **Example Prompt**:
  ```text
  /bg3-update-mod-documentation ancient-armory
  ```

#### 14. `/bg3-update-single-mod`

Worker skill that fetches the latest release details for an individual mod, re-extracts the `.pak` archive if a new version is detected, and updates the local spec.

- **Example Prompt**:
  ```text
  /bg3-update-single-mod 50421
  ```

#### 15. `/bg3-create-build-guide`

Designs Level 1–20 theorycrafted character builds combining `UnlockLevelCurve`, modded BiS gear, feat selections, and mathematical Turn 1 combat sequences (DPR calculation).

- **Example Prompt**:
  ```text
  /bg3-create-build-guide Create a Level 20 Warlock/Sorcerer focused on maximizing Eldritch Blast usage and damage riders
  ```

#### 16. `/grill-me`

Conducts an interactive, branching interview using multiple-choice prompts to clarify design intent, balance constraints, and dependencies before authoring code or plans.

- **Example Prompt**:
  ```text
  /grill-me Grill me on the mechanics and balance constraints before we start authoring the Spellsword class.
  ```

---

## 3. Automation Tools & Packages Reference (`packages/bg3-*` & `setup.sh`)

All 59 canonical studio automation tools are organized into domain-specific packages within `packages/` (`bg3-core`, `bg3-authoring`, `bg3-theorycraft`) and discoverable dynamically via `bg3 tools`.

Every tool supports dual-mode execution:
1. **Unified CLI Command** (recommended): `bg3 <command> <subcommand> [flags...] [--json]`
2. **Direct Module Execution**: `uv run -m <module> [flags...]`

---

### 3.1 Unified CLI Suite & Environment (`setup.sh`, `packages/bg3-core/bg3_core/cli.py`)

#### `setup.sh`
- **Location**: `setup.sh`
- **Purpose**: POSIX bootstrap script. Validates Python 3.10+ in `$PATH`, creates symlink `~/.local/bin/bg3 -> packages/bg3-core/bg3_core/cli.py`, and launches the environment configuration wizard.
- **Usage**: `./setup.sh [--non-interactive] [--skip-steam] [--check]`

#### `packages/bg3-core/bg3_core/cli.py`
- **Command Alias**: `bg3`
- **Primary CLI**: `bg3 <command> <subcommand> [flags...] [--json]`
- **Category**: Unified Entrypoint
- **Purpose**: Root router for Baldur's Gate 3 Mod Studio. Standardizes POSIX exit codes, TTY-aware color formatting, dual-channel `--json` stream discipline, and safety confirmation guards across all domain subcommands.
- **Key Subcommands**:
  - `bg3 mod <action>`: Mod authoring, dependency management, versioning, packaging, and validation.
  - `bg3 loadorder <action>`: Active player profile (`modsettings.lsx`) inspection, activation, validation, and clean-room isolation.
  - `bg3 modio <action>`: Mod.io search, sync, extraction, updates, collections, and cataloging.
  - `bg3 scaffold <action>`: Stats, progressions, root templates, and icon atlas UV scaffolding.
  - `bg3 query`: High-speed BiS gear, spell, and mechanics database queries.
  - `bg3 build` / `bg3 sim`: Character build theorycrafting and combat simulation.
  - `bg3 tools <action>`: Tool registry discovery, search, schema inspection, and verification.
  - `bg3 env <action>`: XDG Base Directory path introspection, health checks, and wizard setup.

#### `bg3 tools` (`packages/bg3-core/bg3_core/tools.py`)
- **Command Alias**: `tools`
- **Primary CLI**: `bg3 tools [list|search|info|verify|audit] [flags...]`
- **Module Location**: `packages/bg3-core/bg3_core/tools.py`
- **Purpose**: Centralized tooling catalog, schema inspection, discovery router, and integrity auditor.
- **Key Flags**:
  - `--list`: Lists all registered tools (supports `--category <name>` and `--json`).
  - `--search <query>`: Keyword and intent search across tools and descriptions.
  - `--info <name>`: Emits complete CLI schema, flags, and usage examples for a tool.
  - `--verify`: Runs automated integrity verification across packages and skills (`--audit-skills`).
  - `--audit-skills`: Audits agent skills for registry discovery compliance and link integrity.
- **Usage**: `bg3 tools search "stat handles" --json`

#### `bg3 env` (`packages/bg3-core/bg3_core/setup_environment.py`)
- **Command Alias**: `setup-env`
- **Primary CLI**: `bg3 env [check|paths|setup] [flags...]`
- **Module Location**: `packages/bg3-core/bg3_core/setup_environment.py`
- **Purpose**: Setup wizard and path diagnostics. Validates Steam installation paths, Larian AppData directories, and mod.io API keys in `$XDG_CONFIG_HOME/bg3/env` (mode `0600`).
- **Usage**: `bg3 env check --json` or `bg3 env paths`

---

### 3.2 Authoring & Scaffolding Tools (`packages/bg3-authoring/`)

#### `bg3 mod scaffold` (`packages/bg3-authoring/bg3_authoring/create_mod_scaffold.py`)
- **Command Alias**: `scaffold-mod`
- **Primary CLI**: `bg3 mod scaffold --name <ModName> [--slug <slug>] [--unlock-level-curve] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/create_mod_scaffold.py`
- **Purpose**: Generates the complete Larian directory tree (`Mods/`, `Projects/`, `Public/`, `Localization/`), calculates `Version64`, allocates UUIDs, and creates a default 512x512 project thumbnail.

#### `bg3 scaffold stat` (`packages/bg3-authoring/bg3_authoring/scaffold_stat_entry.py`)
- **Command Alias**: `scaffold-stat`
- **Primary CLI**: `bg3 scaffold stat --mod <ModName> --type <Type> --name <Name> --display-name <Text> --description <Text>`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/scaffold_stat_entry.py`
- **Purpose**: Appends new stats (`Weapon`, `Armor`, `SpellData`, `PassiveData`, `StatusData`) to `Public/<Mod>/Stats/Generated/Data/*.txt` and registers localized DisplayName and Description handles in `Localization/English/*.xml`.

#### `bg3 scaffold progression` (`packages/bg3-authoring/bg3_authoring/scaffold_progression_node.py`)
- **Command Alias**: `scaffold-progression`
- **Primary CLI**: `bg3 scaffold progression --mod <ModName> --class <Class> --subclass <Subclass> --level <Level>`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/scaffold_progression_node.py`
- **Purpose**: Scaffolds and merges Larian v4.8 XML Progression and `SpellLists.lsx` nodes for class or subclass leveling, automatically resolving `TableUUID` associations.

#### `bg3 scaffold root-template` (`packages/bg3-authoring/bg3_authoring/scaffold_root_template.py`)
- **Command Alias**: `scaffold-template`
- **Primary CLI**: `bg3 scaffold root-template --mod <ModName> --item <StatName> --visual-preset <Preset>`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/scaffold_root_template.py`
- **Purpose**: Binds a stat entry to a 3D GameObject RootTemplate in `Public/<Mod>/RootTemplates/_merged.lsx`, linking collision, visual meshes, and physics presets.

#### `bg3 mod inject-treasure` (`packages/bg3-authoring/bg3_authoring/inject_treasure_table.py`)
- **Command Alias**: `inject-drop`
- **Primary CLI**: `bg3 mod inject-treasure --mod <ModName> --item <ItemName> --container <Container>`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/inject_treasure_table.py`
- **Purpose**: Injects custom items into world drop containers (Tutorial Chest, Camp Chest, or early Act 1 vendors) via `TreasureTable.txt` without modifying base game story files.

#### `bg3 scaffold icon-uvs` (`packages/bg3-authoring/bg3_authoring/scaffold_icon_uvs.py`)
- **Command Alias**: `scaffold-icon-uvs`
- **Primary CLI**: `bg3 scaffold icon-uvs --mod <ModName> --atlas-size <Size> --icon-size <Size>`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/scaffold_icon_uvs.py`
- **Purpose**: Computes normalized UV texture atlas coordinates and generates `GUI/Icons.lsx` entries for custom ability or item icons.

#### `bg3 mod patch` (`packages/bg3-authoring/bg3_authoring/generate_compat_patch.py`)
- **Command Alias**: `compat-patch`
- **Primary CLI**: `bg3 mod patch --mod1 <ModA> --mod2 <ModB> --output Mods/authored/<PatchSlug>`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/generate_compat_patch.py`
- **Purpose**: Generates standalone compatibility patches or Compatibility Framework (`CF`) JSON/LSX configurations between two mods modifying colliding tables.

#### `bg3 mod add-dependency` (`packages/bg3-authoring/bg3_authoring/add_mod_dependency.py`)
- **Command Alias**: `add-dependency`
- **Primary CLI**: `bg3 mod add-dependency <ModSlug> <DependencySlug> [--test] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/add_mod_dependency.py`
- **Purpose**: Appends community or core mod dependencies into `meta.lsx`, updates `README.md`, or adds test-only dependencies to `.test_deps.json` without modifying production manifests.

---

### 3.3 Diagnostics & Auditing Tools (`packages/bg3-authoring/`)

#### `bg3 mod validate` (`packages/bg3-authoring/bg3_authoring/diagnostics/validate_mod.py`)
- **Command Alias**: `validate`
- **Primary CLI**: `bg3 mod validate <ModSlug> [--strict] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/diagnostics/validate_mod.py`
- **Purpose**: Static linter and validator. Verifies LSX XML well-formedness, checks UUID formats, detects missing localization string handles, and validates directory structures.

#### `bg3 mod conflict` (`packages/bg3-authoring/bg3_authoring/diagnostics/check_mod_conflicts.py`)
- **Command Alias**: `check-conflicts`
- **Primary CLI**: `bg3 mod conflict <ModSlug> [--against-library] [--candidate <ModSlug>] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/diagnostics/check_mod_conflicts.py`
- **Purpose**: Analyzes mod packages for entry collisions (duplicate stats, identical RootTemplate names) and flags console-incompatible files (such as native `.dll` files).

#### `bg3 mod sync-loca` (`packages/bg3-authoring/bg3_authoring/diagnostics/sync_localization.py`)
- **Command Alias**: `sync-loca`
- **Primary CLI**: `bg3 mod sync-loca <ModSlug> [--prune] [--compile] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/diagnostics/sync_localization.py`
- **Purpose**: Audits localization XML files, prunes orphaned string handles, compiles binary `.loca` tables, and syncs multi-language XMLs.

#### `bg3 mod diagnose-logs` (`packages/bg3-authoring/bg3_authoring/diagnostics/diagnose_toolkit_logs.py`)
- **Command Alias**: `toolkit-logs`
- **Primary CLI**: `bg3 mod diagnose-logs --mod <ModSlug> [--severity warning|error] [--follow] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/diagnostics/diagnose_toolkit_logs.py`
- **Purpose**: Parses BG3 Toolkit (`Glasses.exe`) message logs, filters by subsystem (Boosts, Stats, Thoth, Osiris), correlates errors to workspace mods, or streams active sessions with `--follow`.

#### `bg3 mod inspect-save` (`packages/bg3-authoring/bg3_authoring/diagnostics/inspect_save_game.py`)
- **Command Alias**: `inspect-save`
- **Primary CLI**: `bg3 mod inspect-save [--audit] [--save-file <Path>] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/diagnostics/inspect_save_game.py`
- **Purpose**: Extracts active mod UUIDs and load orders from `.lsv` save files (Zstandard and LSOF v7 LZ4-frame decoding) and audits them against the player's active `modsettings.lsx`.

---

### 3.4 Packaging & Deployment Tools (`packages/bg3-authoring/`)

#### `bg3 mod pack` (`packages/bg3-authoring/bg3_authoring/packaging/pack_mod_pak.py`)
- **Command Alias**: `pack-pak`
- **Primary CLI**: `bg3 mod pack <ModSlug> [--output dist/<ModSlug>.pak] [--publish-local] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/packaging/pack_mod_pak.py`
- **Purpose**: Pure-Python LSPK v18 packager. Compresses mod files using zlib, auto-compiles binary `.loca`, and writes binary headers directly to `.pak` format without third-party dependencies.

#### `bg3 mod sync-game` (`packages/bg3-authoring/bg3_authoring/packaging/sync_game_data.py`)
- **Command Alias**: `sync-game`
- **Primary CLI**: `bg3 mod sync-game <ModSlug> [--watch] [--clean-mod] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/packaging/sync_game_data.py`
- **Purpose**: Performs idempotent synchronization of mod source trees from `$XDG_DOCUMENTS_DIR/BG3_Mod_Studio/Mods/authored/` to Steam `Baldurs Gate 3/Data/`. Supports continuous file watching with `--watch` and targeted loose data cleanup with `--clean-mod`.

---

### 3.5 Management & Load Order Tools (`packages/bg3-core/`)

#### `bg3 loadorder` (`packages/bg3-core/bg3_core/manage_load_order.py`)
- **Command Alias**: `load-order`
- **Primary CLI**: `bg3 loadorder [list|enable|disable|isolate|validate|clean|sync] [flags...]`
- **Module Location**: `packages/bg3-core/bg3_core/manage_load_order.py`
- **Purpose**: Parses, modifies, and validates the player's `modsettings.lsx`. Enables, disables, orders, isolates, and audits active mods.
- **Key Actions**:
  - `bg3 loadorder list`: Lists active mods in current profile.
  - `bg3 loadorder enable <slug> [--with-deps]`: Enables mod and prerequisite dependencies.
  - `bg3 loadorder isolate <slug>`: Clean-room isolation disabling all unrelated mods.
  - `bg3 loadorder validate`: Validates active load order against dependency ordering rules.

#### `bg3 mod bump-version` (`packages/bg3-core/bg3_core/bump_mod_version.py`)
- **Command Alias**: `bump-version`
- **Primary CLI**: `bg3 mod bump-version <ModSlug> [patch|minor|major|build] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/bump_mod_version.py`
- **Purpose**: Increments semantic versions and re-encodes 64-bit uint `Version64` across all `meta.lsx` instances while updating `README.md`.

#### `bg3 mod render-desc` (`packages/bg3-core/bg3_core/render_modio_description.py`)
- **Command Alias**: `render-description`
- **Primary CLI**: `bg3 mod render-desc <ModSlug> [--write] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/render_modio_description.py`
- **Purpose**: Renders the mod's root `README.md` as GFM-table-formatted `modio_description.html` for publishing.

#### `bg3 modio update-metadata` (`packages/bg3-core/bg3_core/modio_update_metadata.py`)
- **Command Alias**: `modio-update-metadata`
- **Primary CLI**: `bg3 modio update-metadata <ModSlug> [--tags <Tags>] [--confirm] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/modio_update_metadata.py`
- **Purpose**: Previews and applies approved mod.io metadata, tags, non-commercial permissions, and public visibility via REST API; writes require explicit `--confirm`.

---

### 3.6 Library & Mod.io Search Tools (`packages/bg3-core/`)

#### `bg3 query` (`packages/bg3-core/bg3_core/query_mod_database.py`)
- **Command Alias**: `query-db`
- **Primary CLI**: `bg3 query [--slot <Slot>] [--search <Query>] [--limit <N>] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/query_mod_database.py`
- **Purpose**: High-speed database engine searching cataloged items, spells, passives, and boosts. Supports filtering by equipment slot, rarity, and keywords in under 10ms.

#### `bg3 modio update-catalog` (`packages/bg3-core/bg3_core/update_library_catalog.py`)
- **Command Alias**: `update-catalog`
- **Primary CLI**: `bg3 modio update-catalog [--check] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/update_library_catalog.py`
- **Purpose**: Aggregates individual mod specs in `Mods/subscribed/*/README.md` into the master six-column index at `Mods/subscribed/library.md`.

#### `bg3 modio search` (`packages/bg3-core/bg3_core/modio_search.py`)
- **Command Alias**: `modio-search`
- **Primary CLI**: `bg3 modio search <query> [--platform <Platform>] [--limit <N>] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/modio_search.py`
- **Purpose**: Queries the mod.io REST API with platform tags (`windows`, `mac`, `playstation_5`, `xboxseries`) and natural language terms.

#### `bg3 modio sync` (`packages/bg3-core/bg3_core/modio_sync.py`)
- **Command Alias**: `modio-sync`
- **Primary CLI**: `bg3 modio sync [--download-all] [--prune|--no-prune] [--sync-library] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/modio_sync.py`
- **Purpose**: Synchronizes all subscribed mods from mod.io into local `Mods/subscribed/` and updates `Mods/subscribed/library.md`. Supports safe pruning guards.

#### `bg3 modio update` (`packages/bg3-core/bg3_core/modio_update.py`)
- **Command Alias**: `modio-update`
- **Primary CLI**: `bg3 modio update [--all | --mod <slug>] [--check-only] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/modio_update.py`
- **Purpose**: Compares local mod versions against remote mod.io releases and reports or triggers updates.

#### `bg3 modio extract` (`packages/bg3-core/bg3_core/modio_extract.py`)
- **Command Alias**: `modio-extract`
- **Primary CLI**: `bg3 modio extract [--mod-id <ID> | --pak <Path>] [--slug <Slug>] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/modio_extract.py`
- **Purpose**: Unpacks mod archives (`.pak` or `.zip`), extracts Larian XML/TXT files, and outputs structured markdown documentation for `Mods/subscribed/<slug>/README.md`.

#### `bg3 modio create-collection` (`packages/bg3-core/bg3_core/modio_create_collection.py`)
- **Command Alias**: `modio-collection`
- **Primary CLI**: `bg3 modio create-collection [--dry-run] [--title <Title>] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/modio_create_collection.py`
- **Purpose**: Creates or updates public mod.io collections from cataloged mods in `Mods/subscribed/library.md`, checking numeric mod IDs and game ID `6715`.

#### `bg3 modio purge` (`packages/bg3-core/bg3_core/purge_library.py`)
- **Command Alias**: `purge-library`
- **Primary CLI**: `bg3 modio purge [--confirm] [--dry-run] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/purge_library.py`
- **Purpose**: Purges local mod folders from `Mods/subscribed/` and resets `Mods/subscribed/library.md` catalog with strict confirmation guards.

---

### 3.7 Theorycrafting & Combat Modeling (`packages/bg3-theorycraft/`)

#### `bg3 build` (`packages/bg3-theorycraft/bg3_theorycraft/simulate_build_synergy.py`)
- **Command Alias**: `simulate-build`
- **Primary CLI**: `bg3 build [--classes <ClassSpecs>] [--iterations <N>] [--json]`
- **Module Location**: `packages/bg3-theorycraft/bg3_theorycraft/simulate_build_synergy.py`
- **Purpose**: Simulates multiclass progression, spell slot matrices, Spell Save DC ceilings, and Turn 1 combat damage per round (DPR) sequences.
