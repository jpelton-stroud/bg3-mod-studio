---
name: bg3-manage-load-order
description: Inspect, activate, disable, and reorder mods in the game's active profile modsettings.lsx. Use on /bg3-manage-load-order or when managing active Baldur's Gate 3 mods.
---

# BG3 Load Order Management Skill (`bg3-manage-load-order`)

Inspects and manages the active *Baldur's Gate 3* load order directly through natural language or slash command, modifying `modsettings.lsx`.

---

> [!TIP]
> Query the studio tool registry with `bg3 tools search "<intent>" --json`.

## Workflow

```mermaid
flowchart TD
    Trigger["User Request"] --> Parse["Determine Action (View, Clean, Auto-Sort, Enable, Disable)"]
    Parse --> ResolveMod["Resolve UUID & Version from meta.lsx"]
    ResolveMod --> Execute["Execute loadorder CLI with automatic backup"]
    Execute --> Verify["Run Validation Gate"]
    Verify --> Format["Format Response as Markdown Table"]
```

### 1. View & Clean Load Order
- List current profile load order: `bg3 loadorder list --json`
- Clean missing or removed mods from active profile: `bg3 loadorder clean --json`
- Topologically auto-sort active mods based on dependencies: `bg3 loadorder auto-sort --json`

### 2. Mod Activation & Deactivation
- Enable at end of load order with dependencies: `bg3 loadorder enable "<mod_slug_or_UUID>" --with-deps --json`
- Disable a mod safely: `bg3 loadorder disable "<mod_slug_or_UUID>" --json`

### 3. Output Presentation
Present active mods as a structured table with index, mod name, folder, and UUID.

---

## Verification Gate

Always verify load order integrity before concluding:
1. Validate profile rules: `bg3 loadorder validate --json`
2. Confirm command exits with code 0 and valid JSON.
3. Confirm `GustavDev` (or Patch 8 core system modules) reside in canonical positions.
4. Verify automatic backup was created at `modsettings.lsx.<timestamp>.bak`.
