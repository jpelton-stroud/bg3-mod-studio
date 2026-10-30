# Clean-Room Smoke Testing Runbook (Phase 3A)

## 1. Clean-Room Load Order Isolation
Activate the mod while isolating the profile so that only declared dependencies and test companions are active:
```bash
# Isolate mod with prerequisites
uv run bg3 loadorder --enable <mod-slug> --with-deps --isolate --json

# Optional test companions (e.g. instant XP)
uv run bg3 loadorder --enable <mod-slug> --with-deps --isolate --test-dep "UnlockLevelCurve - Instant XP" --json
```

Verify in JSON:
- `isolated_count`: number of unrelated mods disabled.
- `enable.missing_dependencies`: must be empty.

---

## 2. In-Game Smoke Test Checklist
1. **Acquisition**: Check container drops (Tutorial / Camp Chest) or vendor stocks.
2. **Tooltips**: Verify spell and item names and descriptions render properly (no raw handles).
3. **Mechanics**: Cast spells, verify passive triggers on turn start/hit, test level-up trees.
4. **Persistence**: Save game, reload, and verify state persistence.
