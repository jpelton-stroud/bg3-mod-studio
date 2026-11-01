---
name: bg3-sync-single-mod
description: Fetch, unpack, validate, document, or update a single BG3 mod from mod.io into mods/<name>/README.md with rich feature schemas. Use on /bg3-sync-single-mod or via orchestrator.
---

# Single BG3 Mod Documentation & Update Specialist (`bg3-sync-single-mod`)

Downloads, unpacks, analyzes, documents, or updates an individual Baldur's Gate 3 community mod from [mod.io](https://mod.io/g/baldursgate3). Emits structured documentation into `$XDG_DOCUMENTS_DIR/BG3_Mod_Studio/Mods/subscribed/<slug>/README.md`.

Refer to companion resources:
- Specification Format: [README Template](./resources/single_mod_readme_template.md)
- Return Formats: [Status Message Schemas](./resources/sync_status_messages.md)

---

> [!TIP]
> Query the studio tool registry with `bg3 tools search "<intent>" --json`.

## Workflow

```mermaid
flowchart TD
    Start["Mod Query / Slug"] --> Check{"Tracked in library.md?"}
    Check -->|"Yes"| Update["1. Run bg3 modio update"]
    Check -->|"No"| Extract["1. Run bg3 modio extract"]
    Update --> Hash{"Release Hash Matches?"}
    Hash -->|"Yes"| UpToDate["Return Up-to-Date"]
    Hash -->|"No"| Refresh["Download, Unpack, & Refresh README"]
    Extract --> Decompress["Decompress LSPK Assets"]
    Decompress --> Filter["Filter In-Game Features"]
    Filter --> Generate["Generate README.md & Add to library.md"]
    Refresh --> Status["Emit Standardized Return Message"]
    Generate --> Status
    UpToDate --> Status
```

### 1. Ingestion / Update Pipeline
Verify `MODIO_API_KEY` is configured in `~/.config/bg3/env`. Determine action:
- **Tracked Mod**: Execute `bg3 modio update "<MOD_QUERY>" --json`. This compares release hashes, updates local `.pak` files if modified, refreshes `README.md`, and updates `Mods/subscribed/library.md`.
- **New Mod**: Execute `bg3 modio extract --query "<MOD_QUERY>" --write-spec --json`. This downloads the package, uncompresses LSPK assets, and generates initial documentation.

### 2. Feature Filtering & Schema Verification
Cross-check extracted features against the criteria in [README Template](./resources/single_mod_readme_template.md). Exclude dummy templates or WIP stubs (`IsDummy "1"`). Confirm that all granted abilities and passives detail full mechanical formulas and effects.

### 3. Return Status
Emit standardized status according to [Status Message Schemas](./resources/sync_status_messages.md).

---

## Verification Gate

Always verify document generation before concluding:
1. Verify `bg3 modio extract` or `bg3 modio update` exits with code 0 and valid JSON.
2. Confirm `Mods/subscribed/<slug>/README.md` exists and contains the complete Rich Features table.
3. Confirm dummy entries (`IsDummy "1"`) are excluded from documented features.
