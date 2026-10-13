# Baldur's Gate 3 Mod Studio — Automation Tooling & Registry

This directory contains the deterministic automation engine for the **Baldur's Gate 3 Mod Studio**. 

All tools are engineered with **100% Pure Python Standard Library** (zero `pip install`, zero external dependencies, cross-platform WSL/Linux/Windows) and expose structured `--json` outputs for AI agent orchestration.

---

## 🧭 Tool Discovery & Execution Hub (`tools.py`)

The studio includes a centralized discovery and dispatch hub: [`scripts/tools.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/tools.py) powered by the machine-readable catalog [`scripts/registry.json`](file:///home/jpstroud/projects/BaldursGate3/scripts/registry.json).

### Quick Start

```bash
# 1. Search tools by natural language intent or keyword
python3 scripts/tools.py --search "stat handles"
python3 scripts/tools.py --search "turn 1 dpr"
python3 scripts/tools.py --search "unpack pak"

# 2. Inspect full CLI options, flags, and schema for any tool
python3 scripts/tools.py --info scaffold-stat
python3 scripts/tools.py --info pack-pak

# 3. List all 24 tools or filter by category
python3 scripts/tools.py --list
python3 scripts/tools.py --list --category authoring

# 4. Dispatch tool execution via alias
python3 scripts/tools.py run query-db --slot Weapon --limit 5 --json

# 5. Verify registry integrity and test all script entry points
python3 scripts/tools.py --verify

# 6. Audit agent skills for registry integration and tool discovery
python3 scripts/tools.py --audit-skills
```


---

## 🗂️ Tool Catalog by Category

### 1. Authoring & Content Scaffolding
Tools for generating game content, mechanics, items, and progressions.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `scaffold-mod` | [`create_mod_scaffold.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/create_mod_scaffold.py) | Scaffolds complete BG3 mod directory trees (`Mods/`, `Projects/`, `Localization/`, `meta.lsx`). |
| `scaffold-stat` | [`scaffold_stat_entry.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/scaffold_stat_entry.py) | Scaffolds Larian stat entries with automatic string handle allocation in `Localization/English/*.xml`. |
| `scaffold-progression` | [`scaffold_progression_node.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/scaffold_progression_node.py) | Scaffolds and merges Larian v4.8 Progression and companion `SpellLists.lsx` nodes with automatic `TableUUID` resolution. |
| `scaffold-template` | [`scaffold_root_template.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/scaffold_root_template.py) | Binds stat entries to 3D visual GameObjects in `_merged.lsx` linking meshes, collision, and handles. |
| `inject-drop` | [`inject_treasure_table.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/inject_treasure_table.py) | Injects custom mod items into Tutorial Chest, Camp Chest, or early vendors via `TreasureTable.txt`. |
| `generate-icons` | [`generate_icon_atlas.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/generate_icon_atlas.py) | Calculates normalized UV coordinates and generates `GUI/Icons.lsx` definitions for custom icon grids. |
| `compat-patch` | [`generate_compat_patch.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/generate_compat_patch.py) | Auto-generates compatibility patches (standalone or Compatibility Framework) between colliding mods. |

---

### 2. Packaging & Game Deployment
Tools for packaging archives and syncing mods into the game engine.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `pack-pak` | [`pack_mod_pak.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/pack_mod_pak.py) | Pure-Python LSPK v18 `.pak` packager with zlib compression (no LSLib/Wine needed). |
| `sync-game` | [`sync_to_game_data.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/sync_to_game_data.py) | Syncs custom mods from `my_mods/` to the Steam `Baldurs Gate 3/Data` directory with build bumping. |

---

### 3. Diagnostics, Validation & Auditing
Tools for health checks, syntax validation, collision detection, and save audits.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `validate` | [`validate_mod.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/validate_mod.py) | Deterministic static validator verifying LSX XML syntax, handle integrity, and assets. |
| `check-conflicts` | [`check_mod_conflicts.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/check_mod_conflicts.py) | Static entry collision analyzer checking stat overlaps and console-incompatible DLLs. |
| `sync-loca` | [`sync_localization.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/sync_localization.py) | Prunes orphaned string handles (`.bak` backups), audits missing handles, and syncs multi-language XMLs. |
| `inspect-save` | [`inspect_save_game.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/inspect_save_game.py) | Extracts mod load orders from `.lsv` saves and audits against `modsettings.lsx` to diagnose crashes. |

---

### 4. Management & Environment
Tools for load order configuration, versioning, and publishing metadata.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `load-order` | [`manage_load_order.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/manage_load_order.py) | Inspects, activates, disables, and validates mod load order in `modsettings.lsx`. |
| `bump-version` | [`bump_mod_version.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/bump_mod_version.py) | Increments semantic versions and encodes 64-bit uint `Version64` across `meta.lsx`. |
| `gen-metadata` | [`generate_mod_metadata.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/generate_mod_metadata.py) | Extracts publication metadata and generates BBCode descriptions, tags, and changelogs. |
| `setup-env` | [`setup_environment.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/setup_environment.py) | Setup wizard checking Python, Steam BG3, AppData, and mod.io configuration. |

---

### 5. Library & Database Search
Tools for querying cataloged community mods and interacting with mod.io.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `query-db` | [`query_mod_database.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/query_mod_database.py) | High-speed (sub-10ms) query engine searching 2,200+ mod items, passives, spells, and boosts. |
| `update-catalog` | [`update_library_catalog.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/update_library_catalog.py) | Compiles and validates the master community catalog in [`mods/library.md`](file:///home/jpstroud/projects/BaldursGate3/mods/library.md). |
| `modio-search` | [`modio_search.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/modio_search.py) | Searches mod.io with natural language and platform filters (`console`, `windows`, etc.). |
| `modio-sync` | [`modio_sync.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/modio_sync.py) | Downloads and syncs subscribed mods from mod.io into `mods/`. |
| `modio-update` | [`modio_update.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/modio_update.py) | Checks tracked mods against remote mod.io releases and updates specifications. |
| `modio-extract` | [`modio_extract.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/modio_extract.py) | Unpacks LSPK `.pak` archives, extracts files, and indexes mod capabilities. |

---

### 6. Theorycrafting & Build Simulation
Tools for mathematical combat modeling and multiclass rule engines.

| Command Alias | Script | Description |
| :--- | :--- | :--- |
| `simulate-build` | [`simulate_build_synergy.py`](file:///home/jpstroud/projects/BaldursGate3/scripts/simulate_build_synergy.py) | Simulates Turn 1 combat sequences (DPR), Spell Save DC ceilings, and multiclass slot matrices. |

---

## 🤖 AI Agent Integration Protocol

When an AI agent or subagent receives a request that does not match a hardcoded skill:

1. **Query Tool Registry**:
   ```bash
   python3 scripts/tools.py --search "<intent description>" --json
   ```
2. **Inspect Options**:
   ```bash
   python3 scripts/tools.py --info <matched_tool> --json
   ```
3. **Execute Deterministically**:
   ```bash
   python3 scripts/tools.py run <matched_tool> [args...] --json
   ```
   *(or run the script directly: `python3 scripts/<matched_script>.py [args...] --json`)*

---

## 🪙 Token Optimization & Cost Management

The tooling suite and agent skills are engineered with token mitigation protocols to minimize API costs and context bloat across long sessions:

### 1. Subagent Model Tiering (`Model: "flash"`)
Concurrent subagent workers are pinned to `"Model": "flash"` across orchestrators:
- `bg3_create_mod`: Stats, Progression, Localization, and Documentation workers.
- `bg3_document_mods`: Individual Mod Documenter workers.
- `bg3_update_mod_documentation`: Mod Updater check/refresh workers.
- `bg3_search_mods`: Per-mod candidate conflict checkers.

*Cost impact*: **80%–90% reduction** in token expenditure for background subagent tasks.

### 2. Compact Discovery & Query Formats
- **Discovery Hub (`scripts/tools.py`)**: `tools.py --list --json` emits a compact manifest (83.5% token reduction: ~1,689 tokens vs. ~10,289 tokens). Full schemas are retrieved on demand with `tools.py --info <alias>` or `tools.py --list --full`.
- **Database Search (`scripts/query_mod_database.py`)**: Default limit reduced from 50 to 10 entries; `--compact` flag eliminates verbose handle/UUID dumps (~850 tokens vs. up to 15,000 tokens).
- **Conflict Analysis (`scripts/check_mod_conflicts.py`)**: `--summary` flag emits high-level compatibility verdicts and clean collision lists (95.8% reduction: ~60 tokens vs. ~1,445 tokens).

### 3. Artifact-First Streaming
High-volume generation tasks (such as `bg3_create_build_guide`) follow the **Artifact-First** protocol:
- Full 20-level progression tables, stat matrices, and complete gear catalogs are written directly to disk (`build_guides/<build_slug>.md`).
- Only an executive summary (class concept, key gear linchpins, Turn 1 rotation DPR) is rendered into chat, avoiding thousands of redundant context tokens.

### 4. Session Lifecycle & Hygiene
- For distinct features, start fresh chat sessions or clear working context to avoid carrying forward large multi-turn history.
- Use `scripts/tools.py --search` or direct script execution rather than dumping full registry schemas into conversation memory.

---

## 🧪 Verification & Continuous Testing

Run the automated integrity test at any time:

```bash
# Verify tooling registry integrity
python3 scripts/tools.py --verify

# Audit agent skills for registry integration
python3 scripts/tools.py --audit-skills
```

This verifies that:
1. Every script on disk in `scripts/*.py` is registered in `registry.json`.
2. Every registered tool exists on disk.
3. Every script compiles without Python syntax errors.
4. Every script cleanly handles `--help` CLI invocation.
5. Every agent skill in `.agents/skills/` uses valid registered scripts and provides dynamic tool discovery guidance.

