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

Looking for new mods to spice up your next playthrough? Run `/bg3-search-mods` and tell it roughly what you're up for. Need help optimizing your party's leveling paths and gear loadouts across dozens of installed mods? Launch `/bg3-create-build-guide` and tell it what you want out of the character. Want to create your _own_ mod to customize your character's journey? Start with `/bg3-create-mod`, describe your vision, and see where it takes you!

For a deep-dive into feature & functionality specifics, as well as example agent prompts, see [docs/FEATURES](docs/FEATURES.md).

### Mod Discovery & Cataloging

- **Smart mod.io Search & Filtering**: Discover community mods across PC, PS5, and Xbox Series X|S using natural language queries and compatibility filters (`/bg3-search-mods`, `bg3 modio search`).
- **Automated Unpacking & Asset Extraction**: Download and decompress PAK/ZIP archives on demand, extracting engine XMLs, localization tables, and game stats into human-readable markdown (`/bg3-document-mods`, `bg3 modio extract`).
- **Master Mod Catalog**: Track mods centrally in your externalized User Content Studio (`$XDG_DOCUMENTS_DIR/BG3_Mod_Studio/Mods/subscribed/library.md`) using Mod Id, Mod Name, Mod Slug, Description, Features Documented, and Spec Link; unverified IDs remain blank.
- **Conflict & Load Order Analysis**: Proactively audit candidate mods for stat collisions, duplicate UUIDs, and console load order dependencies before installing (`/bg3-check-mod-conflicts`).
- **Upstream Update Tracking**: Check for upstream patches and updates across tracked mods, refreshing documentation without manual data re-entry (`/bg3-update-mod-documentation`, `bg3 modio update`).

### Build Crafting

- **Level 1–20 Progression Design**: Plan complete 20-level multiclass builds leveraging expanded progression frameworks like _UnlockLevelCurve_ (`/bg3-create-build-guide`).
- **Catalog-Wide BiS Gear Queries**: Query the documented mod library for Best-in-Slot weapons, armor, passives, and spell synergies tailored to specific build archetypes (`/bg3-query-gear`).
- **Tactical Combat Sequences**: Script turn-by-turn combat openers and action economy allocations (actions, bonus actions, reactions, spell slots) to maximize tactical output.
- **Sandboxed Build Guides**: Keep build guides organized and isolated in `BG3_Mod_Studio/Build_Guides/` without cluttering version control or game directories.

### Custom Mod Authorship (5-Stage Shift-Left Lifecycle)

- **Stage 1 (Creation: `/bg3-create-mod`)**: Autonomous scaffolding under `BG3_Mod_Studio/Mods/authored/<slug>/`, parallel subagents for stats/progressions/loca/docs, and read-only validation.
- **Stage 2 (Diagnostics & Toolkit Sync: `/bg3-diagnose-mod`)**: Phase 2A static checks, game data sync (with binary `.loca` compilation), and Toolkit (`Glasses.exe`) log generation prompt -> Phase 2B runtime log diagnosis, automated fixes, and verification loop.
- **Stage 3 (In-Game Testing: `/bg3-test-mod`)**: Standalone `.pak` packaging (`--publish-local`), load order activation (`/bg3-manage-load-order`), and save-game compatibility audits (`bg3 save inspect`).
- **Stage 4 (Release Prep: `/bg3-release-prep`)**: Atomic semantic version bump, strict validation, GFM HTML description rendering (`bg3 mod render-desc`), and distribution `.pak` packaging.
- **Stage 5 (Post-Release: `/bg3-post-release`)**: Review allowed tags, preview API mutations, and publish metadata to mod.io via REST API (`bg3 modio update-metadata`).

---

## Quickstart

### 1. Prerequisites

- **Python 3.10+** with the **[uv](https://docs.astral.sh/uv/)** workspace package manager (automatically bootstrapped by `./setup.sh`) and `pyyaml>=6.0`.
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
5. Save your settings securely to `$XDG_CONFIG_HOME/bg3/env` (mode 0600).
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
├── packages/                  # Modular Python workspace packages
│   ├── bg3-core/              # Shared core runtime, XDG path resolvers, and mod.io client
│   ├── bg3-theorycraft/       # Theorycrafting, progression, and gear optimization tools
│   └── bg3-authoring/         # Mod scaffolding, packaging, and diagnostic toolchain
├── tests/                     # Automated test suites
├── .gitignore                 # Production-grade gitignore
├── setup.sh                   # Setup wizard launcher
├── CONTRIBUTING.md            # Contribution guidelines
├── CODE_OF_CONDUCT.md         # Contributor Covenant v2.1
├── LICENSE                    # MIT License
└── README.md                  # Project overview
```

> **User Content Studio**: All user-generated content (build guides, subscribed mods, and custom authored mods) is stored externally in `XDG_DOCUMENTS_DIR/BG3_Mod_Studio` (defaults to `~/Documents/BG3_Mod_Studio`), keeping this codebase completely decoupled from user data.

---

## CLI Reference & Tool Hub

Explore, query, and run any of the 59 registered automation tools via the centralized discovery hub:

```bash
# Discover tools by natural language query
bg3 tools search "stat handles"
bg3 tools search "load order"

# Inspect tool flags and schemas
bg3 tools info scaffold stat
bg3 tools info mod pack

# Run query tool directly
bg3 query --slot Weapon --limit 5 --json
```

### 5-Stage Custom Mod Lifecycle

```bash
# Stage 1: Scaffold and author
bg3 mod create "ArcaneProgression" --json

# Stage 2: Pre-flight validation & game sync
bg3 mod validate arcane-progression --json
bg3 mod sync-game --mods arcane-progression --json
bg3 mod diagnose-logs --mod arcane-progression --severity warning --json

# Stage 3: In-game testing & load order
bg3 mod sync-game --clean-mod arcane-progression --json
bg3 mod pack arcane-progression --publish-local --json
bg3 loadorder enable arcane-progression --json
bg3 loadorder validate --json
bg3 save inspect --audit --json
bg3 save clean-missing --dry-run --json

# Stage 4: Version bump & release prep
bg3 mod bump-version arcane-progression --patch --json
bg3 mod render-desc arcane-progression --write --json
bg3 mod pack arcane-progression --out dist/arcane-progression.pak --json

# Stage 5: Post-release metadata & tags
bg3 modio update-metadata --mod arcane-progression --tags Classes Spells --json
```

---

## Documentation

- [Architecture & Technical Design](docs/ARCHITECTURE.md)
- [CLI Design & Stream Discipline](docs/DESIGN.md)
- [Comprehensive Features & Agent Skills Catalog](docs/FEATURES.md)
- [Mod Creation Workflow Guide](docs/MOD_CREATION_WORKFLOW.md)
- [mod.io Integration & Reference Library](docs/MODIO_INTEGRATION.md)

---

## Contributing

Contributions are welcome! Please check our [Contributing Guidelines](CONTRIBUTING.md) and [Code of Conduct](CODE_OF_CONDUCT.md) before opening a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).
Baldur's Gate 3 is a registered trademark of Larian Studios. This toolkit is an unofficial community development project.
