# Baldur's Gate 3 Mod Studio (`bg3-mod-studio`)

Metapackage that installs the complete Baldur's Gate 3 Mod Studio tooling suite:
- `bg3-core`: Canonical `bg3` CLI entrypoint, shared runtime, LSF/LSPK parsers, mod.io client, load order manager, and save inspector.
- `bg3-authoring`: Custom mod authoring, unified asset scaffolding, diagnostics, and packaging toolkit.
- `bg3-theorycraft`: Modded character build crafting and DPR sequence simulation engine.

## Installation

```bash
pip install bg3-mod-studio
# or
uv tool install bg3-mod-studio
```

## Usage

The canonical unified `bg3` CLI is provided by `bg3-core` and automatically available once `bg3-mod-studio` is installed:

```bash
bg3 --help
```
