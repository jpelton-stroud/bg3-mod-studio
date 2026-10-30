---
name: bg3-query-gear
description: Recommend BiS equipment, stat boosts, spells, and passives from cataloged BG3 community mods in mods/library.md. Use on /bg3-query-gear or when requesting gear advice.
---

# BG3 Mod Equipment & Mechanics Advisor (`bg3-query-gear`)

Intelligent gear and build advisor, translating natural language requests into high-speed queries against the cataloged community mod database ([`mods/`](../../../mods)).

---

> [!TIP]
> Query the studio tool registry with `uv run bg3 tools search "<intent>" --json`.

## Workflow

```mermaid
flowchart TD
    UserQuery["User Request (e.g. 'Rings boosting spell DC')"] --> Translate["Translate to CLI Arguments"]
    Translate --> Query["Run bg3 query --json"]
    Query --> Verify["Verify Query Response"]
    Verify --> Synthesize["Synthesize Recommendations & Synergies"]
```

### 1. Query Translation

| User Intent | CLI Command |
| :--- | :--- |
| Boosts specific stat | `uv run bg3 query --boost "SpellSaveDC" --json` |
| Specific equipment slot | `uv run bg3 query --slot "Amulet" --json` |
| Specific passive | `uv run bg3 query --passive "ExtraAttack" --json` |
| Slot + Rarity combination | `uv run bg3 query --slot "Boots" --rarity "Legendary" --json` |
| Thematic keyword search | `uv run bg3 query --search "necrotic" --json` |

### 2. Synthesize Advice
Structure recommendations with Item Name, Slot, Mod Source, Key Effects, and Build Synergies. Note early-game container drop mechanics via `bg3 mod inject-treasure`.

---

## Verification Gate

Always verify query results before presenting to user:
1. Verify `bg3 query` exits with code 0.
2. If the query database is empty or missing, rebuild it with `uv run bg3 query --reindex`.
3. Confirm returned items exist in [`mods/library.md`](../../../mods/library.md) or [`mods/`](../../../mods).
