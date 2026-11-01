# Campaign Save Audit & Integration Runbook (Phase 3B)

## 1. Full Load Order Placement
For complex integration with other community mods:
```bash
bg3 loadorder enable "<mod-slug>" --json
bg3 loadorder validate --json
```

---

## 2. Campaign Save Game Audit

Inspect campaign saves to ensure compatibility across installed mods:
```bash
# Pre-flight audit
bg3 mod inspect-save --audit --json

# Post-test module persistence verification
bg3 mod inspect-save --json
```
Confirm the mod's UUID is recorded in the save file's module list without corruption before proceeding to release.
