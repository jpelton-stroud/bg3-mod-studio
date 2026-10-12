# Contributing to Baldur's Gate 3 Mod Studio & Mod.io Toolkit

Thank you for your interest in contributing to the **Baldur's Gate 3 Mod Studio & Mod.io Toolkit**! This project provides tools, scripts, and autonomous agent workflows to author, document, sync, and validate mods for Baldur's Gate 3.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Repository Architecture](#repository-architecture)
- [Mod Authoring Standards](#mod-authoring-standards)
- [Mod Documentation & mod.io Standards](#mod-documentation--modio-standards)
- [Commit & Pull Request Conventions](#commit--pull-request-conventions)

---

## Code of Conduct

All contributors are expected to uphold our [Code of Conduct](CODE_OF_CONDUCT.md). Please report unacceptable behavior to project maintainers.

---

## Getting Started

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/<your-account>/BaldursGate3.git
   cd BaldursGate3
   ```
2. **Run the Setup Wizard**:
   ```bash
   ./setup.sh
   ```
   This will prompt you for your `MODIO_API_KEY`, optional `MODIO_PAT`, the path to your BG3 `Data` folder (`BG3_DATA_DIR`), and your default author handle (`BG3_MOD_AUTHOR`).
3. **Verify Python Environment**:
   This project uses Python 3.10+ standard library. No external pip dependencies are required.
   ```bash
   python3 -m py_compile scripts/*.py
   ```

---

## Repository Architecture

- `scripts/`: Pure Python automation tools for scaffolding, syncing, searching, and extracting mods.
- `my_mods/`: Source directory for custom authored mods (contains `Projects/`, `Mods/<UUID>/`, `Public/`, and `Localization/`).
- `mods/`: Curated reference mod documentation specifications extracted from mod.io. Tracked mods are listed in `mods/library.md`.
- `build_guides/`: Local sandbox for theorycrafting level 20 builds (contents ignored in Git by default).
- `.agents/skills/`: Agent skill instructions for autonomous workflows.

---

## Mod Authoring Standards

When submitting or creating custom mods in `my_mods/`:
- **Naming Conventions**: Use PascalCase or CamelCase for mod directory names and metadata (e.g., `ArcaneProgression`).
- **Scaffolding Tool**: Always generate mod structure using `scripts/create_mod_scaffold.py`:
  ```bash
  python3 scripts/create_mod_scaffold.py --name "MyMod" --description "Summary of mod"
  ```
- **Metadata**: Ensure valid Larian Version64 integers and standard UUIDv4 identifiers in `meta.lsx`.
- **Localization**: Never hardcode user-facing strings into stats or progression entries. Use generated handles linked to `Localization/English/<mod_name>.xml`.
- **Asset Dimensions**: Placeholders and custom logos should adhere to standard sizes (512x512 PNG for project thumbnails).

---

## Mod Documentation & mod.io Standards

When adding or updating reference mod specifications in `mods/`:
- Each mod documentation directory must include a `README.md` containing:
  - Mod Overview & Mod.io Metadata
  - System Architecture & Prerequisites
  - In-Game Items & Stat Definitions
  - Spells, Passives & Status Effects
  - Progression Trees & Unlocks
- Update `mods/library.md` to register newly documented mods under the relevant category (Gear, Spells, Classes, Progression, Utilities).

---

## Commit & Pull Request Conventions

We adhere to the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat:` A new script, tool, mod scaffold, or documentation feature.
- `fix:` A bug fix in existing scripts or mod definitions.
- `docs:` Documentation changes only.
- `refactor:` Code changes that neither fix a bug nor add a feature.
- `test:` Adding or updating verification tests.
- `chore:` Maintenance tasks, gitignore updates, or project configs.

### Submitting a Pull Request
1. Fork the repo and create a feature branch (`git checkout -b feat/my-new-feature`).
2. Verify all python scripts compile cleanly (`python3 -m py_compile scripts/*.py`).
3. Fill out the pull request template completely.
4. Ensure your PR description links any relevant issues.
