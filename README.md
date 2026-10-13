# Baldur's Gate 3 Mod Studio & Mod.io Toolkit

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Cross-Platform](https://img.shields.io/badge/platform-Linux%20%7C%20WSL%20%7C%20Windows-brightgreen.svg)](#prerequisites)
[![mod.io API](https://img.shields.io/badge/mod.io-REST%20v1-orange.svg)](https://mod.io/g/baldursgate3)

An all-in-one workspace for authoring, cataloging, synchronizing, and testing **Baldur's Gate 3** mods on **mod.io**, backed by autonomous AI development workflows.

I started this with the intention of learning how to use AI by helping me keep track of what all the different BG3 mods I had installed actually did, then I started using it to help me theorycraft modded character builds. _Then_ I decided I wanted to make my _own_ mods that built on top of other mods without conflicts.

It has since snowballed into an entire agentic mod studio that runs (almost) completely within VS Code! (you still need to install the official Larian Mod Toolkit in order to actually publish your mods to mod.io)

---

## Features Overview

This project focuses on a conversational, AI First approach to Mod Discovery, Build/Theory Crafting, and Custom Mod Authorship.

Looking for new mods to spice up your next playthrough? Run `/bg3_search_mods` and tell it roughly what you're up for. Need help optimizing your party's leveling paths and gear loadouts across dozens of installed mods? Launch `/bg3_create_build_guide` and tell it what you want out of the character. Want to create your _own_ mod to customize your character's journey? Start with `/bg3_create_mod`, describe your vision, and see where it takes you!

For a deep-dive into feature & functionality specifics, as well as example agent prompts, see [docs/FEATURES](docs/FEATURES.md).

### Mod Discovery & Cataloging

- **Smart mod.io Search & Filtering**: Discover community mods across PC, PS5, and Xbox Series X|S using natural language queries and compatibility filters (`/bg3_search_mods`, `scripts/modio_search.py`).
- **Automated Unpacking & Asset Extraction**: Download and decompress PAK/ZIP archives on demand, extracting engine XMLs, localization tables, and game stats into human-readable markdown (`/bg3_document_mods`, `scripts/modio_extract.py`).
- **Master Mod Catalog**: Track installed and candidate mods centrally in `mods/library.md`, maintaining verified feature summaries, UUIDs, and mod.io metadata.
- **Conflict & Load Order Analysis**: Proactively audit candidate mods for stat collisions, duplicate UUIDs, and console load order dependencies before installing (`/bg3_check_mod_conflicts`).
- **Upstream Update Tracking**: Check for upstream patches and updates across tracked mods, refreshing documentation without manual data re-entry (`/bg3_update_mod_documentation`, `scripts/modio_update.py`).

### Build Crafting

- **Level 1–20 Progression Design**: Plan complete 20-level multiclass builds leveraging expanded progression frameworks like _UnlockLevelCurve_ (`/bg3_create_build_guide`).
- **Catalog-Wide BiS Gear Queries**: Query the documented mod library for Best-in-Slot weapons, armor, passives, and spell synergies tailored to specific build archetypes (`/bg3_query_gear`).
- **Tactical Combat Sequences**: Script turn-by-turn combat openers and action economy allocations (actions, bonus actions, reactions, spell slots) to maximize tactical output.
- **Sandboxed Build Guides**: Keep build guides organized and isolated in `build_guides/` without cluttering version control or game directories.

### Custom Mod Authorship

- **Autonomous Mod Scaffolding**: Generate engine-compliant Larian packages under `my_mods/<mod_slug>/` with valid UUIDv4 identifiers, bitwise Larian `Version64` calculation, and valid `meta.lsx` descriptors (`/bg3_create_mod`, `scripts/create_mod_scaffold.py`).
- **Zero-Dependency Asset Generation**: Automatically produce clean 512x512 PNG thumbnails using Python's standard library (`zlib`/`struct`) with no PIL/Pillow dependency required.
- **Two-Way Live Sync & Hot Reload**: Mirror source mods directly into your game's `Data/` directory with selective idempotency and watcher support for live reload while authoring (`scripts/sync_to_game_data.py`).
- **Active Load Order Control**: Inspect, activate, deactivate, and reorder mods directly within `modsettings.lsx` without opening external managers (`/bg3_manage_load_order`).
- **Diagnostics & Toolkit Release Preparation**: Run static validation checks for missing localization or corrupted stat references (`/bg3_diagnose_mod`), then bump versions and prepare release assets for the official Larian Toolkit (`/bg3_release_prep`).

---

## Quickstart

### 1. Prerequisites

- **Python 3.10+** (uses standard library only—no external pip dependencies required).
- **Baldur's Gate 3** (installed via Steam on WSL, Linux, or Windows).
- **mod.io Account** (API Key & Personal Access Token from [mod.io/me/access](https://mod.io/me/access)).

### 2. Run the Interactive Setup Wizard

Run the setup script to configure your environment variables:

```bash
./setup.sh
```

The wizard will:

1. Prompt for your `MODIO_API_KEY` and optionally test it live against the mod.io Baldur's Gate 3 API.
2. Prompt for your `MODIO_PAT` (Personal Access Token).
3. Detect your OS/WSL environment and configure your game's `Data` path (`BG3_DATA_DIR`).
4. Set your default mod author name (`BG3_MOD_AUTHOR`).
5. Save your settings to `.env`.
6. (Optional) Link a remote GitHub repository via GitHub CLI (`gh`).

You can review your configuration anytime with:

```bash
./setup.sh --check
```

---

## Directory Layout

```text
BaldursGate3/
├── .agents/skills/            # Autonomous AI agent workflows
├── docs/                      # Technical documentation & guides
│   ├── ARCHITECTURE.md        # System architecture and design
│   ├── MOD_CREATION_WORKFLOW.md # Step-by-step mod authoring guide
│   └── MODIO_INTEGRATION.md   # mod.io API and library reference
├── mods/                      # Documented mod specifications
│   ├── library.md             # Master mod catalog
│   └── <mod_slug>/            # Whitelisted mod specifications & data
├── my_mods/                   # Custom authored mods
│   └── <mod_slug>/            # Mod package (Projects, Mods, Public, Localization)
├── build_guides/              # Sandbox for Level 20 build crafting (ignored by Git)
├── scripts/                   # Pure Python automation tools
├── .env.example               # Environment variables template
├── .gitignore                 # Production-grade gitignore with whitelist rules
├── setup.sh                   # Setup wizard launcher
├── CONTRIBUTING.md            # Contribution guidelines
├── CODE_OF_CONDUCT.md         # Contributor Covenant v2.1
├── LICENSE                    # MIT License
└── README.md                  # Project overview
```

---

## CLI Reference

### Mod Creation & Scaffolding

```bash
# Scaffold a new mod
python3 scripts/create_mod_scaffold.py --name "ArcaneProgression" --description "Expanded arcane progression"

# Scaffold a mod dependent on UnlockLevelCurve (Levels 13-20)
python3 scripts/create_mod_scaffold.py --name "EldritchAscension" --unlock-level-curve
```

### Live Syncing to Game Data

```bash
# Preview files that would be synced
python3 scripts/sync_to_game_data.py --dry-run

# Perform one-time synchronization
python3 scripts/sync_to_game_data.py

# Watch mode for automatic synchronization on file save
python3 scripts/sync_to_game_data.py --watch
```

### mod.io Exploration & Extraction

```bash
# Search for mods on mod.io
python3 scripts/modio_search.py "paladin"

# Search for console-compatible mods (PS5 or Xbox)
python3 scripts/modio_search.py "spells" --platform ps5

# Download, extract, and document a mod by ID
python3 scripts/modio_extract.py --mod-id 4166963 --output-dir mods/unlocklevelcurve

# Synchronize personal subscribed mods
python3 scripts/modio_sync.py --list
```

---

## Documentation

- [Architecture & Technical Design](docs/ARCHITECTURE.md)
- [Mod Creation Workflow Guide](docs/MOD_CREATION_WORKFLOW.md)
- [mod.io Integration & Reference Library](docs/MODIO_INTEGRATION.md)

---

## Contributing

Contributions are welcome! Please check our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before opening a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).
Baldur's Gate 3 is a registered trademark of Larian Studios. This toolkit is an unofficial community development project.
