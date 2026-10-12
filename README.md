# Baldur's Gate 3 Mod Studio & Mod.io Toolkit

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform: Cross-Platform](https://img.shields.io/badge/platform-Linux%20%7C%20WSL%20%7C%20Windows-brightgreen.svg)](#prerequisites)
[![mod.io API](https://img.shields.io/badge/mod.io-REST%20v1-orange.svg)](https://mod.io/g/baldursgate3)

An all-in-one workspace for authoring, cataloging, synchronizing, and testing **Baldur's Gate 3** mods on **mod.io**, backed by autonomous AI development workflows.

I started this with the intention of learning how to use AI by helping me keep track of what all the different BG3 mods I had installed actually did, then I started using it to help me theorycraft modded character builds. _Then_ I decided I wanted to make my _own_ mods that built on top of other mods without conflicts.

It has since snowballed into an entire agentic mod studio that runs (almost) completely within VS Code! (you still need to install the official Larian Mod Toolkit in order to actually publish your mods to mod.io)

---

## Features

### Agentic Features

- **🎨 Autonomous Mod Authoring (`bg3_create_mod`, `grill-me`)**:
  Multi-agent pipeline that interviews modders on design intent, structures technical specifications, authors stats and localization XML, and validates file structures against Larian engine standards.
- **🔍 Intelligent Discovery & Conflict Analysis (`bg3_search_mods`, `bg3_check_mod_conflicts`)**:
  Natural-language catalog exploration with automated conflict evaluation, load-order checks, and console compatibility verification against your local mod library.
- **📖 Autonomous Documentation & Cataloging (`bg3_document_mods`, `bg3_update_mod_documentation`)**:
  Concurrent subagent workflows to download, deconstruct, and document community mods into `mods/<slug>/README.md` and refresh `mods/library.md`.
- **⚔️ Build Crafting & BiS Theorycrafting (`bg3_create_build_guide`)**:
  Designs min-maxed Level 20 character build guides integrating modded gear, progression paths, and turn-1 combat sequencing.

### Script-Based Features

- **⚡ Mod Scaffolding (`create_mod_scaffold.py`)**:
  Generates production-grade Larian v4.8 engine metadata (`meta.lsx`), calculates 64-bit version integers, allocates unique UUIDs and localization handles, and produces compliant 512x512 PNG assets with zero external dependencies.
- **🔄 Live Game Data Synchronization (`sync_to_game_data.py`)**:
  Idempotently mirrors mods authored under `my_mods/` directly into your Steam Baldur's Gate 3 `Data/` folder, featuring continuous watch mode (`--watch`) for instant hot-reloading during mod development.
- **🌐 mod.io Management Suite (`modio_*.py`)**:
  Command-line tools to search mod.io with console filters (`modio_search.py`), extract and deconstruct PAK files into clean XML/TXT specs (`modio_extract.py`), sync personal subscriptions (`modio_sync.py`), and check for upstream updates (`modio_update.py`).
- **⚙️ Setup & Environment Wizard (`setup.sh` / `setup_environment.py`)**:
  Interactive setup wizard to detect game installation paths, validate mod.io API credentials, and configure author environments.
- **📚 Curated Mod Library (`mods/library.md`)**:
  Maintains detailed feature documentation and stat specifications for documented community mods across Gear, Spells, Classes, Progression, and Utilities.

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
│   └── <ModName>_<UUID>/      # Larian mod package (Projects, Mods, Public, Localization)
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
