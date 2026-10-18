# Arcane Progression

- **Mod slug:** `arcane-progression`
- **Module UUID:** `cfef8d1a-128b-4b02-b518-4177f162e61a`
- **Larian folder:** `ArcaneProgression_cfef8d1a-128b-4b02-b518-4177f162e61a`
- **Version:** `1.1.0.0`
- **Author:** MTGHillGiant

## Overview

Arcane Progression is a comprehensive companion patch mod for UnlockLevelCurve (by Charis). While UnlockLevelCurve unlocks character levels up to 20 and integrates high-level spell slots and upcasting, many iconic 5th Edition D&D class and subclass features between levels 13 and 20 were left unimplemented, broken, or unlocalized.

Built natively for Patch 7 and Patch 8 console and PC play, Arcane Progression completes the Level 13–20 progression curve across all 12 classes and their archetypes without external script extender dependencies.

---

## Features

### Base Class Features (Levels 13–20)

| Class | Level | Feature | Mechanics |
| :--- | :---: | :--- | :--- |
| **Barbarian** | 18 | **Indomitable Might** | Grants advantage on all Strength checks, saving throws, and raw ability tests. |
| **Bard** | 14 | **Magical Secrets** | Broadens high-tier spell choices: select two spells from any class spell catalog. |
| **Bard** | 15 | **Bardic Inspiration (d12)** | Fixes the parent mod's empty passive, properly scaling inspiration and combat inspiration dice to d12. |
| **Bard** | 18 | **Magical Secrets (High Tier)** | Select two additional high-level spells across all class spell lists. |
| **Cleric** | 14 & 17 | **Destroy Undead (CR 3 & 4)** | Turned undead take 8d6 (CR 3) or 12d6 (CR 4) Radiant damage and have Undead Fortitude suppressed. |
| **Cleric** | 20 | **Divine Intervention: Reborn** | Reusable manifestation of Divine Intervention (Golden Chest, Sunder the Heretical, Opulent Revival, or Arm Thy Servant) once per Long Rest. |
| **Druid** | 18 | **Beast Spells** | Cast verbal and somatic spells while transformed in Wild Shape. |
| **Druid** | 20 | **Archdruid** | Unlimited Wild Shape transformations (`ActionResource(WildShape, 97, 0)`). |
| **Fighter** | 17 | **Action Surge (2 Uses)** | Grants a second charge of Action Surge per Short Rest (`Shout_ActionSurge_2`). |
| **Monk** | 14 | **Diamond Soul** | Proficiency across all 6 saving throws and a reaction to spend 1 Ki point to reroll a failed save. |
| **Monk** | 18 | **Empty Body** | Active shout costing 4 Ki: Invisibility and resistance to all damage types except Force for 10 turns. |
| **Paladin** | 14 | **Cleansing Touch** | Purge harmful magical ailments, charms, curses, and conditions from self or allies. |
| **Paladin** | 18 | **Aura Range Improvement** | Expands protective Paladin auras outwards to a 9m/10m (30ft) radius. |
| **Ranger** | 14 | **Vanish** | Use the Hide action as a Bonus Action. |
| **Ranger** | 18 | **Feral Senses** | Immunity to Blinded and permanent detection of invisible creatures within 9m. |
| **Ranger** | 20 | **Foe Slayer** | Adds Wisdom modifier to weapon attack rolls and damage rolls. |
| **Rogue** | 14 | **Blindsense** | Fixes empty parent passive: detects invisible creatures within 10m and grants Blindness immunity. |
| **Rogue** | 18 | **Elusive (Fixed)** | Attackers cannot land critical hits or roll with advantage against the Rogue while not incapacitated. |
| **Rogue** | 20 | **Stroke of Luck** | Once per Short Rest, turn a missed attack roll into an immediate reroll with advantage. |
| **Warlock** | 15 & 18 | **High-Tier Invocations** | Level 15: _Master of Myriad Forms_ (at-will _Disguise Self_); Level 18: _Shroud of Shadows_ (at-will _Invisibility_). |
| **Wizard** | 18 | **Spell Mastery** | Select one 1st-level and one 2nd-level wizard spell to cast at will without expending spell slots. |

---

### Subclass Features (Levels 13–20)

| Subclass | Parent Class | Level | Feature | Mechanics |
| :--- | :--- | :---: | :--- | :--- |
| **College of Swords** | Bard | 14 | **Master's Flourish** | Perform Defensive, Mobile, and Slashing flourishes using a free d6 boost without expending Bardic Inspiration. |
| **Life Domain** | Cleric | 17 | **Supreme Healing** | Maximizes healing dice on all cast spells restoring hit points. |
| **Trickery Domain** | Cleric | 17 | **Improved Duplicity** | Bonus action defensive illusion granting Mirror Image charges and attack roll advantage for 10 turns. |
| **Nature Domain** | Cleric | 17 | **Master of Nature** | Charm Animals and Plants as a Bonus Action. |
| **Knowledge Domain** | Cleric | 17 | **Visions of the Past** | Expertise in History and Insight, with permanent Advantage on Perception checks. |
| **Circle of the Land** | Druid | 14 | **Nature's Sanctuary** | Beasts and plants attacking the Druid suffer Disadvantage on attack rolls. |
| **Champion** | Fighter | 18 | **Survivor (Fixed)** | Dynamic percentage scaling: regains 5 + Constitution modifier HP each turn when below 50% HP. |
| **Eldritch Knight** | Fighter | 15 | **Arcane Charge** | Teleport up to 9m as a reaction or bonus action whenever Action Surge is unleashed. |
| **Way of the Open Hand** | Monk | 17 | **Quivering Palm** | Strike with lethal vibrations (3 Ki); detonate at will forcing a CON save for 10d10 Necrotic damage. |
| **Way of the Four Elements**| Monk | 17 | **Elemental Attunement** | Damage resistance across elemental types and +2 bonus Ki points. |
| **Way of Shadow** | Monk | 17 | **Opportunist** | Reaction melee strike when an ally hits an adjacent hostile creature. |
| **Oath of Devotion** | Paladin | 15 | **Purity of Spirit** | Permanent immunity to Charmed/Frightened with continuous _Protection from Evil and Good_. |
| **Oath of Devotion** | Paladin | 20 | **Holy Nimbus** | 10-turn avatar of light: 9m sunlight dealing 10 Radiant damage/turn with advantage on spell saves. |
| **Oath of the Ancients** | Paladin | 15 | **Undying Sentinel** | Drop to 1 HP instead of 0 HP once per Long Rest. |
| **Oath of the Ancients** | Paladin | 20 | **Elder Champion** | 10-turn avatar of nature: regenerate 10 HP per turn and cast Paladin spells as Bonus Actions. |
| **Oath of Vengeance** | Paladin | 15 | **Soul of Vengeance** | Reaction melee strike whenever a creature under Vow of Enmity makes an attack. |
| **Oath of Vengeance** | Paladin | 20 | **Avenging Angel** | 10-turn avatar of vengeance: 18m flight wings and a 9m aura imposing Frightened on enemies. |
| **Oathbreaker** | Paladin | 15 | **Supernatural Resistance**| Resistance to non-magical bludgeoning, piercing, and slashing damage. |
| **Oathbreaker** | Paladin | 20 | **Dread Lord** | 10-turn avatar of gloom: 9m dark aura imposing disadvantage on enemy attack rolls and dealing 4d10 psychic damage to frightened foes. |
| **Beast Master** | Ranger | 15 | **Share Spells** | Beneficial spells cast on the Ranger automatically apply to their summoned beast companion. |
| **Gloom Stalker** | Ranger | 15 | **Shadowy Dodge** | Reaction when attacked to impose disadvantage on the attacker's roll. |
| **Hunter** | Ranger | 15 | **Superior Hunter's Defense** | Gains Evasion to negate area damage on successful Dexterity saving throws. |
| **Arcane Trickster** | Rogue | 13 | **Versatile Trickster** | Advantage on attack rolls when an ally or Mage Hand is within 3m, with a distracting bonus action. |
| **Assassin** | Rogue | 17 | **Death Strike** | Automatically doubles all damage dealt against Surprised foes. |
| **Thief** | Rogue | 13 | **Use Magic Device** | Ignore class restrictions on scrolls and magic items, with a bonus to saving throws. |
| **Thief** | Rogue | 17 | **Thief's Reflexes** | Gain an extra Action during the first round of combat. |
| **Draconic Bloodline** | Sorcerer | 14 | **Dragon Wings** | Manifest permanent dragon wings granting flight at will and bonus movement speed. |
| **Storm Sorcery** | Sorcerer | 14 | **Storm's Fury** | Reaction when struck by a melee attack: deals 14 Lightning damage and pushes attacker 6m. |
| **Wild Magic** | Sorcerer | 14 | **Controlled Chaos** | Reaction when an enemy casts a spell to force them to roll on the hostile Wild Magic Surge table. |
| **The Fiend** | Warlock | 14 | **Hurl Through Hell** | Banish target through the Lower Planes for 1 turn; deals 10d10 Psychic damage upon return. |
| **The Great Old One** | Warlock | 14 | **Create Thrall** | Permanently dominate an incapacitated or sleeping humanoid to serve as your thrall. |
| **The Archfey** | Warlock | 14 | **Dark Delirium** | Banish target into an illusory mist where they are charmed, frightened, and incapacitated. |
| **Abjuration School** | Wizard | 14 | **Spell Resistance** | Advantage on all saving throws against spells and resistance against spell damage. |
| **Conjuration School** | Wizard | 14 | **Focused Conjuration** | Damage cannot break concentration on Conjuration spells. |
| **Divination School** | Wizard | 14 | **Greater Portent** | Gain a 3rd Portent die per Long Rest. |
| **Evocation School** | Wizard | 14 | **Overchannel** | Maximize damage dice on 1st–5th level spells once per Short Rest. |
| **Necromancy School** | Wizard | 14 | **Command Undead** | Use an action to seize mental control of target undead via a Wisdom contest. |
| **Transmutation School**| Wizard | 14 | **Master Transmuter** | Panacea: restore touched creature to maximum HP and cure all conditions and curses. |
| **Enchantment School** | Wizard | 14 | **Split Enchantment** | Twin single-target Enchantment spells onto a second target simultaneously. |
| **Illusion School** | Wizard | 14 | **Illusory Self** | Reaction once per Short Rest to cause an attack roll that hits you to automatically miss. |

---

### Wizard Spell Mastery Options

- **Level 1:** _Shield, Mage Armor, Magic Missile, Longstrider, Fog Cloud, Grease, Feather Fall, Thunderwave, Burning Hands, Chromatic Orb, Ray of Sickness,_ and _False Life_.
- **Level 2:** _Misty Step, Mirror Image, Blur, Web, Darkness, Scorching Ray, Hold Person, Invisibility, Cloud of Daggers, Shatter, Blindness,_ and _Phantasmal Force_.

---

## Dependencies & Compatibility

- **Required:** Baldur's Gate 3 base game module `GustavX`.
- **Required:** `UnlockLevelCurve` (`a2ffd0e4-c407-8642-2611-c934ea0b0a77`). Load UnlockLevelCurve before Arcane Progression.
- **Compatibility:** Authored for Patch 7 and Patch 8 Native Toolkit (PC and consoles). Fully compatible with custom load orders and progression patches.
