# Baldur's Gate 3 Mod Studio — Automation Tooling & CLI Suite

This directory contains the deterministic automation engine and unified CLI suite for the **Baldur's Gate 3 Mod Studio**. 

All tools are engineered with **100% Pure Python Standard Library** (zero `pip install`, zero external dependencies, cross-platform WSL/Linux/Windows) and expose structured `--json` outputs for autonomous machine agents and CI/CD pipelines.

---

## 🚀 Unified CLI Suite (`scripts/bg3.py`)

The primary command-line interface for the studio is [`scripts/bg3.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/bg3.py), which is symlinked to `~/.local/bin/bg3` by `setup.sh`:

```bash
# General invocation
bg3 <command> <subcommand> [options...] [--json]

# Studio environment paths and secret status
bg3 env paths --json
bg3 env check --json

# Discovery and schema inspection
bg3 tools list --json
bg3 tools search "stat handles" --json
bg3 tools info scaffold-stat --json
bg3 tools verify --json
bg3 tools verify --audit-skills --json

# Unified command runner (for any tool alias or script)
bg3 run query_mod_database --limit 5 --json
```

---

## 🗂️ Domain-Specific Architecture

Scripts are organized into domain-specific packages adhering to the 2026 CLI clean layered architecture:

```
scripts/
├── bg3.py                       # Root Unified CLI Entrypoint (symlinked to ~/.local/bin/bg3)
├── registry.json                # Machine-readable tooling manifest & schema catalog
├── README.md                    # This architecture and sitemap guide
├── lib/                         # Shared libraries (parsers, env paths, client adapters)
├── templates/                   # Mod templates and readme scaffolding assets
├── authoring/                   # Mod scaffolding, stats, progressions, and assets
├── diagnostics/                 # Validation, conflict detection, log triage, loca sync
├── library/                     # Mod.io REST sync, extraction, cataloging, DB queries
├── management/                  # Load order, version bumping, metadata, setup, tools
├── packaging/                   # Pure Python LSPK .pak archive building & game data sync
└── theorycrafting/              # Combat DPR simulation and multiclass slot modeling
```

---

## 📦 Shared Architecture Package (`scripts/lib/`)

Non-CLI shared utilities and binary parsers reside in [`scripts/lib/`](file:///home/jpstroud/projects/BaldursGate3/scripts/lib/):

| Module | Responsibility |
| :--- | :--- |
| `cli_common.py` | Dual-mode stdout/stderr stream discipline, ANSI color handling, and structured JSON envelopes. |
| `env_paths.py` | XDG Base Directory specification paths, cross-platform Steam, AppData, and mod directory resolution. |
| `lspk.py` | Pure Python Larian LSPK v18 `.pak` archive reader and writer with zlib compression. |
| `larian_parsers.py` | Bitwise `Version64` calculation, dual-layout `meta.lsx` parsing, functor splitting, and binary `.loca` compiling/decoding. |
| `modio_client.py` | Zero-dependency mod.io REST v1 client with streaming downloads and multipart/form-data payload construction. |
| `library_catalog.py` | Structured 6-column catalog parser, validator, and table generator for `mods/library.md`. |
| `mod_overrides.py` | Centralized overrides for non-standard folder layouts and community mod archive naming. |
| `mod_resolver.py` | Centralized dependency metadata resolution and .pak provisioning. |

---

## 🧰 Domain Tool Catalogs

### 1. Authoring & Content Scaffolding (`scripts/authoring/`)
Tools for generating game content, mechanics, items, and progressions.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `scaffold-mod` | [`create_mod_scaffold.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/authoring/create_mod_scaffold.py) | Scaffolds complete BG3 mod directory trees (`Mods/`, `Projects/`, `Localization/`, `meta.lsx`). |
| `scaffold-stat` | [`scaffold_stat_entry.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/authoring/scaffold_stat_entry.py) | Scaffolds Larian stat entries with automatic string handle allocation in `Localization/English/*.xml`. |
| `scaffold-progression` | [`scaffold_progression_node.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/authoring/scaffold_progression_node.py) | Scaffolds and merges Larian v4.8 Progression and companion `SpellLists.lsx` nodes with automatic `TableUUID` resolution. |
| `scaffold-template` | [`scaffold_root_template.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/authoring/scaffold_root_template.py) | Binds stat entries to 3D visual GameObjects in `_merged.lsx` linking meshes, collision, and handles. |
| `inject-drop` | [`inject_treasure_table.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/authoring/inject_treasure_table.py) | Injects custom mod items into Tutorial Chest, Camp Chest, or early vendors via `TreasureTable.txt`. |
| `scaffold-icons` | [`scaffold_icon_uvs.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/authoring/scaffold_icon_uvs.py) | Calculates normalized UV coordinates and generates `GUI/Icons.lsx` definitions for custom icon grids. |
| `compat-patch` | [`generate_compat_patch.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/authoring/generate_compat_patch.py) | Auto-generates compatibility patches (standalone or Compatibility Framework) between colliding mods. |
| `add-dependency` | [`add_mod_dependency.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/authoring/add_mod_dependency.py) | Injects permanent and test dependencies into `meta.lsx`, `.test_deps.json`, and `README.md`. |

---

### 2. Diagnostics, Validation & Auditing (`scripts/diagnostics/`)
Tools for health checks, syntax validation, collision detection, and save audits.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `validate` | [`validate_mod.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/diagnostics/validate_mod.py) | Deterministic static validator verifying LSX XML syntax, handle integrity, and assets. |
| `check-conflicts` | [`check_mod_conflicts.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/diagnostics/check_mod_conflicts.py) | Static entry collision analyzer checking stat overlaps and console-incompatible DLLs. |
| `sync-loca` | [`sync_localization.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/diagnostics/sync_localization.py) | Prunes orphaned string handles, compiles binary `.loca`, and audits missing handles. |
| `diagnose-logs` | [`diagnose_toolkit_logs.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/diagnostics/diagnose_toolkit_logs.py) | Triages BG3 Toolkit (`Glasses.exe`) runtime logs, correlating errors to workspace mods. |
| `inspect-save` | [`inspect_save_game.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/diagnostics/inspect_save_game.py) | Extracts mod load orders from `.lsv` saves (Zstd/LSOF v7) and audits against `modsettings.lsx`. |

---

### 3. Library & Database Search (`scripts/library/`)
Tools for querying cataloged community mods and interacting with mod.io.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `query-db` | [`query_mod_database.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/library/query_mod_database.py) | High-speed query engine searching mod items, passives, spells, and boosts. |
| `update-catalog` | [`update_library_catalog.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/library/update_library_catalog.py) | Compiles and validates 6-column categorized rows in [`mods/library.md`](file:///home/jpstroud/projects/BaldursGate3/mods/library.md). |
| `modio-search` | [`modio_search.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/library/modio_search.py) | Searches mod.io with natural language and platform filters (`console`, `windows`, etc.). |
| `modio-sync` | [`modio_sync.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/library/modio_sync.py) | Downloads and syncs subscribed mods from mod.io into `mods/`. |
| `modio-update` | [`modio_update.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/library/modio_update.py) | Checks tracked mods against remote mod.io releases and updates specifications. |
| `modio-extract` | [`modio_extract.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/library/modio_extract.py) | Unpacks remote or local LSPK `.pak` archives, extracts files, and indexes mod capabilities. |
| `modio-collection` | [`modio_create_collection.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/library/modio_create_collection.py) | Creates or updates public mod.io collections from cataloged mods in `mods/library.md`. |
| `purge-library` | [`purge_library.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/library/purge_library.py) | Purges untracked or corrupted mod folders from `mods/` and resets catalog. |

---

### 4. Management & Environment (`scripts/management/`)
Tools for load order configuration, versioning, environment setup, and registry inspection.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `load-order` | [`manage_load_order.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/management/manage_load_order.py) | Inspects, activates, disables, orders, and validates mod load order in `modsettings.lsx`. |
| `bump-version` | [`bump_mod_version.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/management/bump_mod_version.py) | Atomically increments semantic versions across `meta.lsx` and synchronizes `README.md`. |
| `render-description` | [`render_modio_description.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/management/render_modio_description.py) | Renders a mod's root `README.md` as GFM-table-formatted `modio_description.html`. |
| `post-release` | [`modio_update_metadata.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/management/modio_update_metadata.py) | Previews and applies approved mod.io metadata, tags, non-commercial permissions, and visibility. |
| `setup-env` | [`setup_environment.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/management/setup_environment.py) | Setup wizard checking Python, Steam BG3, AppData, and mod.io configuration. |
| `tools` | [`tools.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/management/tools.py) | Centralized schema registry, tool discovery, and execution dispatcher. |

---

### 5. Packaging & Game Deployment (`scripts/packaging/`)
Tools for packaging archives and syncing mods into the game engine.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `pack-pak` | [`pack_mod_pak.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/packaging/pack_mod_pak.py) | Pure-Python LSPK v18 `.pak` packager with automatic `.loca` compilation, local publish (`--publish-local`), and local purge (`--clean-local`). |
| `sync-game` | [`sync_game_data.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/packaging/sync_game_data.py) | Syncs custom mods to Steam BG3 `Data/` with compiled `.loca` generation, live watch mode, and targeted loose data cleanup (`--clean-mod`). |

---

### 6. Theorycrafting & Build Simulation (`scripts/theorycrafting/`)
Tools for mathematical combat modeling and multiclass rule engines.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `simulate-build` | [`simulate_build_synergy.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/theorycrafting/simulate_build_synergy.py) | Simulates Turn 1 combat sequences (DPR), Spell Save DC ceilings, and multiclass slot matrices. |

---

## 🤖 AI Agent Integration Protocol

Autonomous machine agents and skills interact with the tooling suite using the unified `bg3` CLI:

1. **Discovery & Search**:
   ```bash
   bg3 tools search "<intent or keyword>" --json
   ```
2. **Schema & Option Inspection**:
   ```bash
   bg3 tools info <command-alias> --json
   ```
3. **Deterministic Execution**:
   ```bash
   bg3 run <command-alias> [args...] --json
   # Or directly through the noun-verb hierarchy:
   bg3 mod validate <mod-slug> --json
   bg3 query --slot Weapon --limit 5 --json
   ```

---

## 🧪 Verification & Continuous Testing

Run the automated integrity test suite at any time:

```bash
# Verify tooling registry integrity across all domain subfolders
bg3 tools verify --json

# Audit agent skills for registry integration and tool discovery
bg3 tools verify --audit-skills --json

# Run complete regression test suite
python3 -m unittest discover -s tests -p "test_*.py"
```
