# Features & Functionality Guide

This document details the core technical features, autonomous agent skills, and deterministic automation tooling available in the **Baldur's Gate 3 Mod Studio & Mod.io Toolkit**.

---

## 1. Technical Features & Architecture Overview

The workspace combines autonomous AI orchestration with deterministic Python automation to streamline every stage of the _Baldur's Gate 3_ modding lifecycle—from documenting the community you have installed to authoring custom subclasses, gear, and spells.

### Key Technical Capabilities

- **Zero-Dependency Automation Engine (65 Tools across 3 Workspace Packages)**:
  All studio automation tools (and the unified `bg3` CLI entrypoint) are implemented strictly using the **Python 3.10+ Standard Library** (`zlib`, `struct`, `xml.etree.ElementTree`, `urllib.request`, `hashlib`). They require zero virtual environments, third-party packages (`pip`), or external compilers for standard runtime operation.
- **Unified 2026 CLI Suite (`bg3`)**:
  The primary entrypoint is installed to `~/.local/bin/bg3` via `uv tool install "bg3[all]"`. It exposes structured domain commands (`mod`, `loadorder`, `modio`, `scaffold`, `query`, `build`, `tools`, `env`, `run`), standardizes POSIX exit codes, and provides modern **Dual-Channel Stream Discipline**: rich, styled output on interactive terminals, and pristine, machine-parsable JSON on `stdout` when `--json` is supplied or piped.
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
  Selectively mirrors source mod files from `$XDG_DOCUMENTS_DIR/BG3_Mod_Studio/Mods/authored/<ModSlug>/` to your `Baldurs Gate 3/.../Data/` directory. Features SHA/timestamp caching to prevent redundant disk I/O, an optional file watcher (`--watch`), and clean-up modes (`--clean-mod`).
- **Mod.io REST Integration Suite (`bg3 modio`)**:
  Automates mod discovery, platform-tag filtering (`windows`, `mac`, `playstation_5`, `xboxseries`), archive extraction, collection creation, and catalog synchronization using personal mod.io API keys and access tokens (`bg3 modio`).
- **Safe Sandboxing & Clean-Room Testing**:
  - Test dependencies are declared cleanly in `.test_deps.json` without contaminating production `meta.lsx` (`bg3 mod add-dependency <slug> --test`).
  - Clean-room load order isolation (`bg3 loadorder isolate <slug>`) temporarily disables unrelated mods in `modsettings.lsx` during verification.
  - Theorycrafting generators stream progression matrices directly to disk (`$XDG_DOCUMENTS_DIR/BG3_Mod_Studio/Build_Guides/`) outside Git.
- **Cost & Token Optimization Protocols**:
  - Background subagent workers strictly inherit the parent model (`"Model": "inherit"`) preserving complete tool and reasoning compatibility across complex workflows.
  - High-speed discovery hub (`bg3 tools`) emits compact manifests (`--json`) saving up to 83.5% tokens during automated AI routing.

---

## 2. Autonomous Agent Skills (Slash Commands)

Autonomous skills bundled inside the workspace domain packages (`packages/*/skills/`) and deployed dynamically into `${BG3_STUDIO_DIR}/.agents/skills/` allow developers to trigger end-to-end workflows via natural language slash commands.

| Slash Command                   | Skill                         | Category       | Primary Function                                                           |
| :------------------------------ | :---------------------------- | :------------- | :------------------------------------------------------------------------- |
| `/bg3-create-mod`               | `bg3-create-mod`              | Stage 1        | Autonomous creation: interview, scaffolding, concurrent subagents, static validation. |
| `/bg3-diagnose-mod`             | `bg3-diagnose-mod`            | Stage 2        | Toolkit staging & diagnostics: Data/ sync & .loca, User-Action Gate 1 runtime triage. |
| `/bg3-test-mod`                 | `bg3-test-mod`                | Stage 3        | Clean-room testing: Data purge, local .pak deploy, User-Action Gate 2, Dual-Track routing. |
| `/bg3-release-prep`             | `bg3-release-prep`            | Stage 4        | Release staging: Version64 bump, strict lint, GFM HTML render, Data/ staging for Gate 3. |
| `/bg3-post-release`             | `bg3-post-release`            | Stage 5        | Storefront governance: mod.io REST API metadata/tags, dev teardown, subscriber test. |
| `/bg3-manage-load-order`        | `bg3-manage-load-order`       | Management     | Natural language inspection, ordering, and activation in `modsettings.lsx`.|
| `/bg3-check-mod-conflicts`      | `bg3-check-mod-conflicts`     | Compatibility  | Evaluates stat collisions and console load order compatibility.            |
| `/bg3-create-modio-collection`  | `bg3-create-modio-collection` | Community      | Creates or updates public mod.io collections from the mod library catalog. |
| `/bg3-query-gear`               | `bg3-query-gear`              | Library        | Interactive advisor querying cataloged BiS mod items and spells.           |
| `/bg3-search-mods`              | `bg3-search-mods`             | Discovery      | Searches mod.io with platform filters and checks for conflicts.            |
| `/bg3-sync-mod-docs`            | `bg3-sync-mod-docs`           | Documentation  | Concurrently downloads, unpacks, documents, and updates mod batches.       |
| `/bg3-sync-single-mod`          | `bg3-sync-single-mod`         | Documentation  | Extracts, inspects, documents, or updates a single mod archive.            |
| `/bg3-create-build-guide`       | `bg3-create-build-guide`      | Theorycrafting | Builds high-end Level 20 build guides pairing mod items with vanilla gear. |
| `/grill-me`                     | `grill-me`                    | Interview      | Interactive design-tree clarification interview before planning/coding.    |

---

### Detailed Skill Descriptions & Example Prompts

#### 1. `/bg3-create-mod` (Stage 1: Creation)

Orchestrates mod authoring in `$XDG_DOCUMENTS_DIR/BG3_Mod_Studio/Mods/authored/<ModSlug>/`. Conducts an interactive `/grill-me` interview to resolve design decisions, generates directories and metadata (`Version64`, UUIDv4), dispatches specialized concurrent subagents to author stats, progressions, and RootTemplates, and executes comprehensive read-only static verification (LSX/XML schema integrity, string handle parity, and library conflict pre-check) without touching external game directories or `AppData/`.

- **Example Prompt**:
  ```text
  /bg3-create-mod Create a rogue subclass named Shadowblade with psychic sneak attack bonuses and a custom dagger.
  ```

#### 2. `/bg3-diagnose-mod` (Stage 2: Diagnostics & Toolkit Staging)

Acts as an autonomous mod doctor managing **User-Action Gate 1 (Toolkit Diagnostics)**: Phase 2A asserts static workspace cleanliness, stages unpacked assets and compiled binary `.loca` into `<Game>/Data/`, and directs the author to launch the official Baldur's Gate 3 Toolkit (`Glasses.exe`); Phase 2B triages runtime logs (`messages.log`), applies targeted source fixes to `$XDG_DOCUMENTS_DIR/BG3_Mod_Studio/Mods/authored/<ModSlug>/`, and loops back to Phase 2A until clean before offering Stage 3 testing.

- **Example Prompt**:
  ```text
  /bg3-diagnose-mod Diagnose shadowblade and check for any Toolkit log errors.
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
  /bg3-check-mod-conflicts Check if candidate mod 51234 conflicts with any of my installed mods.
  ```

#### 8. `/bg3-create-modio-collection`

Creates or updates public mod.io collections from cataloged mods in the user's mod library, verifying numeric mod IDs and game ID `6715` with dry-run previews before writing.

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

#### 11. `/bg3-sync-mod-docs`

Orchestrates concurrent subagents to download, unpack, validate, document, and update community mods from mod.io into `$BG3_SUBSCRIBED_MODS_DIR/<mod_name>/README.md` and updates `library.md`. Supports batch queries, explicit mod slugs, or auditing all tracked subscriptions.

- **Example Prompt**:
  ```text
  /bg3-sync-mod-docs 5e-spells unlocklevelcurve extra-gear
  ```

#### 12. `/bg3-sync-single-mod`

Worker skill that fetches, unpacks, validates, documents, or updates a single Baldur's Gate 3 mod from mod.io into `mods/<mod_name>/README.md` using the rich feature schema and static in-game validation.

- **Example Prompt**:
  ```text
  /bg3-sync-single-mod 4166963
  ```

#### 13. `/bg3-create-build-guide`

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

## 3. Automation Tools & Packages Reference (`packages/bg3-*`)

All 65 canonical studio automation tools are organized into domain-specific packages within `packages/` (`bg3`, `bg3-authoring`, `bg3-theorycraft`) and discoverable dynamically via `bg3 tools`.

Every tool supports dual-mode execution:
1. **Unified CLI Command** (recommended): `bg3 <command> <subcommand> [flags...] [--json]`
2. **Direct Module Execution**: `uv run -m <module> [flags...]`

---

### 3.1 Unified CLI Suite & Environment (`packages/bg3-core/bg3_core/cli.py`, `setup_environment.py`)

#### `bg3 env` (`packages/bg3-core/bg3_core/setup_environment.py`)
- **Command Alias**: `env`
- **Primary CLI**: `bg3 env [setup|check|paths] [flags...]`
- **Purpose**: Interactive setup wizard, non-interactive status check, and XDG storage path resolution.
- **Usage**: `bg3 env setup [--non-interactive] [--dry-run]`, `bg3 env check [--json]`, `bg3 env paths`

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

#### `bg3 mod create` (`packages/bg3-authoring/bg3_authoring/create_mod_scaffold.py`)
- **Command Alias**: `create`
- **Primary CLI**: `bg3 mod create <name> [--name <Name>] [--author <Author>] [--description <Desc>] [--version <Ver>] [--dest <Path>] [--dry-run]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/create_mod_scaffold.py`
- **Purpose**: Generates the complete canonical Larian directory tree (`Mods/`, `Projects/`, `Public/`, `Localization/`), calculates `Version64`, allocates UUIDs, inlines the default README specification, and generates a default 512x512 project thumbnail.

#### `bg3 scaffold <asset>` / `bg3 mod scaffold <asset>` (`packages/bg3-authoring/bg3_authoring/scaffold_asset.py`)
- **Command Alias**: `scaffold`
- **Primary CLI**: `bg3 scaffold <asset-type> --mod <ModName> [flags...]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/scaffold_asset.py` (facade routing to domain engines)
- **Purpose**: Modular asset scaffolding engine returning uniform typed `ScaffoldResult` contracts across 15 asset categories:
  - **Mechanics (`scaffold_mechanics.py`)**:
    - `bg3 scaffold class --mod <Mod> --name <Name> [--subclass <Sub>] [--parent <Parent>]`
    - `bg3 scaffold progression --mod <Mod> --class <Class> --level <Lvl> [--subclass <Sub>]`
    - `bg3 scaffold feat --mod <Mod> --name <Name> [--passives <List>]`
    - `bg3 scaffold action-resource --mod <Mod> --name <Name> [--dice <Dice>]`
    - `bg3 scaffold spell-list --mod <Mod> --name <Name> --spells <Spells>`
    - `bg3 scaffold level-map --mod <Mod> --name <Name> --curve <Curve>`
    - `bg3 scaffold default-values --mod <Mod> --name <Name> --origin <Origin>`
    - `bg3 scaffold stat --mod <Mod> --type <Type> --name <Name> --display-name <Text> --description <Text>`
  - **Visuals (`scaffold_visuals.py`)**:
    - `bg3 scaffold root-template --mod <Mod> --name <Name> --preset <Preset>`
    - `bg3 scaffold appearance-visual --mod <Mod> --name <Name> --visual-resource <UUID>`
  - **Atlas (`scaffold_atlas.py`)**:
    - `bg3 scaffold icon-uvs --mod <Mod> --atlas-size <Size> --icon-size <Size>`
  - **Character (`scaffold_character.py`)**:
    - `bg3 scaffold race --mod <Mod> --name <Name>`
    - `bg3 scaffold origin --mod <Mod> --name <Name>`
    - `bg3 scaffold appearance --mod <Mod> --name <Name>`
    - `bg3 scaffold tag --mod <Mod> --name <Name> --category <Category>`

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

#### `bg3 mod conflict` (`packages/bg3-core/bg3_core/check_mod_conflicts.py`)
- **Command Alias**: `check-conflicts`
- **Primary CLI**: `bg3 mod conflict <ModSlug> [--against-library] [--candidate <ModSlug>] [--json]`
- **Module Location**: `packages/bg3-core/bg3_core/check_mod_conflicts.py`
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

---

### 3.4 Packaging & Deployment Tools (`packages/bg3-authoring/`)

#### `bg3 mod pack` (`packages/bg3-authoring/bg3_authoring/packaging/pack_mod_pak.py`)
- **Command Alias**: `pack-pak`
- **Primary CLI**: `bg3 mod pack <ModSlug> [--output dist/<ModSlug>.pak] [--publish-local] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/packaging/pack_mod_pak.py`
- **Purpose**: Pure-Python LSPK v18 packager. Compresses mod files using raw LZ4 block compression (LSPK v18), auto-compiles binary `.loca`, and writes binary headers directly to `.pak` format without third-party dependencies.

#### `bg3 mod sync-game` (`packages/bg3-authoring/bg3_authoring/packaging/sync_game_data.py`)
- **Command Alias**: `sync-game`
- **Primary CLI**: `bg3 mod sync-game --mods <ModSlug> [--watch] [--clean-mod <slug>] [--json]`
- **Module Location**: `packages/bg3-authoring/bg3_authoring/packaging/sync_game_data.py`
- **Purpose**: Performs idempotent synchronization of mod source trees from `$XDG_DOCUMENTS_DIR/BG3_Mod_Studio/Mods/authored/` to Steam `Baldurs Gate 3/Data/`. Supports continuous file watching with `--watch` and targeted loose data cleanup with `--clean-mod`.

---

### 3.5 Management & Load Order Tools (`packages/bg3-core/`)

#### `bg3 save` (`packages/bg3-core/bg3_core/manage_saves.py` & `bg3_core/save_inspector.py`)
- **Command Alias**: `saves`
- **Primary CLI**: `bg3 save [list|inspect|clean-missing|backup|purge] [flags...]`
- **Module Location**: `packages/bg3-core/bg3_core/manage_saves.py` & `packages/bg3-core/bg3_core/save_inspector.py`
- **Purpose**: Discovers, inspects, audits, backups, purges, and rescues Baldur's Gate 3 `.lsv` save files.
- **Key Actions**:
  - `bg3 save inspect [save|latest] [--audit]`: Extracts active mod UUIDs from binary LSF AST and audits against `modsettings.lsx`.
  - `bg3 save clean-missing [save|latest] [--out <path>] [--dry-run] [--yes]`: Strips missing or uninstalled mods from save AST to rescue unopenable or corrupted saves, preserving a `.bak` backup.
  - `bg3 save list`: Discovers all save games across Proton, WSL, and native paths.
  - `bg3 save backup [--save <name>] [--dest <dir>]`: Safely archives saves to timestamped ZIP packages.
  - `bg3 save purge [--keep 5] [--days 14] [--dry-run] [--yes]`: Prunes old save games with retention rules while protecting the latest save.

#### `bg3 loadorder` (`packages/bg3-core/bg3_core/manage_load_order.py`)
- **Command Alias**: `load-order`
- **Primary CLI**: `bg3 loadorder [list|sync|clean|enable|disable|validate|auto-sort|isolate|restore|dedup] [flags...]`
- **Module Location**: `packages/bg3-core/bg3_core/manage_load_order.py`
- **Purpose**: Parses, modifies, validates, and auto-sorts the player's active profile `modsettings.lsx`.
- **Key Actions**:
  - `bg3 loadorder list`: Lists active mods in current profile.
  - `bg3 loadorder sync`: Synchronizes installed local mods into the active load order profile.
  - `bg3 loadorder clean`: Cleans missing or invalid mods from the load order profile.
  - `bg3 loadorder enable <slug> [--with-deps]`: Enables mod and its prerequisite dependencies.
  - `bg3 loadorder disable <slug>`: Disables mod from the active load order profile.
  - `bg3 loadorder validate`: Validates active load order against declared dependencies and core positions.
  - `bg3 loadorder auto-sort`: Topologically auto-sorts active mods based on declared dependencies.
  - `bg3 loadorder isolate <slug>`: Clean-room isolation disabling all unrelated mods except dependencies.
  - `bg3 loadorder restore`: Restores quarantined mods from `Mods_Disabled/` back to active `Mods/`.
  - `bg3 loadorder dedup`: Deduplicates installed `.pak` files in AppData Mods.

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

#### `bg3 build` / `bg3 sim` (`packages/bg3-theorycraft/bg3_theorycraft/simulate_build_synergy.py`)
- **Command Alias**: `simulate-build`, `build`, `sim`
- **Primary CLI**: `bg3 build simulate [--classes <ClassSpecs>] [--dpr-sequence {melee_burst,eldritch_blast,ranged_burst}] [--target-ac <AC>] [--advantage] [--disadvantage] [--savage-attacker] [--ac-curve] [--json]`
- **Module Location**: `packages/bg3-theorycraft/bg3_theorycraft/simulate_build_synergy.py`
- **Purpose**: Simulates multiclass progression, spell slot matrices, Spell Save DC ceilings, action economy, and Turn 1 combat damage per round (DPR) sequences across melee, ranged, and spell bursts. Returns strongly-typed `SimulationResult` domain models (`models.py`) with full dictionary mapping backward compatibility.
