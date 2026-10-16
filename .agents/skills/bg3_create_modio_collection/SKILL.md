---
name: bg3_create_modio_collection
description: Creates or updates a public Baldur's Gate 3 mod.io collection from mods documented in mods/library.md. Triggers on /bg3_create_modio_collection or requests to create a BG3 mod.io collection.
---

# Create a BG3 mod.io Collection

Use `scripts/modio_create_collection.py` to create a public BG3 collection or update one of the authenticated user's collections using numeric Mod Id values in the six-column categorized rows of `mods/library.md`.

## Discovery & Tooling

Inspect tool arguments and schema details with:

```bash
python3 scripts/tools.py --info modio-collection
```

## Safety and credentials

- Require `MODIO_PAT` in the process environment. Never ask the user to paste it, pass it as a CLI argument, print it, or put it in logs.
- The script checks that selected mod profiles and collections belong to Baldur's Gate 3 (game ID `6715`) before writing.
- Never write to mod.io without first showing the complete change preview and receiving the user's explicit approval in chat. A slash-command invocation alone is not approval.
- A dry run sends only read requests. The script also requests a final `yes` confirmation before any write.
- If the user approves a dry-run preview, rerun without `--dry-run`, inspect the newly generated preview, and continue only if it matches the approved changes. If it differs, stop and show the new preview.
- The collection is public. For an existing collection, the user chooses either add-only or replace; replace removes mods not in the selected library set.
- Report API errors and partial outcomes precisely. Never report a failed or partial operation as fully successful.

## Workflow

1. Verify that `MODIO_PAT` is already configured in the environment. Do not inspect or disclose its value.
2. Run a dry-run and let the user choose documented mods with valid numeric Mod Id values, then create a new collection or select one of their existing BG3 collections:

   ```bash
   python3 scripts/modio_create_collection.py --dry-run
   ```

   For a new collection, the script asks for its name and description. For an existing collection, it asks whether to add missing selected mods only or replace its contents with the selected set. Library entries without valid numeric IDs are warned about and excluded.
3. Show the script's entire change preview, including selected mods and additions/removals. Ask the user to approve or decline in chat. Do not treat the CLI confirmation prompt as a substitute for this approval.
4. After approval, rerun the script without `--dry-run`. Compare the fresh preview with the approved preview. At the final CLI prompt, enter `yes` only when they match; otherwise decline and report the difference.
5. Report the collection name and ID, each operation's result, and any API errors or partial failures. State if the user declined or ran a dry run.

## Troubleshooting

- If the script reports missing IDs, update the `Mod Id` field in the corresponding category row only after verifying the ID from trusted mod documentation.
- If the token is missing or an API request fails, report the error without requesting or exposing the token. Do not retry a write automatically.
- For command options:

  ```bash
  python3 scripts/modio_create_collection.py --help
  ```
