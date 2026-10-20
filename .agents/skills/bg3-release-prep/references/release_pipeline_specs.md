# Release Pipeline Specifications & Toolkit Publishing

## 1. Release Architecture & Versioning
- **Version64 Encoding**: Encodes `major.minor.patch.build` into a 64-bit integer synchronized across `Projects/<ModName>_<UUID>/meta.lsx` and `Mods/<ModName>_<UUID>/meta.lsx`.
- **Localization Compilation**: Compiles `Localization/English/*.xml` into binary `.loca` and stages in `<Game>/Data/`.
- **HTML Description**: `scripts/bg3.py mod render-description` translates GitHub Flavored Markdown to clean HTML suitable for mod.io.

---

## 2. User-Action Gate 3 (Toolkit Publishing)
Because binary mod publishing is restricted to the official Baldur's Gate 3 Toolkit (`Glasses.exe`):
1. Launch **Baldur's Gate 3 Toolkit** (`Glasses.exe`).
2. Open Project `<ModName>`.
3. Open **File -> Mod Project Manager**.
4. Paste the rendered HTML from `my_mods/<slug>/modio_description.html` into the Description box.
5. Click **Publish Mod** to submit the build to mod.io.
6. Once published, transition to **Stage 5 Post-Release** ([`bg3-post-release`](../../bg3-post-release/SKILL.md)).
