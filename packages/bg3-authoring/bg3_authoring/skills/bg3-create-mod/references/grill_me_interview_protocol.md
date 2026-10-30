# Mod Design Interview Protocol (`grill-me`)

Before authoring, walk down each branch of the mod design tree one question at a time:

### Design Tree Branches
1. **Branch A (Mod Identity & Theme)**: Name (PascalCase, e.g. `ArcaneProgression`), summary, and character fantasy.
2. **Branch B (Classes & Progression)**: Target classes/subclasses, level bounds (1-12 vanilla vs. 13-20 `UnlockLevelCurve`), progression unlock levels.
3. **Branch C (Spells, Passives & Abilities)**: Action economy (Action, Bonus Action, Reaction), resource costs (Spell slots, Ki, Charges), damage/status effects.
4. **Branch D (Parent Dependencies)**: Base game only (`GustavDev`), `UnlockLevelCurve` (`a2ffd0e4-c407-8642-2611-c934ea0b0a77`), or cataloged community mods in `mods/library.md`.
5. **Branch E (In-Game Acquisition & Item Drops)**: Container drop locations (Tutorial Chest, Camp Chest, vendors like Arron or Dammon) for `scripts/authoring/inject_treasure_table.py`.

### Interview Formatting
- List recommended option first with `(Recommended)`.
- Format all options as direct user responses.
- Synthesize responses into a structured implementation plan and obtain explicit user approval before authoring.
