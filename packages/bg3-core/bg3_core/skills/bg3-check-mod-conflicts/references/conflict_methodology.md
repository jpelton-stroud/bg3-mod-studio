# BG3 Mod Conflict Detection Methodology

## 1. Conflict Vectors

Common BG3 conflict sources include:
- **Direct Stated Incompatibility**: Author explicitly lists incompatibilities in mod descriptions.
- **Missing Prerequisites**: Missing frameworks (*Community Library*, *Compatibility Framework*, *5e Spells*, *BG3 Script Extender*).
- **Progression Table Clashes**: Both mods edit the same class/subclass node in `Progressions.lsx` without Compatibility Framework.
- **Vanilla Asset Overwrites**: Both mods overwrite identical spell, status, or item root templates.

---

## 2. Mode 1: Candidate vs. Existing Library

1. **Library Verification**: Check categorized rows in `Mods/subscribed/library.md`. Inspect specs in `Mods/subscribed/`.
2. **Metadata Inspection**:
   ```bash
   bg3 modio search --query "<MOD_SLUG>" --platform "<PLATFORM>" --json
   ```
3. **Subsystem Audit**:
   - **Progressions & Rules**: Level curves, spell slots, feat intervals.
   - **Classes & Subclasses**: Class overrides and spell lists.
   - **Spells & Gear**: Overlapping spell entries or treasure tables.
4. **Console Platform Rules**:
   - **No Manual Load Order**: Console players cannot reorder mods; priority conflicts cannot be resolved manually. Tag with `[Console Load Order]`.
   - **No Script Extender (BG3SE)**: Native PC DLL dependencies fail on console.

---

## 3. Mode 2: Cross-Candidate Batch Conflicts

1. **Pairwise Analysis**: Compare pairs across candidate sets for shared class, cantrip, or subsystem replacements.
2. **Order Constraints**: Identify inter-dependencies requiring strict load ordering. On console, flag any priority constraint with `[Console Load Order]`.
