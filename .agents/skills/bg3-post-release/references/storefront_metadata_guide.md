# Storefront Metadata & Teardown Guide

## 1. Storefront Settings Reference

When executing `--confirm`, the API updates:
- **Tags**: Adds approved game tags while preserving all existing tags.
- **Community Options**: Enables Allow comments, Allow dependants, and Allow to be added to collections.
- **Credit Options**: Enables all non-commercial reuse and credit variants.
- **Visibility**: Sets to `1` (Public).
- **Description**: Uploaded from `my_mods/<slug>/modio_description.html`.

---

## 2. Environment Teardown Invariants

Before launching the game as a consumer subscriber, local development assets must be cleared to prevent Patch 7 UUID conflicts and third-party warnings:

```bash
# 1. Purge loose files synced to <Game>/Data/
python3 scripts/bg3.py mod sync-data --clean-mod <mod-slug> --json

# 2. Delete local test .pak from AppData/Mods/
python3 scripts/bg3.py mod pack --mod <mod-slug> --clean-local --json

# 3. Disable local test entry in modsettings.lsx
python3 scripts/bg3.py loadorder --disable <mod-slug> --json
```

---

## 3. Storefront Safety Rules (Affirmative)

- Send write requests only after explicit user confirmation of the preview.
- Confine mutations strictly to the uniquely resolved remote profile matching the local mod.
- Preserve all previously assigned tags.
- Maintain non-commercial terms on all publications.
- Upload binary pak files strictly through the official Baldur's Gate 3 Toolkit (`Glasses.exe`).
