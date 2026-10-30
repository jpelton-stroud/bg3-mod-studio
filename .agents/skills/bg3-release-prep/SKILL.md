---
name: bg3-release-prep
description: Prepare BG3 mods for official Toolkit publication with version bumping, HTML rendering, validation, and packaging (Stage 4). Use on /bg3-release-prep or before release.
---

# BG3 Mod Release Preparation Assistant (Stage 4) (`bg3-release-prep`)

Stage 4 pipeline for *Baldur's Gate 3* mods, preparing loose development files and HTML descriptions for User-Action Gate 3 (`Glasses.exe` publishing).

Refer to specifications:
- Publishing & Versioning: [Release Pipeline Specs](./references/release_pipeline_specs.md)

---

> [!TIP]
> Query the studio tool registry with `uv run bg3 tools search "<intent>" --json`.

## Workflow

```mermaid
flowchart TD
    Start["/bg3-release-prep <slug>"] --> Bump["1. Atomic Semantic Version Bump"]
    Bump --> Loca["2. Prune & Compile Binary .loca"]
    Loca --> Strict["3. Strict Validation & Conflict Gate"]
    Strict --> Render["4. Render mod.io HTML Description"]
    Render --> Sync["5. Stage Loose Files to <Game>/Data/"]
    Sync --> Publish["6. User-Action Gate 3: Toolkit Publishing"]
    Publish --> Handoff["7. Transition to Stage 5: Post-Release"]
```

### 1. Semantic Bump & Localization Compilation
```bash
uv run bg3 mod bump-version --mod <mod-slug> --patch --json
uv run bg3 mod sync-localization --mod <mod-slug> --prune --compile --json
```

### 2. Strict Validation & Description Rendering
```bash
uv run bg3 mod validate --mod <mod-slug> --strict --json
uv run bg3 mod conflict --candidate <mod-slug> --against-library --json
uv run bg3 mod render-description --mod <mod-slug> --write --json
```

### 3. Game Data Staging & Packaging
Sync loose development files and `.loca` to `<Game>/Data/`:
```bash
uv run bg3 mod sync-data --mods <mod-slug> --json

# Optional package for Nexus Mods
uv run bg3 mod pack --mod <mod-slug> --out "dist/<mod-slug>.pak" --json
```

---

## Verification Gate

Verify release preparation before Toolkit publishing:
1. Confirm validation and conflict commands exit with code 0.
2. Confirm `my_mods/<mod-slug>/modio_description.html` exists and is non-empty.
3. Confirm 512×512 PNG icons exist and binary `.loca` is compiled.
4. Guide user through [Release Pipeline Specs](./references/release_pipeline_specs.md) and transition to [`bg3-post-release`](../bg3-post-release/SKILL.md).
