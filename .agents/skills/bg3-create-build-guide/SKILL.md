---
name: bg3-create-build-guide
description: Generate Level 20 BG3 build guides with Best-in-Slot modded gear, progression tables, and Turn 1 combat sequences. Use on /build_guide or when creating build guides.
---

# BG3 Level 20 Build Guide Creator (`bg3-create-build-guide`)

Guides creation of comprehensive Level 20 *Baldur's Gate 3* build guides following the conventions in [`build_guides/`](../../../build_guides).

Refer to specifications:
- Document Template: [Build Guide Template](./resources/build_guide_template.md)
- Feats & Mechanics: [Build Conventions](./references/build_conventions.md)

---

> [!TIP]
> Query the studio tool registry with `python3 scripts/bg3.py tools search "<intent>" --json`.

## Workflow Overview

1. **Parameters & Role**: Determine class split (totaling 20), starting class, archetype (Caster, Hybrid, Pure Melee).
2. **Mod & Gear Inspection**: Inspect [`mods/`](../../../mods) for mod items (e.g. *Sets of Faerun*). Fall back to top-tier vanilla gear.
3. **Synergy Simulation**: Calculate Turn 1 DPR, Spell DC, and slot matrices:
   ```bash
   python3 scripts/bg3.py build simulate --classes "<Class=Level,...>" --stats "<S=N,D=N,C=N,I=N,W=N,Ch=N>" --gear "<Items>" --dpr-sequence <melee_burst|eldritch_blast> --json
   ```
4. **Draft Guide**: Populate the 5 standardized sections following the [Build Guide Template](./resources/build_guide_template.md).
5. **Artifact Delivery**: Write the complete document to disk under `build_guides/<category>/build_guide_<classes>.md`. Deliver concise executive summary in chat with file link.

---

## Verification Gate

Always verify the generated build guide before concluding:
1. Verify simulator command exits with code 0 and valid metrics.
2. Confirm all 20 progression levels are represented and total exactly 20.
3. Confirm Pure Melee guides omit spell columns per [Build Conventions](./references/build_conventions.md).
4. Verify all relative links to [`mods/`](../../../mods) resolve correctly.
