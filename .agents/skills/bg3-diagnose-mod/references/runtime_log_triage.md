# Toolkit Runtime Log Diagnosis & Triage Reference

## 1. Engine Log Inspection

Execute deterministic triage against BG3 Toolkit (`Glasses.exe`) sessions:
```bash
# General warning/error triage
python3 scripts/bg3.py mod diagnose-logs --mod <mod-slug> --severity warning --json

# Filter by engine subsystem
python3 scripts/bg3.py mod diagnose-logs --subsystem Boosts --mod <mod-slug> --json
python3 scripts/bg3.py mod diagnose-logs --subsystem Stats --mod <mod-slug> --json
python3 scripts/bg3.py mod diagnose-logs --subsystem Osiris --mod <mod-slug> --json

# Live stream active session
python3 scripts/bg3.py mod diagnose-logs --follow
```

---

## 2. Automated Remediation Guidelines

1. **Missing String Handles**: If logs indicate missing localization handles, run:
   ```bash
   python3 scripts/bg3.py mod sync-localization --mod <mod-slug> --write --json
   ```
2. **Stat Typo / Missing Reference**: Correlate logged IDs to `Public/<ModName>_<UUID>/Stats/Generated/Data/`.
3. **Circuit Breaker Guardrail**:
   - Limit continuous diagnostic cycles to 3 iterations.
   - If identical error signatures persist across 2 cycles, halt and prompt the user with log traces.
