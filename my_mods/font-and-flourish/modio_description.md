# FontAndFlourish
**Author:** MTGHillGiant

## Overview
Enhances College of Swords Bard and Bardic Inspiration with D&amp;D 2024 spell-slot-to-Inspiration conversion (free action with upcasting) and targeted multi-attack Melee Slashing Flourish.

## Features Included
### Spells & Actions
| Spell Name | Type | Level | Description |
| :--- | :--- | :--- | :--- |
| **Font of Inspiration** | Shout | - | Harmonize your magical reserves. Expend a spell slot to restore [1] charge of Bardic Inspiration. |
| **Shout_FontOfInspiration_2** | Shout | - | Shout_FontOfInspiration_2 |
| **Shout_FontOfInspiration_3** | Shout | - | Shout_FontOfInspiration_3 |
| **Shout_FontOfInspiration_4** | Shout | - | Shout_FontOfInspiration_4 |
| **Shout_FontOfInspiration_5** | Shout | - | Shout_FontOfInspiration_5 |
| **Shout_FontOfInspiration_6** | Shout | - | Shout_FontOfInspiration_6 |
| **Slashing Flourish (Melee)** | Target | Cantrip | Attack up to [1] enemies within melee reach, or strike the same enemy twice. Deals an extra 1d6 damage. |
| **Zone_BladeFlourish_Slashing** | Zone | - | Zone_BladeFlourish_Slashing |

### Passives & Traits
| Passive Name | Boosts / Properties | Description |
| :--- | :--- | :--- |
| **FontOfInspiration** | `ActionResourceReplenishTypeOverride(BardicInspiration,ShortRest);UnlockSpell(Shout_FontOfInspiration)` | You regain all of your expended uses of Bardic Inspiration when you finish a Short or Long Rest. In addition, you can expend a spell slot with Font of Inspiration to regain Bardic Inspiration uses. |

## Dependencies & Load Order
This mod requires the following parent dependencies to be loaded before it:
- **GustavDev** (`28ac9ce2-2aba-8cda-b3b5-6e922f71b6b8`)

## Recommended Toolkit Tags
`Combat, Spells`
