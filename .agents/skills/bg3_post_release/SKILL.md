---
name: bg3_post_release
description: Applies approved metadata, profile tags, and description updates for a local Baldur's Gate 3 mod already published on mod.io (Stage 5 of the mod lifecycle). Triggers on /bg3_post_release, /bg3_update_modio_metadata, or when handed off by bg3_release_prep.
---

# Post-Release Publishing & Profile Metadata (Stage 5)

Use this skill as **Stage 5** of the custom mod lifecycle to update a published mod profile through the mod.io REST API. This does not upload a `.pak` file; binary publishing is performed via the official Baldur's Gate 3 Toolkit (`Glasses.exe`).

## Discovery & Tooling

Inspect tool arguments, flags, and schema definitions with:

```bash
python3 scripts/tools.py --info post-release
python3 scripts/tools.py --info sync-game
python3 scripts/tools.py --info pack-pak
python3 scripts/tools.py --info load-order
python3 scripts/tools.py --info render-description
```

## Required Interaction

Never write to mod.io until both the proposed tag list and the complete set of profile changes have been shown to the user and explicitly approved. A slash-command invocation alone is not approval for the API writes.

## Workflow

### 1. Resolve the local mod

Accept a mod name or slug that identifies exactly one folder under `my_mods/`, for example:

```text
/bg3_post_release paladins-call
```

Use the local folder name as the CLI `--mod` argument. If there is no exact normalized local folder match, or more than one match, stop and report the issue. Do not guess or use a path outside `my_mods/`.

Read only that mod's `README.md` when evaluating its content and implemented features. Do not inspect game files or other documentation to infer tags.

### 2. Get allowed tags and inspect the target

Require `MODIO_PAT` in the environment. Never ask the user to paste it, pass it as a CLI argument, display it, or include it in logs.

Run an initial no-write preview to fetch the game-approved tags, resolve the matching mod.io profile, and ensure the publishing description exists:

```bash
python3 scripts/modio_update_metadata.py --mod "<local-folder>" --json
```

If `modio_description.html` is missing, the CLI generates it from the local README using `scripts/render_modio_description.py`. If the README, generated description, token, API lookup, or preflight is invalid, report the error and stop without API writes.

Use the preview's `allowed_tags` and the README's content to prepare concise, relevant tag suggestions. Suggest only names present in `allowed_tags`. Present the suggestions and let the user add, remove, or edit individual choices; validate the final choices against `allowed_tags`. If the remote profile does not resolve uniquely to the local mod, stop without writes.

### 3. Show the full change preview

After the user approves the tag list, run a second no-write preview with only those approved tags:

```bash
python3 scripts/modio_update_metadata.py --mod "<local-folder>" --tags "<approved-tag-1>,<approved-tag-2>" --json
```

Show the resolved mod name, profile URL, description file, tags to add, and settings to be sent. State explicitly:

- The API will add the approved tags and preserve all existing tags.
- `community_options` will enable only Allow comments, Allow dependants, and Allow to be added to collections. Other community flags remain unchanged.
- `credit_options` will enable every non-commercial reuse option exposed by the API, including the non-commercial credit/permission variants. The commercial-use/re-sale option will remain disabled.
- `visible` will be set to `1` (Public). The separate mod `status` will not be changed.
- Description will be uploaded from `my_mods/<local-folder>/modio_description.html`.

Ask for a separate explicit confirmation to perform these API writes. If the user declines or does not confirm, stop with no write requests.

### 4. Apply after confirmation

Only after the final confirmation, run the same CLI call with `--confirm`:

```bash
python3 scripts/modio_update_metadata.py --mod "<local-folder>" --tags "<approved-tag-1>,<approved-tag-2>" --confirm --json
```

The CLI re-runs preflight before writing. It makes one Edit Mod request for the description, community and credit flags, and public visibility, and a separate Add Mod Tags request for approved tags not already present. It attempts both independent write operations and returns per-operation outcomes; do not describe the result as all-or-nothing.

### 5. Report results

Report whether each operation succeeded, failed, or was skipped. For partial failures, state which changes have already succeeded and quote the API error without exposing credentials. Do not claim a failed operation succeeded.

Provide the resolved profile's manual confirmation link:

```text
https://mod.io/g/baldursgate3/m/<resolved-mod-slug>/admin/settings
```

### 6. Post-Release Environment Teardown & Live Subscription Verification

Once the mod is confirmed published and live on mod.io, switch from developer authoring mode to consumer subscriber mode. Deleting local test artifacts prevents Patch 7 UUID collisions, "third-party mod" warnings, and multiplayer checksum mismatches:

```bash
# 1. Purge loose files synced to <Game>/Data/ for Toolkit publishing
python3 scripts/sync_game_data.py --clean-mod <mod-slug> --json

# 2. Delete local test .pak from AppData/Mods/
python3 scripts/pack_mod_pak.py --mod <mod-slug> --clean-local --json

# 3. Remove local test entry from modsettings.lsx
python3 scripts/manage_load_order.py --disable <mod-slug> --json
```

Instruct the user:
1. Launch **Baldur's Gate 3**.
2. Open the in-game **Mod Manager**.
3. Locate the newly published mod in the browser, subscribe, and enable it.
4. Verify clean download, activation, and game launch as an official mod.io subscriber.

## Safety Rules

- Never issue a write request during either preview.
- Never write if the user has not separately approved the final change preview.
- Never mutate any mod other than the uniquely resolved local mod's remote profile.
- Never remove existing tags.
- Never enable commercial use/resale or change mod status.
- Never publish or upload mod files through this workflow.

## Optional Next Steps

Once profile metadata and tags are confirmed live, you can optionally include the mod in a public or curated collection:
- Run `/bg3_create_modio_collection` to update or create a public mod.io collection including this mod.
