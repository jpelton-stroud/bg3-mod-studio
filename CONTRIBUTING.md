# Contributing to Baldur's Gate 3 Mod Studio & Mod.io Toolkit

Thank you for your interest in contributing to the **Baldur's Gate 3 Mod Studio & Mod.io Toolkit**! This project provides CLI tools, modular packages, and autonomous agent workflows to author, document, sync, and validate mods for Baldur's Gate 3.

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
   git clone https://github.com/jpelton-stroud/bg3-mod-studio.git
   cd bg3-mod-studio
   ```
2. **Synchronize Workspace Dependencies & Install Tools**:
   This project is organized as a modular `uv` workspace with zero heavy external runtime dependencies.
   ```bash
   uv sync
   ./setup.sh
   ```
   This will prompt you for your `MODIO_API_KEY`, optional `MODIO_PAT`, your BG3 `Data` directory, default author handle, and your Studio Document workspace directory.
3. **Run Automated Test Suite & Verification**:
   ```bash
   uv run python -m unittest discover tests
   uv run bg3 tools verify --audit-skills
   ```

---

## Repository Architecture

- `packages/bg3-core/`: Core runtime, unified CLI router, pure Python LSPK packager, mod.io REST client, and XDG environment resolution.
- `packages/bg3-authoring/`: Mod scaffolding, XML/LSX AST parsers, binary localization compilers, conflict analysis, and diagnostics.
- `packages/bg3-theorycraft/`: Level 1–20 multiclass simulation, spell slot calculations, and combat DPR sequence theorycrafting.
- `.agents/skills/`: 15 Antigravity agent skills symlinked from package resources for autonomous workflows.
- `tests/`: Comprehensive integration and unit test suite across all workspace packages.

User-authored mods, subscribed mod archives, and build guides reside in your externalized Studio directory (`$XDG_DOCUMENTS_DIR/BG3_Mod_Studio`), keeping git history clean.

---

## Mod Authoring Standards

When authoring custom mods:
- **Naming Conventions**: Use PascalCase or CamelCase for mod directory names and metadata (e.g., `ArcaneProgression`).
- **Scaffolding Tool**: Always generate mod structures using `bg3 mod create`:
  ```bash
  bg3 mod create "MyMod" --description "Summary of mod"
  ```
- **Metadata**: Ensure valid Larian Version64 integers and standard UUIDv4 identifiers in `meta.lsx`.
- **Localization**: Never hardcode user-facing strings into stats or progression entries. Use generated handles linked to `Localization/English/<mod_name>.xml`.
- **Validation**: Validate mod schemas before testing or packaging:
  ```bash
  bg3 mod validate --mod my-mod
  ```

---

## Mod Documentation & mod.io Standards

When adding or updating reference mod specifications in your subscribed mod library:
- Each mod documentation directory must include a `README.md` containing:
  - Mod Overview & Mod.io Metadata
  - System Architecture & Prerequisites
  - In-Game Items & Stat Definitions
  - Spells, Passives & Status Effects
  - Progression Trees & Unlocks
- Run `bg3 modio update-catalog --write` to register or refresh the mod under the relevant category in `mods/library.md`. Each row uses Mod Id, Mod Name, Mod Slug, Description, Features Documented, and Spec Link; unknown IDs stay blank until verified.

---

## Commit & Pull Request Conventions

We adhere to the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat:` A new tool, mod scaffold, or workspace feature.
- `fix:` A bug fix in existing packages or schema definitions.
- `docs:` Documentation changes only.
- `refactor:` Code changes that neither fix a bug nor add a feature.
- `test:` Adding or updating verification tests.
- `chore:` Maintenance tasks, gitignore updates, or project configs.

### Submitting a Pull Request
1. Fork the repo and create a feature branch (`git checkout -b feat/my-new-feature`).
2. Run the test suite: `uv run python -m unittest discover tests`.
3. Verify tool registry integrity: `uv run bg3 tools verify --audit-skills`.
4. Fill out the pull request template completely.
5. Ensure your PR description links any relevant issues.
