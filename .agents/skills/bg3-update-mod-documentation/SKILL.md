---
name: bg3-update-mod-documentation
description: Orchestrate concurrent subagents to check and update BG3 mod docs from mod.io, refreshing READMEs and catalogs in mods/library.md. Use on /bg3-update-mod-documentation.
---

# BG3 Mod Documentation Update Orchestrator (`bg3-update-mod-documentation`)

Coordinates concurrent worker subagents to check and update *Baldur's Gate 3* mod documentation from `https://mod.io/g/baldursgate3`.

Refer to specifications:
- Subagent Template: [Update Subagent Template](./resources/update_subagent_template.json)
- Sync & Status Reference: [Catalog Sync Flow](./references/catalog_sync_flow.md)

---

> [!TIP]
> Query the studio tool registry with `python3 scripts/bg3.py tools search "<intent>" --json`.

## Workflow

```mermaid
flowchart TD
    Start["User triggers /bg3-update-mod-documentation"] --> Resolve["1. Resolve Batch (or all tracked mods)"]
    Resolve --> Dispatch["2. Launch Concurrent Subagents in Parallel"]
    Dispatch --> Wait["3. Reactive Wait for Notifications"]
    Wait --> Catalog["4. Re-catalog mods/library.md if updated"]
    Catalog --> Present["5. Present Summary Status Table"]
```

### 1. Batch Resolution & Subagent Dispatch
Accept targeted slugs or inspect all tracked mods:
```bash
python3 scripts/bg3.py modio update --list-tracked --json
```
Launch one worker subagent per mod using the schema in [Update Subagent Template](./resources/update_subagent_template.json), following [`bg3-update-single-mod`](../bg3-update-single-mod/SKILL.md).

Stop calling tools and await reactive completion notifications without polling.

### 2. Catalog & Table Compilation
When any mod is updated, refresh the catalog:
```bash
python3 scripts/bg3.py library update-catalog --write
```
Render the consolidated update status table with status indicators (`🟢 Up-to-date`, `🔄 Updated`, `⚠️ Not Tracked`, `❌ Failed`).

---

## Verification Gate

Always verify documentation updates before concluding:
1. Verify `update --list-tracked` or `update-catalog` commands exit with code 0.
2. Confirm all updated mods have valid six-column rows in [`mods/library.md`](../../../mods/library.md).
3. Validate that relative links to `mods/<slug>/README.md` resolve correctly.
