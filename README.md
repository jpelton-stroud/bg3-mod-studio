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
- **Master Mod Catalog**: Track mods centrally in `mods/library.md` using Mod Id, Mod Name, Mod Slug, Description, Features Documented, and Spec Link; unverified IDs remain blank.
- **Conflict & Load Order Analysis**: Proactively audit candidate mods for stat collisions, duplicate UUIDs, and console load order dependencies before installing (`/bg3_check_mod_conflicts`).
- **Upstream Update Tracking**: Check for upstream patches and updates across tracked mods, refreshing documentation without manual data re-entry (`/bg3_update_mod_documentation`, `scripts/modio_update.py`).

### Build Crafting

- **Level 1–20 Progression Design**: Plan complete 20-level multiclass builds leveraging expanded progression frameworks like _UnlockLevelCurve_ (`/bg3_create_build_guide`).
- **Catalog-Wide BiS Gear Queries**: Query the documented mod library for Best-in-Slot weapons, armor, passives, and spell synergies tailored to specific build archetypes (`/bg3_query_gear`).
- **Tactical Combat Sequences**: Script turn-by-turn combat openers and action economy allocations (actions, bonus actions, reactions, spell slots) to maximize tactical output.
- **Sandboxed Build Guides**: Keep build guides organized and isolated in `build_guides/` without cluttering version control or game directories.

### Custom Mod Authorship (5-Stage Shift-Left Lifecycle)

- **Stage 1 (Creation: `/bg3_create_mod`)**: Autonomous scaffolding under `my_mods/<slug>/`, parallel subagents for stats/progressions/loca/docs, and read-only validation.
- **Stage 2 (Diagnostics & Toolkit Sync: `/bg3_diagnose_mod`)**: Phase 2A static checks & collision triage on `my_mods/` -> Phase 2B sync to `<Game>/Data/` (with automatic binary `.loca` compilation) & BG3 Toolkit (`Glasses.exe`) log diagnosis.
- **Stage 3 (In-Game Testing: `/bg3_test_mod`)**: Standalone `.pak` packaging (`--publish-local`), load order activation (`/bg3_manage_load_order`), and save-game compatibility audits (`scripts/inspect_save_game.py`).
- **Stage 4 (Release Prep: `/bg3_release_prep`)**: Atomic semantic version bump, strict validation, GFM HTML description rendering (`scripts/render_modio_description.py`), and distribution `.pak` packaging.
- **Stage 5 (Post-Release: `/bg3_post_release`)**: Review allowed tags, preview API mutations, and publish metadata to mod.io via REST API (`scripts/modio_update_metadata.py`).

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
├── .agents/skills/            # Autonomous AI agent workflows (15 specialized skills)
├── docs/                      # Technical documentation & guides
│   ├── ARCHITECTURE.md        # System architecture and design
│   ├── FEATURES.md            # Features, workflows, and example agent prompts
│   ├── MOD_CREATION_WORKFLOW.md # Step-by-step mod authoring guide
│   └── MODIO_INTEGRATION.md   # mod.io API and library reference
├── mods/                      # Documented mod specifications
│   ├── library.md             # Master mod catalog (6-column categorized table)
│   └── <mod_slug>/            # Whitelisted mod specifications & data
├── my_mods/                   # Custom authored mods
│   └── <mod_slug>/            # Mod package (Projects, Mods, Public, Localization)
├── build_guides/              # Sandbox for Level 20 build crafting (ignored by Git)
├── scripts/                   # Pure Python automation tooling suite (27 CLI tools)
│   ├── lib/                   # Shared engine parsers, LSPK packager, and mod.io client
│   ├── tools.py               # Tool discovery and execution hub
│   └── registry.json          # Machine-readable tools registry
├── .env.example               # Environment variables template
├── .gitignore                 # Production-grade gitignore with whitelist rules
├── setup.sh                   # Setup wizard launcher
├── CONTRIBUTING.md            # Contribution guidelines
├── CODE_OF_CONDUCT.md         # Contributor Covenant v2.1
├── LICENSE                    # MIT License
└── README.md                  # Project overview
```

---

## CLI Reference & Tool Hub

Explore, query, and run any of the 27 registered automation tools via the centralized discovery hub:

```bash
# Discover tools by natural language query
python3 scripts/tools.py --search "stat handles"
python3 scripts/tools.py --search "load order"

# Inspect tool flags and schemas
python3 scripts/tools.py --info scaffold-stat
python3 scripts/tools.py --info pack-pak

# Run any tool directly or through the dispatcher
python3 scripts/tools.py run query-db --slot Weapon --limit 5 --json
```

### 5-Stage Custom Mod Lifecycle

```bash
# Stage 1: Scaffold and author
python3 scripts/create_mod_scaffold.py --name "ArcaneProgression" --json

# Stage 2: Pre-flight validation & game sync
python3 scripts/validate_mod.py --mod arcane-progression --json
python3 scripts/sync_to_game_data.py --mods arcane-progression --json
python3 scripts/diagnose_toolkit_logs.py --mod arcane-progression --severity warning --json

# Stage 3: In-game testing & load order
python3 scripts/pack_mod_pak.py --mod arcane-progression --publish-local --json
python3 scripts/manage_load_order.py --enable arcane-progression --validate --json
python3 scripts/inspect_save_game.py --audit --json

# Stage 4: Version bump & release prep
python3 scripts/bump_mod_version.py --mod arcane-progression --patch --json
python3 scripts/render_modio_description.py --mod arcane-progression --write --json
python3 scripts/pack_mod_pak.py --mod arcane-progression --out dist/arcane-progression.pak --json

# Stage 5: Post-release metadata & tags
python3 scripts/modio_update_metadata.py --mod arcane-progression --tags "Classes,Spells" --json
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
