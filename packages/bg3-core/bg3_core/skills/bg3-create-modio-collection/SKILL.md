---
name: bg3-create-modio-collection
description: Create or update a public Baldur's Gate 3 mod.io collection from mods documented in library.md. Use on /bg3-create-modio-collection or when creating a mod.io collection.
---

# Create a BG3 mod.io Collection (`bg3-create-modio-collection`)

Creates a public BG3 collection or updates one of the authenticated user's collections using numeric Mod ID values from `Mods/subscribed/library.md`.

---

## Safety and Credentials Invariants

1. **Environment Authentication**: Require `MODIO_PAT` in the process environment. Keep token values masked in all logs and outputs.
2. **Game Guard**: Ensure selected mod profiles and collections belong strictly to Baldur's Gate 3 (Game ID `6715`).
3. **Explicit Approval Gate**: Present the complete change preview to the user. Await affirmative confirmation in chat before executing live API writes.
4. **Dry-Run Parity**: Execute `--dry-run` first to preview additions and removals. Continue live execution only when live preview matches the approved dry-run.

---

> [!TIP]
> Query the studio tool registry with `bg3 tools search "<intent>" --json`.

## Workflow

### 1. Verification & Dry Run Preview
Confirm `MODIO_PAT` is present, then execute dry run:
- Run dry-run collection assembly: `bg3 modio create-collection --dry-run`
- The script confirms BG3 collection membership and checks numeric Mod IDs from `Mods/subscribed/library.md`.

### 2. User Approval & Live Execution
1. Present the complete preview (selected mods, additions, removals) to the user.
2. Upon user approval, rerun without `--dry-run`:
   - Run live collection creation: `bg3 modio create-collection`
3. Confirm that the live preview matches the approved dry-run preview.

---

## Verification Gate

Always verify collection state and API responses:
1. Verify `create-collection` exits with code 0.
2. Confirm the collection URL and ID are displayed and operational.
3. Verify all selected mods were added to the target collection.
4. If missing numeric IDs were reported, verify IDs against trusted mod documentation before updating `Mods/subscribed/library.md`.
