---
name: bg3-release-prep
description: Prepares a Baldur's Gate 3 mod for publication via the official Toolkit, automating atomic version bumping, strict validation, HTML description rendering, game data sync, and packaging (Stage 4 of the mod lifecycle). Triggers on /bg3-release-prep, /release, or when handed off by bg3-test-mod.
---

# BG3 Mod Release Preparation Assistant (Stage 4) (`bg3-release-prep`)

This skill orchestrates the **Stage 4 (Release Preparation)** pipeline for *Baldur's Gate 3* mods. Because mod publication is locked to the official Baldur's Gate 3 Toolkit (`Glasses.exe`) and cannot be executed via the mod.io REST API directly—with `Glasses.exe` mod.io publication consuming loose development files staged in `<Game>/Data/` rather than packed `.pak` archives—this workflow ensures every asset, handle, version tag, and description is 100% publication-ready before handing off to **User-Action Gate 3 (Toolkit Publishing)** and **Stage 5: Post-Release** ([`bg3-post-release`](../bg3-post-release/SKILL.md)).

## Discovery & Tooling

Inspect tool arguments, flags, and schema definitions with:

```bash
python3 scripts/bg3.py tools info bump-version
python3 scripts/bg3.py tools info validate
python3 scripts/bg3.py tools info sync-localization
python3 scripts/bg3.py tools info render-description
python3 scripts/bg3.py tools info sync-data
python3 scripts/bg3.py tools info pack-pak
```

---

## Release Pipeline Architecture

```mermaid
flowchart TD
    Trigger["Trigger: /bg3-release-prep &lt;slug&gt;"] --> Step1["1. Atomic Semantic Version Bump
python3 scripts/bg3.py mod bump-version --mod &lt;slug&gt; --patch --json"]
    Step1 --> Step2["2. Localization Prune & Compile
python3 scripts/bg3.py mod sync-localization --mod &lt;slug&gt; --prune --compile --json"]
    Step2 --> Step3["3. Strict Validation & Conflict Gate
python3 scripts/bg3.py mod validate --mod &lt;slug&gt; --strict --json
python3 scripts/bg3.py mod conflict --candidate &lt;slug&gt; --against-library --json"]
    Step3 -->|Pass| Step4["4. Render mod.io HTML Description
python3 scripts/bg3.py mod render-description --mod &lt;slug&gt; --write --json"]
    Step3 -->|Fail| Halt["Halt: Report Errors & Propose Fixes"]
    Step4 --> Step5["5. Final Game Data Sync & Optional Dist .pak
python3 scripts/bg3.py mod sync-data --mods &lt;slug&gt; --json
python3 scripts/bg3.py mod pack --mod &lt;slug&gt; --out dist/&lt;slug&gt;.pak --json"]
    Step5 --> Step6["6. User-Action Gate 3 (Toolkit Publishing) & Stage 5 Handoff:
ask_question -> /bg3-post-release &lt;slug&gt;"]
```

---

## Step-by-Step Execution

### Step 1: Atomic Semantic Version Bump
Determine the version increment from the user (defaulting to `--patch` unless `--minor` or `--major` is requested):

```bash
python3 scripts/bg3.py mod bump-version --mod <mod-slug> --patch --json
```

This atomically encodes the new Version64 in `Projects/<ModName>_<UUID>/meta.lsx`, `Mods/<ModName>_<UUID>/meta.lsx`, and synchronizes the version string in `my_mods/<mod-slug>/README.md`.

---

### Step 2: Prune & Compile Localization
Ensure no orphaned handles pollute the localization table, and compile the binary `.loca` file:

```bash
python3 scripts/bg3.py mod sync-localization --mod <mod-slug> --prune --compile --json
```

---

### Step 3: Strict Validation & Conflict Gate
Run strict validation to ensure:
- 0 XML/LSX syntax errors.
- 100% of referenced string handles exist in `Localization/English/*.xml`.
- Required 512×512 PNG thumbnails exist in `Projects/` and `Mods/`.
- Spell list references match defined spells.
- No collisions with tracked mods in [`mods/library.md`](../../../mods/library.md).

```bash
python3 scripts/bg3.py mod validate --mod <mod-slug> --strict --json
python3 scripts/bg3.py mod conflict --candidate <mod-slug> --against-library --json
```

> [!WARNING]
> If strict validation fails with errors, stop the release pipeline immediately, report the errors, and offer automated fixes before continuing.

---

### Step 4: Render mod.io HTML Description
Export the mod's complete root README as a GitHub Flavored Markdown / HTML description formatted specifically for mod.io:

```bash
python3 scripts/bg3.py mod render-description --mod <mod-slug> --write --json
```

This writes `my_mods/<mod-slug>/modio_description.html` beside the README, formatting tables, callouts, and lists cleanly for the mod.io web portal.

---

### Step 5: Game Data Synchronization & Optional Distribution Packaging
Deploy the updated mod's loose development files into the game's active `<Game>/Data/` folder so the official Toolkit detects all recent changes and the compiled binary `.loca`:

```bash
python3 scripts/bg3.py mod sync-data --mods <mod-slug> --json
```

> [!IMPORTANT]
> Official mod.io publication in the Baldur's Gate 3 Toolkit (`Glasses.exe`) directly consumes loose development files staged in `<Game>/Data/` (specifically `Data/Editor/Mods/<ModName>/`, `Data/Projects/<ModName>/`, and `Data/Public/<ModName>/`).

Optionally, package a standalone distribution `.pak` for Nexus Mods or manual archive sharing:

```bash
python3 scripts/bg3.py mod pack --mod <mod-slug> --out "dist/<mod-slug>.pak" --json
```

> [!NOTE]
> `python3 scripts/bg3.py mod pack --mod <mod-slug> --out dist/<mod-slug>.pak` produces an optional standalone package strictly for Nexus Mods or manual archive sharing. Official `Glasses.exe` mod.io publishing does **not** require or read the `dist/` archive.

---

### Step 6: Presentation & Progressive Gate Handoff to Stage 5

Present the release summary and guide the user through **User-Action Gate 3 (Toolkit Publishing)**:

```markdown
### 🚀 Mod Release Package Ready: <Mod Name> (v<Version>)

- **Semantic Version**: `<New Version>` (Version64: `<Encoded Int>`)
- **Validation**: [✓] Passed strict structural and handle checks
- **Assets**: [✓] 512×512 thumbnail and publish logo verified
- **Game Data**: [✓] Loose development files synced to BG3 `Data/` directory with compiled binary `.loca`
- **Dist Archive**: [✓] `dist/<mod-slug>.pak` packaged (optional for Nexus Mods or manual archive sharing)

---

#### 🛠️ User-Action Gate 3 (Toolkit Publishing) Steps:
1. Open the **Baldur's Gate 3 Toolkit** (`Glasses.exe`).
2. Open Project **`<Mod Name>`**.
3. Select **File -> Mod Project Manager**.
4. In the Project Settings, copy the contents of `my_mods/<mod-slug>/modio_description.html` into the Description field.
5. Click **Publish Mod** to submit the build to mod.io.
```

> [!IMPORTANT]
> **User-Action Gate 3 (Toolkit Publishing)** is a mandatory manual checkpoint because mod.io binary uploads are strictly restricted to the official Toolkit. Once `Glasses.exe` confirms publication to mod.io, transition to Stage 5 to configure storefront metadata, tags, and perform consumer subscriber cleanup.

Use `ask_question` to transition to **Stage 5: Post-Release** ([`bg3-post-release`](../bg3-post-release/SKILL.md)):
- **Proceed to Stage 5 Post-Release**: Once published in the Toolkit, run `/bg3-post-release <mod-slug>` to inspect allowed tags, review profile settings, publish the verified description and tags via the mod.io REST API, and tear down local development staging.
- **Finish Release Process**: Complete workflow without updating mod.io API metadata.
