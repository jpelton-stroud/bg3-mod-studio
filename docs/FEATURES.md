# Features & Functionality Guide

This document details the core technical features, autonomous agent skills, and deterministic automation tooling available in the **Baldur's Gate 3 Mod Studio & Mod.io Toolkit**.

---

## 1. Technical Features & Architecture Overview

The workspace combines autonomous AI orchestration with deterministic Python automation to streamline every stage of the _Baldur's Gate 3_ modding lifecycle—from documenting the community you have installed to authoring custom subclasses, gear, and spells.

### Key Technical Capabilities

- **Zero-Dependency Automation Engine**:
  All 24 studio tools are implemented strictly using the **Python 3.10+ Standard Library** (`zlib`, `struct`, `xml.etree.ElementTree`, `urllib.request`). They require zero virtual environments, third-party packages (`pip`), or external compilers.
- **Pure-Python LSPK v18 Binary Packaging (`pack_mod_pak.py`)**:
  Builds uncorrupted Larian LSPK v18 package archives with custom zlib compression and binary headers directly on Linux, WSL, or Windows—bypassing the need for Windows-exclusive `LSLib` or `wine`.
- **Larian 64-bit Version Encoding (`Version64`)**:
  Calculates and updates Larian-compliant 64-bit unsigned integer version tags across `meta.lsx` and game profiles:
  $$\text{Version64} = (\text{major} \ll 55) \mid (\text{minor} \ll 47) \mid (\text{revision} \ll 31) \mid \text{build}$$
- **Larian XML Structure Engine (`*.lsx` & `*.xml`)**:
  Generates and parses standard Larian v4.8 XML structures, handles deterministic UUIDv4 generation, automatically allocates localization string handles in `Localization/English/*.xml`, and scaffolds `_merged.lsx` RootTemplates with valid 3D presets.
- **Sub-10ms Mod Database Query Engine (`query_mod_database.py`)**:
  Indexes over 2,200 cataloged community mod items, passives, spells, and boosts. Provides fuzzy search, slot filtering, and handle lookups in milliseconds.
- **Idempotent Differential Game Synchronization (`sync_to_game_data.py`)**:
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
| `/bg3_create_mod`               | [`bg3_create_mod`](.agents/skills/bg3_create_mod/SKILL.md)                             | Authoring      | Orchestrates design, stat authoring, localization, and sync.               |
| `/bg3_diagnose_mod`             | [`bg3_diagnose_mod`](.agents/skills/bg3_diagnose_mod/SKILL.md)                         | Diagnostics    | AI doctor diagnosing load orders, handles, XMLs, and collisions.           |
| `/bg3_document_mods`            | [`bg3_document_mods`](.agents/skills/bg3_document_mods/SKILL.md)                       | Documentation  | Concurrently downloads, unpacks, and catalogs mod batches.                 |
| `/bg3_document_single_mod`      | [`bg3_document_single_mod`](.agents/skills/bg3_document_single_mod/SKILL.md)           | Documentation  | Extracts, inspects, and catalogs a single mod archive.                     |
| `/bg3_manage_load_order`        | [`bg3_manage_load_order`](.agents/skills/bg3_manage_load_order/SKILL.md)               | Management     | Natural language inspection and editing of `modsettings.lsx`.              |
| `/bg3_query_gear`               | [`bg3_query_gear`](.agents/skills/bg3_query_gear/SKILL.md)                             | Library        | Interactive advisor querying cataloged BiS mod items and spells.           |
| `/bg3_release_prep`             | [`bg3_release_prep`](.agents/skills/bg3_release_prep/SKILL.md)                         | Publication    | Validates assets, bumps Version64, and prepares release metadata.          |
| `/bg3_search_mods`              | [`bg3_search_mods`](.agents/skills/bg3_search_mods/SKILL.md)                           | Discovery      | Searches mod.io with platform filters and checks for conflicts.            |
| `/bg3_check_mod_conflicts`      | [`bg3_check_mod_conflicts`](.agents/skills/bg3_check_mod_conflicts/SKILL.md)           | Compatibility  | Evaluates collision and compatibility against tracked mods.                |
| `/bg3_update_mod_documentation` | [`bg3_update_mod_documentation`](.agents/skills/bg3_update_mod_documentation/SKILL.md) | Maintenance    | Checks tracked mods for upstream updates and refreshes specs.              |
| `/bg3_update_single_mod`        | [`bg3_update_single_mod`](.agents/skills/bg3_update_single_mod/SKILL.md)               | Maintenance    | Updates documentation and assets for an individual mod.                    |
| `/bg3_create_build_guide`       | [`bg3_create_build_guide`](.agents/skills/bg3_create_build_guide/SKILL.md)             | Theorycrafting | Builds high-end Level 20 build guides pairing mod items with vanilla gear. |
| `/grill-me`                     | [`grill-me`](.agents/skills/grill-me/SKILL.md)                                         | Interview      | Interactive design-tree clarification interview before planning/coding.    |

---

### Detailed Skill Descriptions & Example Prompts

#### 1. `/bg3_create_mod`

Orchestrates an end-to-end mod authoring pipeline. Automatically grills design requirements, generates directories, creates UUIDs and Version64 tags, allocates localization handles, authors stats and RootTemplates, and synchronizes files into the game data folder.

- **Example Prompt**:
  ```text
  /bg3_create_mod Create a rogue subclass named Shadowblade with psychic sneak attack bonuses and a custom dagger.
  ```

#### 2. `/bg3_diagnose_mod`

Acts as an autonomous mod doctor. Performs a 4-layer diagnostic inspection (directory structure, XML syntax, localization handle references, and stat collisions) and proposes automated fixes.

- **Example Prompt**:
  ```text
  /bg3_diagnose_mod Diagnose my_mods/Shadowblade and fix any missing localization handles or XML malformations.
  ```

#### 3. `/bg3_document_mods`

Spawns parallel background subagents to unpack, inspect, and document a batch of community mods from mod.io. Automatically cataloging items, passives, and spells into `mods/<mod_slug>/README.md` and updating `mods/library.md`.

- **Example Prompt**:
  ```text
  /bg3_document_mods faerun-colors additional-enemies-mod ancient-armory
  ```

#### 4. `/bg3_document_single_mod`

Downloads, extracts, and validates an individual mod archive from mod.io, generating a standardized markdown specification with stat tables and mechanics.

- **Example Prompt**:
  ```text
  /bg3_document_single_mod ancient-armory
  ```

#### 5. `/bg3_manage_load_order`

Inspects, activates, disables, or reorders mods within the player's active profile `modsettings.lsx` via natural language, verifying prerequisite dependencies.

- **Example Prompt**:
  ```text
  /bg3_manage_load_order Check my current load order, enable Shadowblade at the end, and verify there are no missing dependencies.
  ```

#### 6. `/bg3_query_gear`

Advises on Best-in-Slot (BiS) gear, stat boosts, spells, and passives across the local community catalog. Translates natural language requests into instant database queries.

- **Example Prompt**:
  ```text
  /bg3_query_gear Find the best modded rings and cloaks for an Arcane Trickster focusing on Spell Save DC and critical hits.
  ```

#### 7. `/bg3_release_prep`

Automates pre-publication verification for custom mods: executes strict XML validation, prunes orphaned localization handles, increments `Version64`, packages the `.pak`, and generates mod.io BBCode descriptions.

- **Example Prompt**:
  ```text
  /bg3_release_prep my_mods/shadow-blade
  ```

#### 8. `/bg3_search_mods`

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
- **Purpose**: Centralized discovery, search, info inspection, verification, and dispatch router for all 24 studio tools.
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
- **Usage**: `python3 scripts/create_mod_scaffold.py <ModName> [--author <Author>] [--description <Desc>]`

#### `scripts/scaffold_stat_entry.py`

- **Command Alias**: `scaffold-stat`
- **Purpose**: Appends new stats (`Weapon`, `Armor`, `SpellData`, `PassiveData`, `StatusData`) to `Public/<Mod>/Stats/Generated/Data/*.txt` and registers localized DisplayName and Description handles in `Localization/English/*.xml`.
- **Usage**: `python3 scripts/scaffold_stat_entry.py --mod <ModName> --type Weapon --name MAG_ShadowDagger --rarity VeryRare`

#### `scripts/scaffold_progression_node.py`

- **Command Alias**: `scaffold-progression`
- **Purpose**: Scaffolds and merges Larian v4.8 XML Progression and `SpellLists.lsx` nodes for class or subclass leveling, automatically resolving `TableUUID` associations.
- **Usage**: `python3 scripts/scaffold_progression_node.py --mod <ModName> --class Rogue --subclass Shadowblade --level 3`

#### `scripts/scaffold_root_template.py`

- **Command Alias**: `scaffold-template`
- **Purpose**: Binds a stat entry to a 3D GameObject RootTemplate in `Public/<Mod>/RootTemplates/_merged.lsx`, linking collision, visual meshes, and physics presets.
- **Usage**: `python3 scripts/scaffold_root_template.py --mod <ModName> --item MAG_ShadowDagger --visual-preset Dagger_A`

#### `scripts/inject_treasure_table.py`

- **Command Alias**: `inject-drop`
- **Purpose**: Injects custom items into world drop containers (Tutorial Chest, Camp Chest, or early Act 1 vendors) via `TreasureTable.txt` without modifying base game story files.
- **Usage**: `python3 scripts/inject_treasure_table.py --mod <ModName> --item MAG_ShadowDagger --drop-location TutorialChest`

#### `scripts/generate_icon_atlas.py`

- **Command Alias**: `generate-icons`
- **Purpose**: Computes normalized UV texture atlas coordinates and generates `GUI/Icons.lsx` entries for custom ability or item icons.
- **Usage**: `python3 scripts/generate_icon_atlas.py --mod <ModName> --atlas-size 2048 --icon-size 64`

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

#### `scripts/sync_to_game_data.py`

- **Command Alias**: `sync-game`
- **Purpose**: Performs idempotent synchronization of mod source trees from `my_mods/` to Steam `Baldurs Gate 3/Data/`. Supports continuous file watching with `--watch`.
- **Usage**: `python3 scripts/sync_to_game_data.py --mod Shadowblade [--watch]`

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
- **Purpose**: Audits localization XML files, prunes orphaned string handles, creates `.bak` safety backups, and syncs handles across multiple language files.
- **Usage**: `python3 scripts/sync_localization.py --mod my_mods/Shadowblade [--prune]`

#### `scripts/inspect_save_game.py`

- **Command Alias**: `inspect-save`
- **Purpose**: Extracts active mod UUIDs and load orders from `.lsv` save files and audits them against the player's active `modsettings.lsx` to diagnose load-order crashes.
- **Usage**: `python3 scripts/inspect_save_game.py --save ~/.local/share/Larian\ Studios/.../Quicksave.lsv`

---

### Management & Publication Tools

#### `scripts/manage_load_order.py`

- **Command Alias**: `load-order`
- **Purpose**: Parses, modifies, and validates the player's `modsettings.lsx`. Enables, disables, moves, and audits active mods.
- **Usage**: `python3 scripts/manage_load_order.py --enable Shadowblade --order 12`

#### `scripts/bump_mod_version.py`

- **Command Alias**: `bump-version`
- **Purpose**: Increments semantic versions (`--major`, `--minor`, `--patch`) and re-encodes 64-bit uint `Version64` across all `meta.lsx` instances in a mod.
- **Usage**: `python3 scripts/bump_mod_version.py --mod my_mods/Shadowblade --minor`

#### `scripts/generate_mod_metadata.py`

- **Command Alias**: `gen-metadata`
- **Purpose**: Extracts mod properties and formats ready-to-publish BBCode descriptions, release changelogs, and metadata tags for mod.io and the official Toolkit.
- **Usage**: `python3 scripts/generate_mod_metadata.py --mod my_mods/Shadowblade`

#### `scripts/setup_environment.py`

- **Command Alias**: `setup-env`
- **Purpose**: Interactive/non-interactive configuration wizard. Validates Steam installation paths, Larian AppData directories, and mod.io API keys in `.env`.
- **Usage**: `python3 scripts/setup_environment.py [--non-interactive]`

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
