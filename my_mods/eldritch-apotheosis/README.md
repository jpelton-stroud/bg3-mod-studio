# Eldritch Apotheosis

- **Mod slug:** `eldritch-apotheosis`
- **Module UUID:** `e1d817c0-a907-4e05-9b24-7f83a005e0ab`
- **Larian folder:** `EldritchApotheosis_e1d817c0-a907-4e05-9b24-7f83a005e0ab`
- **Version:** `1.0.0.0`
- **Author:** MTGHillGiant

## Overview

**Eldritch Apotheosis** completely overhauls the iconic Warlock cantrip *Eldritch Blast*, reimagining its progression from character Level 1 through Level 20.

### The Companion to Eldritch Ascension
In the modded Baldur's Gate 3 ecosystem, **Eldritch Ascension** (`PactOfTheBladeUnleashed`) fulfills the ultimate martial gish fantasy: dual-wield pact binding, 4 melee attacks, and necrotic vampirism. 

**Eldritch Apotheosis** serves as its direct spellcaster counterpart:
- Elevates the pure blaster cantrip fantasy to catastrophic heights.
- Harmonizes with **UnlockLevelCurve** (Levels 13–20) so Warlock cantrips stay neck-and-neck with high-tier martial multi-attacks and 9th-level spells like *Meteor Swarm* and *Wish*.
- Delivers a satisfying, continuous sense of progression across all three Acts and beyond. Rather than waiting long dry spells between beam spikes, your eldritch power steadily swells through escalating projectile counts, scaling damage dice riders, and innate Charisma multipliers.

---

## Features

### 1. Beam Count Scaling (`LevelMapSeries: EldritchBlast`)
*UUID*: `ecad9e7a-389d-4789-ba69-898cfd34da3c`  
*Fallback Value*: `2`

Unlike vanilla BG3 (which starts at 1 beam and caps at 3 beams at Level 10), Eldritch Apotheosis scales from **2 beams at Level 1** up to a devastating volley of **10 beams at Level 20**.

| Tier | Character Level | Beams Fired | Design & Power Rationale |
| :--- | :---: | :---: | :--- |
| **Tier 1: Act 1 Baseline** | **Level 1 – 4** | **2** | Immediate dual-beam baseline cementing the Warlock's role as a dedicated ranged artillery caster. |
| **Tier 2: Midgame Spike** | **Level 5 – 9** | **3** | Standard D&D 5e Level 5 power spike matching extra attack martial progressions. |
| **Tier 3: Endgame Cap** | **Level 10 – 12** | **4** | Outpaces vanilla cap (+1 beam over vanilla) for high-intensity Act 3 encounters. |
| **Epic Tier (ULC)** | **Level 13 – 14** | **5** | Transitions into epic play; +1 beam every 2 levels. |
| **Epic Tier (ULC)** | **Level 15 – 16** | **6** | Sustained epic multi-targeting barrage. |
| **God Tier** | **Level 17** | **7** | High-magic acceleration (+1 beam every level). |
| **God Tier** | **Level 18** | **8** | Heavy artillery volley across split targets. |
| **God Tier** | **Level 19** | **9** | Near-maximum eldritch saturation. |
| **Apotheosis Capstone** | **Level 20** | **10** | Maximum level capstone: fires 10 beams per cast, rivaling 9th-level spell slot salvos. |

---

### 2. Scaling Damage Dice Rider (`LevelMapSeries: EldritchBlastDamageRider`)
*UUID*: `b4e18d3f-5612-4c28-9844-48b9f0e137b2`  
*Fallback Value*: `0`

In addition to base $1\text{d}10$ Force damage per beam, Eldritch Apotheosis applies an escalating damage dice rider that grows automatically with your character level:

| Tier | Character Level | Bonus Dice Rider | Base + Rider per Beam | Avg Base Dice Damage |
| :--- | :---: | :---: | :---: | :---: |
| **Tier 1** | **Level 1 – 4** | **None (+0)** | $1\text{d}10$ Force | $5.5$ |
| **Tier 2** | **Level 5 – 9** | **+1d4** | $1\text{d}10 + 1\text{d}4$ Force | $8.0$ |
| **Tier 3** | **Level 10 – 12** | **+1d6** | $1\text{d}10 + 1\text{d}6$ Force | $9.0$ |
| **Epic Tier** | **Level 13 – 16** | **+1d8** | $1\text{d}10 + 1\text{d}8$ Force | $10.0$ |
| **God Tier** | **Level 17 – 19** | **+1d10** | $1\text{d}10 + 1\text{d}10$ ($2\text{d}10$) Force | $11.0$ |
| **Capstone** | **Level 20** | **+1d12** | $1\text{d}10 + 1\text{d}12$ Force | $12.0$ |

---

### 3. Innate Charisma Scaling Multipliers
Authored in [`Spell_Projectile.txt`](file:///home/jpstroud/projects/BaldursGate3/my_mods/eldritch-apotheosis/Public/EldritchApotheosis_bdfd89d8-be6b-2bb0-f2e9-9588a3f5e0ab/Stats/Generated/Data/Spell_Projectile.txt):

- **Levels 1–12 (Acts 1–3 Baseline)**: 
  Standard cantrip mechanics. Warlocks rely on the *Agonizing Blast* Eldritch Invocation for $+1\times \text{CHA}$ modifier on hit.
- **Levels 13–19 (Epic Tier Awakening)**: 
  `+1x Charisma Modifier` Force damage is applied **innately** to every beam on hit via:  
  `IF(CharacterLevelGreaterThan(12) and IsCharismaModifierPositive()):DealDamage(CharismaModifier,Force,Magical)`
- **Level 20 (Apotheosis Capstone)**: 
  An additional `+1x Charisma Modifier` Force damage is applied (granting **$+2\times \text{CHA}$ innate modifier**) via a second sequential check:  
  `IF(CharacterLevelGreaterThan(19) and IsCharismaModifierPositive()):DealDamage(CharismaModifier,Force,Magical)`

#### Additive Stacking with Invocations & Items
These innate scaling tiers stack fully and additively with class passives and gear:
- **Agonizing Blast** (Warlock Invocation): $+1\times \text{CHA}$
- **Potent Robe** (*Gregarious Spellcaster*): $+1\times \text{CHA}$
- **Level 13–19 Synergized**: $+1\times (\text{Innate}) + 1\times (\text{Agonizing}) + 1\times (\text{Potent Robe}) = \mathbf{+3\times \text{CHA}}$ per beam.
- **Level 20 Synergized**: $+2\times (\text{Innate}) + 1\times (\text{Agonizing}) + 1\times (\text{Potent Robe}) = \mathbf{+4\times \text{CHA}}$ per beam!

---

## Detailed Combat Math Breakdown

The tables below contrast damage per beam and total volley damage across landmark levels.

> **Assumption for Optimized Values**:
> - Level 1: 16 CHA (+3 mod)
> - Level 5: 18 CHA (+4 mod)
> - Level 10: 20 CHA (+5 mod)
> - Level 13 & 17: 22 CHA (+6 mod via Mirror of Loss / ASI)
> - Level 20: 24 CHA (+7 mod via Birthright / Duke Ravengard's Longsword / Mirror of Loss)

### Table 1: Damage Per Single Beam Hit

| Level | Beams | Base Dice + Rider | Innate CHA | Agonizing Blast | Potent Robe | Total Single-Beam Damage (Min – Max, Avg) |
| :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **1** | 2 | $1\text{d}10$ | $+0$ | $+3$ | — | **$4 - 13$** (Avg **$8.5$**) |
| **5** | 3 | $1\text{d}10 + 1\text{d}4$ | $+0$ | $+4$ | $+4$ | **$10 - 22$** (Avg **$16.0$**) |
| **10** | 4 | $1\text{d}10 + 1\text{d}6$ | $+0$ | $+5$ | $+5$ | **$12 - 26$** (Avg **$19.0$**) |
| **13** | 5 | $1\text{d}10 + 1\text{d}8$ | $+6$ | $+6$ | $+6$ | **$20 - 36$** (Avg **$28.0$**) |
| **17** | 7 | $1\text{d}10 + 1\text{d}10$ | $+6$ | $+6$ | $+6$ | **$20 - 38$** (Avg **$29.0$**) |
| **20** | 10 | $1\text{d}10 + 1\text{d}12$ | $+14$ | $+7$ | $+7$ | **$30 - 50$** (Avg **$40.0$**) |

---

### Table 2: Total Damage Volley Across All Beams

| Level | Beams | Baseline (Raw Dice Only) | Agonizing Blast Only | Fully Synergized Volley (Innate + Agonizing + Potent Robe) |
| :---: | :---: | :--- | :--- | :--- |
| **1** | 2 | $2\text{d}10$ (Avg **$11.0$**) | $2\text{d}10 + 6$ (Avg **$17.0$**, Max 26) | $2\text{d}10 + 6$ (Avg **$17.0$**) |
| **5** | 3 | $3\text{d}10 + 3\text{d}4$ (Avg **$24.0$**) | $3\text{d}10 + 3\text{d}4 + 12$ (Avg **$36.0$**, Max 54) | $3\text{d}10 + 3\text{d}4 + 24$ (Avg **$48.0$**, Max 66) |
| **10** | 4 | $4\text{d}10 + 4\text{d}6$ (Avg **$36.0$**) | $4\text{d}10 + 4\text{d}6 + 20$ (Avg **$56.0$**, Max 84) | $4\text{d}10 + 4\text{d}6 + 40$ (Avg **$76.0$**, Max 104) |
| **13** | 5 | $5\text{d}10 + 5\text{d}8 + 30$ (Avg **$80.0$**) | $5\text{d}10 + 5\text{d}8 + 60$ (Avg **$110.0$**, Max 150) | $5\text{d}10 + 5\text{d}8 + 90$ (Avg **$140.0$**, Max 180) |
| **17** | 7 | $14\text{d}10 + 42$ (Avg **$119.0$**) | $14\text{d}10 + 84$ (Avg **$161.0$**, Max 224) | $14\text{d}10 + 126$ (Avg **$203.0$**, Max 266) |
| **20** | 10 | $10\text{d}10 + 10\text{d}12 + 140$ (Avg **$260.0$**) | $10\text{d}10 + 10\text{d}12 + 210$ (Avg **$330.0$**, Max 430) | $\mathbf{10\text{d}10 + 10\text{d}12 + 280}$ (Avg **$400.0$**, Max **$500.0$**) |

> [!TIP]
> **Turn 1 Burst Synergy with Eldritch Ascension**:  
> If using both mods, striking an enemy in melee activates **Eldritch Weaving**, unlocking *Eldritch Blast* as a **Bonus Action**. At Level 20, a Warlock can unleash an opening melee combo followed by a 10-beam bonus action volley, generating **$600+$ total Force & weapon damage in a single round** without consuming spell slots.

---

## Dependencies

- **Required:** Baldur's Gate 3 base game module `GustavX`.
- **Optional progression mod:** UnlockLevelCurve unlocks this mod's Level 13–20 progression; without it, the mod functions through Level 12.

## Compatibility

- **Clean Additive Override**:  
  Eldritch Apotheosis overrides `Projectile_EldritchBlast` using Larian's inheritance directive (`using "Projectile_EldritchBlast"`). No core story scripts or base game asset files are touched.
- **Safe Mid-Campaign**:  
  Can be safely installed or updated in existing savegames without causing progression lock or missing spell entries.
- **UnlockLevelCurve compatible:**
  Designed from the ground up for levels 13–20. If playing with standard Level 12 caps, the mod functions through Tier 3 (4 beams, 1d6 rider). Installing `UnlockLevelCurve` unlocks Tiers 4–6 through Level 20.
- **Passive & Item Synergy**:  
  Preserves `Repelling Blast` pushback mechanics (`Force(4.5)`), *Spellmight Gloves*, *Callous Glow Ring*, and all other damage riders that trigger on cantrip / spell hit.

---

### Installation & Toolkit Sync

### Method 1: Automatic Game Data Sync (Recommended)
Sync mod files directly into your Baldur's Gate 3 `Data/` directory using the workspace synchronization script:

```bash
# Standard sync
python3 scripts/sync_game_data.py --mods eldritch-apotheosis

# Preview changes without modifying files
python3 scripts/sync_game_data.py --mods eldritch-apotheosis --dry-run

# Live watcher mode for real-time development
python3 scripts/sync_game_data.py --mods eldritch-apotheosis --watch
```

### Method 2: Manual Toolkit Workspace Import
1. Locate your game's **Data** folder (e.g., `C:\Program Files (x86)\Steam\steamapps\common\Baldurs Gate 3\Data\`).
2. Copy the folders from this mod directory directly into `Data/`:
   - `Projects/`
   - `Mods/`
   - `Public/`
   - `Localization/`
3. Launch the **Baldur's Gate 3 Toolkit** (Patch 7 / Patch 8).
4. Select **File -> Open Project...** and choose **EldritchApotheosis**.
5. Save and Publish to mod.io or export as a `.pak`.

---

### File Structure

```text
my_mods/eldritch-apotheosis/
├── Projects/EldritchApotheosis_e1d817c0-a907-4e05-9b24-7f83a005e0ab/
│   ├── meta.lsx                                # Toolkit project metadata
│   └── thumbnail.png                           # Toolkit project icon (2.6 MB)
├── Mods/EldritchApotheosis_e1d817c0-a907-4e05-9b24-7f83a005e0ab/
│   ├── meta.lsx                                # Engine module definition & UUID
│   └── mod_publish_logo.png                    # mod.io / in-game mod manager logo (2.6 MB)
├── Public/EldritchApotheosis_e1d817c0-a907-4e05-9b24-7f83a005e0ab/
│   ├── LevelMapValues/
│   │   └── LevelMapValues.lsx                  # 2-10 Beams & d4-d12 damage dice LevelMaps
│   └── Stats/Generated/Data/
│       └── Spell_Projectile.txt                # Eldritch Blast projectile override & CHA scaling
├── Editor/Mods/EldritchApotheosis_e1d817c0-a907-4e05-9b24-7f83a005e0ab/
│   └── Assets/                                 # Editor assets scaffolding
├── Localization/English/
│   └── EldritchApotheosis.xml                  # English localization strings
├── thumbnail.png                               # Mod directory preview thumbnail (2.6 MB)
└── README.md                                   # Comprehensive documentation & combat math
```

---

## Additional Credits

None listed.
