# Remediation & Return Message Templates

## Standardized Return Messages

### Mode 1: Candidate vs. Library
- Clean:
  ```text
  No conflicts found with existing mods
  ```
- Conflict Detected:
  ```text
  Possible conflict found: <Tracked Mod Name> - <Brief description of the issue>
  ```
- Console Load Order Conflict:
  ```text
  Possible conflict found: <Tracked Mod Name> - <Brief description of issue> [Console Load Order: cannot reorder on console to ensure proper override]
  ```

### Mode 2: Cross-Candidate Batch
- Clean Batch:
  ```text
  No conflicts found between candidate mods
  ```
- Conflict Detected:
  ```text
  Possible conflict found: <Candidate Mod 1> vs <Candidate Mod 2> - <Brief description of the conflict>
  ```
- Console Conflict Detected:
  ```text
  Possible conflict found: <Candidate Mod 1> vs <Candidate Mod 2> - <Brief description of issue> [Console Load Order: cannot reorder on console to resolve override order]
  ```

---

## Automated Patch Generation Commands

> [!NOTE]
> Patch scaffolding commands require the `bg3-authoring` package (`pip install bg3-authoring`).

```bash
# Generate standalone compatibility override patch mod
bg3 mod patch --mod1 <mod1> --mod2 <mod2> --name "<Mod1><Mod2>Patch" --mode standalone --json

# Generate Compatibility Framework config payload
bg3 mod patch --mod1 <mod1> --mod2 <mod2> --mode cf --json
```
