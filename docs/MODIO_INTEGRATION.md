# mod.io Integration & Reference Library Guide

This guide covers mod.io API authentication, searching mods, extracting game definitions, and maintaining the mod catalog.

---

## 1. Authentication Setup

mod.io provides a REST API for searching and downloading Baldur's Gate 3 community mods.

1. **Obtain API Key & PAT**:
   - Go to [https://mod.io/me/access](https://mod.io/me/access).
   - Create an **API Key** (used for public search and downloads).
   - Generate a **Personal Access Token (PAT)** with Read/Write access (used for managing your subscribed mods).
2. **Configure Environment**:
   Run the interactive setup launcher:
   ```bash
   ./setup.sh
   ```
   Or set environment variables in `.env`:
   ```bash
   MODIO_API_KEY=your_key_here
   MODIO_PAT=your_pat_here
   ```

---

## 2. Searching Mods

Query the mod.io catalog directly from the CLI:

```bash
# Search for warlock mods
python3 scripts/modio_search.py "warlock"

# Search with console platform filtering (PS5 or Xbox)
python3 scripts/modio_search.py "difficulty" --platform ps5

# Output machine-readable JSON
python3 scripts/modio_search.py "spells" --json
```

---

## 3. Extracting & Documenting Mods

Download and deconstruct community mods into structured markdown specifications:

```bash
# Document a single mod by mod.io ID or slug
python3 scripts/modio_extract.py --mod-id 4166963

# Extract mod and save specification into mods/
python3 scripts/modio_extract.py --mod-id 4166963 --output-dir mods/unlocklevelcurve
```

The extractor:
- Downloads the mod archive from mod.io.
- Inspects PAK files and decompresses Larian TXT and XML data files into `data/`.
- Extracts all spells, passives, statuses, items, and progression curves.
- Emits a comprehensive `README.md` specification.

---

## 4. Subscriptions & Account Sync

Synchronize all mods subscribed on your mod.io profile:

```bash
# List all subscribed mods
python3 scripts/modio_sync.py --list

# Download and update all subscribed mods
python3 scripts/modio_sync.py --download-all
```

---

## 5. Checking Mod Conflicts

When planning a mod load order or evaluating custom mods against community creations:
- Use the autonomous skill `/bg3_check_mod_conflicts` to compare mod definitions.
- The conflict checker verifies:
  1. Overlapping root template or stat overrides.
  2. Missing prerequisite frameworks (`UnlockLevelCurve`, `CompatibilityFramework`, `CommunityLibrary`).
  3. Console platform compatibility (e.g. verifying no external native DLLs or Script Extender requirements).

---

## 6. Updating Profile Metadata & Tags (`/bg3_post_release`)

Update a published mod's mod.io profile metadata and approved tags via the REST API (game ID `6715`):

```bash
# Preview allowed tags and remote settings (no API writes)
python3 scripts/modio_update_metadata.py --mod <mod-slug> --json

# Preview specific tags to add
python3 scripts/modio_update_metadata.py --mod <mod-slug> --tags "Classes,Spells" --json

# Apply approved updates (writes require explicit --confirm)
python3 scripts/modio_update_metadata.py --mod <mod-slug> --tags "Classes,Spells" --confirm --json
```

---

## 7. Curating mod.io Collections (`/bg3_create_modio_collection`)

Create or update public collections on mod.io using the cataloged entries in `mods/library.md`:

```bash
# Dry run: preview mod selection and additions without API writes
python3 scripts/modio_create_collection.py --dry-run

# Run collection sync
python3 scripts/modio_create_collection.py
```
