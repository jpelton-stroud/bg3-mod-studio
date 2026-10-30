# Build Guide Conventions & Mechanics

## 1. Feat Strategy & Stat Conventions

### Ability Scores
- **Primary Setup**: Assumes `Choose Your Stats` mod sets primary stat to 20, freeing all Feat slots from ASIs for high-impact combat/mobility passives.
- **Fallback Setup**: Always provide a standard 27 Point Buy allocation for unmodded play.

### Feat Priorities
- **High-Impact Passives**: Alert (+5 initiative), War Caster (advantage on concentration), Spell Sniper (crit threshold reduction), Savage Attacker (reroll melee damage), Sentinel (reaction lockdown), Dual Wielder, Resilient (Wisdom).
- **Progression Intervals**: Standard levels 4, 8, 12, 16, 19 (plus Fighter 6 & 14, Rogue 10).

---

## 2. Progression Table Schema

### Caster & Hybrid Builds (5 Columns)
```markdown
| Total Level | Class & Level | Cantrips Gained | Vanilla Spells Learned / Prepared | Feats & Key Features |
| :---: | :--- | :--- | :--- | :--- |
| **1** | **Fighter 1** | — | — | **Fighting Style**: Defense (+1 AC); Second Wind; **CON Save** |
```

### Pure Melee Builds (4 Columns)
Omit cantrips and spell columns entirely:
```markdown
| Total Level | Class & Level | Class Features & Maneuvers | Feats & Key Features |
| :---: | :--- | :--- | :--- |
| **1** | **Fighter 1** | Fighting Style: Great Weapon Fighting; Second Wind | **STR & CON Save**; All Armor & Weapons |
```

---

## 3. Level 13–20 Mechanics (`UnlockLevelCurve`)

- Full casters unlock 7th and 8th level spell slots for upcasting or modded spells.
- Cantrips scale to 4 dice/beams at Character Level 17.
- Incorporate extended subclass capstones where appropriate.
