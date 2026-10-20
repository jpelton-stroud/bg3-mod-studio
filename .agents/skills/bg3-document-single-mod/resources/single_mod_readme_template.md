# Rich Features Specification Template (`README.md`)

```markdown
# Mod Specification: [Mod Name]
**Category**: [Gear | Spells | Classes & Subclasses | Progression & Rules | Utilities & Cheats]
**Author**: [Author] | **Version**: [Version] | **mod.io ID**: `[ID]`
**Mod Slug**: `[slug]` | **Features Documented**: `[count] implemented`
**URL**: `https://mod.io/g/baldursgate3/m/[slug]`

---

## Overview
[1-2 paragraph description of the mod, its purpose, and synergies]

---

## Implemented In-Game Features

| Feature Name & Type | In-Game Identifier | Base Stats & Modifiers | Granted Abilities, Spells & Passives (Full Mechanics) | Acquisition & Usage |
| :--- | :--- | :--- | :--- | :--- |
| **[Item / Spell Name]**<br>*[Weapon / Armor / Cantrip / Passive]* | `[Technical_ID]` | Base weapon damage, AC, crit range, or stat boosts | Detailed explanation of what the granted passives/spells actually do (damage roll, save DC, effect formula, cooldown) | Camp chest, merchant, or class progression unlock |
```

### Static Implementation Rules
- **Include**: Valid entries in `Stats/Generated/Data/*.txt` with resolved English handles.
- **Exclude**: Entries with `IsDummy "1"`, WIP placeholders, and abstract base templates (`_Base_Weapon`).
- **Mechanics Requirement**: Granted passives must explain what the ability does in numbers and effects, not just list names.
