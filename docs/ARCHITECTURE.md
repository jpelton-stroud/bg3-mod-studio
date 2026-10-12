# Architecture & Technical Design

This document details the architectural design and structural patterns of the **Baldur's Gate 3 Mod Studio & Mod.io Toolkit**.

---

## Workspace Overview

```text
BaldursGate3/
├── .agents/skills/            # Autonomous subagent skills for BG3 mod tasks
├── docs/                      # Technical guides and architecture specifications
├── mods/                      # Documented mod catalog from mod.io
│   ├── library.md             # Master mod index and feature catalog
│   └── <mod_slug>/            # Whitelisted mod specifications & extracted assets
├── my_mods/                   # Custom authored mods
│   └── <ModName>_<UUID>/      # Standard Larian mod directory package
│       ├── Localization/      # Localization XMLs
│       ├── Mods/<UUID>/       # meta.lsx engine metadata
│       ├── Projects/<UUID>/   # meta.lsx project descriptor
│       └── Public/<UUID>/     # Root stats, scripts, and asset folders
├── build_guides/              # Theorycrafting sandbox (ignored by Git)
├── scripts/                   # Pure Python automation tools
├── .env.example               # Environment variables template
├── .gitignore                 # Production-grade gitignore with whitelist rules
├── setup.sh                   # POSIX setup wizard launcher
└── README.md                  # Project overview & quickstart
```

---

## Core Components

### 1. Mod Scaffolding (`scripts/create_mod_scaffold.py`)
Baldur's Gate 3 mods require exact engine structures recognized by the Larian engine and the Baldur's Gate 3 Toolkit:
- **UUIDv4 Generation**: Automatically generates valid module UUIDs and localization handles.
- **Larian Version64 Calculation**: Encodes version components using bitwise shifts:
  $$\text{Version64} = (\text{major} \ll 55) \mid (\text{minor} \ll 47) \mid (\text{revision} \ll 31) \mid \text{build}$$
- **Engine Descriptors (`meta.lsx`)**: Emits standard Larian v4.8 XML metadata referencing parent dependencies (e.g. `GustavDev` or `UnlockLevelCurve`).
- **Placeholder Assets**: Generates clean 512x512 PNG project thumbnails without external graphics libraries using standard library `zlib` and `struct`.

### 2. Live Synchronization (`scripts/sync_to_game_data.py`)
To test and publish mods in the Baldur's Gate 3 Toolkit, source files must reside in the game's `Data/` directory.
- **Selective Mirroring**:
  - `my_mods/<Mod>/Mods/<UUID>/` $\to$ `Data/Mods/<UUID>/`
  - `my_mods/<Mod>/Projects/<UUID>/` $\to$ `Data/Projects/<UUID>/`
  - `my_mods/<Mod>/Public/<UUID>/` $\to$ `Data/Public/<UUID>/`
  - `my_mods/<Mod>/Localization/` $\to$ `Data/Localization/` and `Data/Mods/<UUID>/Localization/`
- **Idempotency**: Utilizes `filecmp.cmp` to only copy modified or newly created files, preventing unnecessary disk I/O.
- **Watcher Mode**: Listens for file modifications with configurable intervals (`--watch`) for instant hot-reloading during mod development.

### 3. Mod.io Management Suite (`scripts/modio_*.py`)
- **`modio_search.py`**: Queries the mod.io REST API with platform filters (PC, PS5, Xbox Series X|S) and natural language terms.
- **`modio_extract.py`**: Downloads mod archives, inspects PAK and ZIP containers, extracts Larian TXT and XML data files, and generates rich markdown documentation.
- **`modio_update.py`**: Checks for upstream updates on tracked mods in `mods/`.
- **`modio_sync.py`**: Synchronizes personal subscribed mods using mod.io Personal Access Tokens (PAT).

---

## Autonomous Agent Skills (`.agents/skills/`)

The workspace incorporates specialized AI agent skills to streamline complex mod workflows:
- `bg3_create_mod`: Orchestrates multi-agent pipelines to interview, plan, author stats, generate localization, and validate mods.
- `bg3_search_mods`: Searches mod.io, cross-checks against the local library, and checks for conflicts.
- `bg3_check_mod_conflicts`: Evaluates load order constraints, console compatibility, and overlapping overrides.
- `bg3_document_mods`: Downloads and documents multiple mods concurrently.
- `bg3_create_build_guide`: Builds optimized Level 20 build guides pairing custom mod gear with vanilla assets.
- `grill-me`: Conducts interactive design-tree interviews before coding.
