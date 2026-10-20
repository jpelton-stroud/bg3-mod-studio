# Campaign Save Audit & Integration Runbook (Phase 3B)

## 1. Full Load Order Placement
For complex integration with other community mods:
```bash
python3 scripts/bg3.py loadorder --enable <mod-slug> --validate --json
```

---

## 2. Campaign Save Game Audit

Inspect campaign saves to ensure compatibility across installed mods:
```bash
# Pre-flight audit
python3 scripts/bg3.py mod inspect-save --audit --json

# Post-test module persistence verification
python3 scripts/bg3.py mod inspect-save --json
```
Confirm the mod's UUID is recorded in the save file's module list without corruption before proceeding to release.
