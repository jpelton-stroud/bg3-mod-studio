# System Architecture & Technical Design

This document details the system architecture, component layering, data pipelines, and engine structural contracts of the **Baldur's Gate 3 Mod Studio & Mod.io Toolkit**.

> [!NOTE]
> For user guides, autonomous agent slash commands, example prompts, and the CLI flags reference for all 27 studio tools, refer to the [Features & Functionality Guide](docs/FEATURES.md).

---

## 1. System Topology & Multi-Tier Architecture

The studio operates across four architectural layers: the **Agent & Orchestration Tier**, the **Automation & Tooling Tier**, the **Workspace State & Data Tier**, and the **Engine & Game Boundary**.

```mermaid
flowchart TD
    subgraph Tier1["1. Agent & Orchestration Tier (.agents/skills/)"]
        Agents["15 Autonomous Subagent Skills\n(/bg3_create_mod, /bg3_diagnose_mod, /bg3_test_mod, etc.)"]
        GrillMe["Clarification Engine\n(/grill-me Interactive Trees)"]
    end

    subgraph Tier2["2. Automation & Tooling Tier (scripts/)"]
        Router["Discovery & Dispatch Hub\n(scripts/tools.py - 27 tools)"]
        SharedLib["Shared Engine Package\n(scripts/lib/: lspk, parsers, paths, modio)"]
        Scaffold["Scaffolding & Authoring\n(create_mod_scaffold, scaffold_stat, etc.)"]
        Packaging["Binary Packaging & Sync\n(pack_mod_pak, sync_to_game_data)"]
        Diagnostics["Validation & Doctor\n(validate_mod, check_mod_conflicts, diagnose_logs)"]
        ModioSuite["Mod.io REST Client\n(modio_search, modio_extract, modio_update_metadata)"]
        QueryEngine["High-Speed Query Engine\n(query_mod_database)"]
    end

    subgraph Tier3["3. Workspace State & Data Tier"]
        MyMods["Custom Mods Workspace\n(my_mods/<mod-slug>/)"]
        ModsLib["Community Mod Library\n(mods/library.md & specs)"]
        Sandboxes["Theorycrafting Sandbox\n(build_guides/)"]
        Config[".env Configuration\n(API Keys & Paths)"]
    end

    subgraph Tier4["4. Engine & Game Boundary"]
        GameData["Larian Game Data Directory\n(Baldurs Gate 3/Data/)"]
        ProfileSettings["Active Player Profile\n(modsettings.lsx)"]
        ModioRemote["Remote mod.io REST API\n(v1/games/6715)"]
        Distribution["LSPK v18 Package\n(*.pak)"]
    end

    Tier1 -->|Routes or executes| Router
    Router --> SharedLib
    Router --> Scaffold
    Router --> Packaging
    Router --> Diagnostics
    Router --> ModioSuite
    Router --> QueryEngine

    Scaffold -->|Generates source| MyMods
    Packaging -->|Mirrors source & compiled .loca| GameData
    Packaging -->|Compiles package| Distribution
    Diagnostics -->|Linters & audits| MyMods
    Diagnostics -->|Inspects load order & saves| ProfileSettings
    ModioSuite -->|Queries & updates metadata| ModioRemote
    ModioSuite -->|Extracts & indexes| ModsLib
    QueryEngine -->|Fuzzy search / BiS| ModsLib
    Tier1 -->|Streams matrices| Sandboxes
```

---

## 2. Core Workflows & Data Pipelines

### 5-Stage Shift-Left & Loopback Lifecycle

Custom mod authoring follows a strict 5-stage pipeline with Progressive Gate Handoffs and loopback diagnostics:

```mermaid
flowchart TD
    S1["Stage 1: Creation (/bg3_create_mod)
- /grill-me interview & specification plan
- Scaffolding & parallel subagents (stats, progressions, loca, docs)
- Read-only smoke check on my_mods/<slug>/"]
    
    S2["Stage 2: Diagnostics (/bg3_diagnose_mod)
- Phase 2A: Static pre-flight, Data/ sync & Glasses.exe log launch
- Phase 2B: Runtime log triage, auto-fixes & verification loop"]
    
    S3["Stage 3: In-Game Testing (/bg3_test_mod)
- Phase 3A: Clean smoke test with dependency closure (--with-deps / --isolate)
- Phase 3B: Multi-mod campaign integration & save audit (optional gate)
- User in-game verification & loopback/release gate"]
    
    S4["Stage 4: Release Preparation (/bg3_release_prep)
- bump_mod_version (atomic meta.lsx & README sync)
- validate_mod --strict & localization prune/compile
- render_modio_description (GFM HTML table generation)
- Final Data/ sync & dist/<slug>.pak packaging"]
    
    S5["Stage 5: Post-Release (/bg3_post_release)
- modio_update_metadata (2-stage tag/setting preview + confirmation)
- Optional: modio_create_collection"]
    
    S1 -->|Stage 1 Gate| S2
    S2 -->|Stage 2 Gate| S3
    S3 -->|Testing Passed| S4
    S3 -.->|Issues Found (Loopback)| S2
    S4 -->|Publish in Toolkit| S5
```

### Community Mod Discovery & Ingestion Pipeline

When exploring community mods on mod.io, the ingestion pipeline decompresses upstream packages, parses engine files, extracts item and spell definitions, and builds an indexed catalog without runtime dependencies.

```mermaid
flowchart LR
    Remote["mod.io REST API\n(v1/games/6715)"] -->|modio_search.py| SearchResults["Candidate Mod\n(Platform Filtered)"]
    SearchResults -->|modio_extract.py| DL["Download Archive\n(.pak / .zip)"]
    DL --> Extract["Pure-Python Unpacker\n(zlib + struct)"]
    Extract --> Parse["Larian Engine Parsers\n(XML & TXT)"]
    Parse --> Specs["mods/<slug>/README.md\n(Rich Markdown Spec)"]
    Parse --> Index["Master Catalog\n(mods/library.md: six columns)"]
    Index --> FastDB["query_mod_database.py\n(Sub-10ms Fuzzy Search)"]
```

---

## 3. Larian Engine Structural Contracts & Binary Standards

### Larian Engine Package Hierarchy

To ensure compatibility with the official Larian Toolkit and game runtime, all custom authored mods in `my_mods/<mod-slug>/` follow this exact four-root layout:

```text
my_mods/<mod-slug>/
├── Mods/<ModName>_<UUID>/
│   └── meta.lsx                      # Primary engine descriptor (ModuleInfo & dependencies)
├── Projects/<ModName>_<UUID>/
│   └── meta.lsx                      # Larian Toolkit project descriptor
├── Public/<ModName>_<UUID>/
│   ├── RootTemplates/
│   │   └── _merged.lsx               # 3D GameObject templates & visual asset links
│   ├── Stats/Generated/Data/
│   │   ├── Armor.txt                 # Armor, jewelry, and clothing stats
│   │   ├── Passive.txt               # Passives, boosts, and conditions
│   │   ├── Spell_*.txt               # Spells, cantrips, and abilities
│   │   └── Weapon.txt                # Weapons and damage profiles
│   ├── Progressions/
│   │   └── Progressions.lsx          # Class, subclass, and level progression nodes
│   └── GUI/
│       └── Icons.lsx                 # Texture atlas UV mappings for custom icons
├── Localization/
│   └── English/
│       └── <ModName>.xml             # String handles (contentuid) and English text
├── README.md                         # Architecture notes & documentation
└── thumbnail.png                     # Standard 512x512 project thumbnail
```

### Larian 64-bit Version Encoding (`Version64`)

Larian's engine encodes semantic versioning into an unsigned 64-bit integer (`Version64`) using bitwise shifts. The formula implemented by `scripts/create_mod_scaffold.py` and `scripts/bump_mod_version.py` is:

$$\text{Version64} = (\text{major} \ll 55) \mid (\text{minor} \ll 47) \mid (\text{revision} \ll 31) \mid \text{build}$$

```text
 63      55 54      47 46               31 30                         0
┌──────────┬──────────┬───────────────────┬────────────────────────────┐
│  Major   │  Minor   │     Revision      │           Build            │
│ (8 bits) │ (8 bits) │     (16 bits)     │         (31 bits)          │
└──────────┴──────────┴───────────────────┴────────────────────────────┘
```

### Pure-Python LSPK v18 Binary Packaging (`pack_mod_pak.py`)

Rather than relying on Windows-exclusive binaries (`LSLib/divine.exe`) or running through `wine`, the workspace implements a pure Python packager for Larian's **LSPK v18** format:

- **Zero External Dependencies**: Implemented strictly with Python's standard library `struct`, `zlib`, and `hashlib`.
- **Package Header**: Writes standard 128-byte LSPK v18 signature (`LSPK`), file version, and file table metadata offset.
- **File Entry Table**: Compresses individual files with `zlib`, calculates uncompressed and compressed sizes, CRC32/MD5 checksums, and relative archive offsets.
- **Cross-Platform Compatibility**: Packages created with `pack_mod_pak.py` mount identically across Linux, macOS, Windows, and game consoles (PlayStation 5, Xbox Series X|S).

---

## 4. Synchronization & File Integrity Architecture

### Idempotent Selective Synchronization (`sync_to_game_data.py`)

The live synchronization system mirrors source files from `my_mods/<mod-slug>/` into the game installation directory (`Baldurs Gate 3/Data/`) for in-engine testing:

1. **Selective Root Mapping**:
   - `my_mods/<mod-slug>/Mods/<ModName>_<UUID>/` $\to$ `Data/Mods/<ModName>_<UUID>/`
   - `my_mods/<mod-slug>/Projects/<ModName>_<UUID>/` $\to$ `Data/Projects/<ModName>_<UUID>/`
   - `my_mods/<mod-slug>/Public/<ModName>_<UUID>/` $\to$ `Data/Public/<ModName>_<UUID>/`
   - `my_mods/<mod-slug>/Localization/` $\to$ `Data/Localization/` and `Data/Mods/<ModName>_<UUID>/Localization/`
2. **Differential Comparison Engine**:
   - Compares file metadata (modification times and sizes) and evaluates content differences using `filecmp.cmp(shallow=False)` before writing.
   - Prevents unnecessary write cycles and reduces disk I/O when working with solid-state drives or network storage.
3. **Continuous Hot-Reload Watcher (`--watch`)**:
   - Polls mod source trees with configurable sleep intervals (default 1.0s).
   - Automatically synchronizes newly saved files so changes appear immediately in the Larian Toolkit or next game reload.

### Master Mod Indexing & Database Queries (`query_mod_database.py`)

The community mod library (`mods/`) indexes over 2,200 unique community gear items, passives, spells, and boosts:

- **Aggregation Pipeline**: `scripts/update_library_catalog.py` crawls all `mods/<slug>/README.md` files, parses mod.io IDs, titles, descriptions, feature counts, and directory slugs, and compiles the categorized six-column `mods/library.md` with relative spec links.
- **Query Optimization**: `scripts/query_mod_database.py` evaluates queries against cached catalog structures using in-memory tokenization and regex matching. Lookups complete in under 10ms, allowing agent workflows to perform real-time Best-in-Slot gear evaluation without noticeable latency.

---

## 5. Architectural Principles & Isolation

- **Zero-Dependency Philosophy**: All 27 tools in `scripts/` use strictly the Python 3.10+ standard library. They run out-of-the-box on Linux, WSL, and Windows without virtual environment setups or `pip install` requirements.
- **Safe Sandboxing**:
  - Custom authored mods remain safe in `my_mods/` and tracked by version control.
  - Theorycrafting scratchpads reside in `build_guides/` and are explicitly excluded from Git to prevent repository bloat.
  - Backup copies (`.bak`) are created automatically whenever localization handles or `modsettings.lsx` orders are mutated.
- **Path Portability**: Path resolvers inspect `.env` configurations (`BG3_DATA_DIR`) and environment variables to handle POSIX, Windows UNC, and WSL `/mnt/c/` drive mount variations seamlessly.
