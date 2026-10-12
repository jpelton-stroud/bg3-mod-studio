# Mod Specification: UnlockLevelCurve - Level 13-20 | Patch 8
**Category**: Classes & Subclasses | **Author**: Charis | **Version**: 144255927717156327 | **mod.io ID**: `4166963`
**URL**: `https://mod.io/g/baldursgate3/m/unlocklevelcurve`

---

## Overview
UnlockLevelCurve extends character progression in Baldur's Gate 3 from level 12 up to level 20, incorporating custom XP curves and full class/subclass progression trees for all base classes. It integrates higher-tier spell slots (up to 9th level), upcasted and newly scaled class spells, high-level class features (such as Eldritch Master, higher-level Wild Shapes, expanded Paladin auras, and extra sneak attack/feat progression), and seamless integration into the game's level-up interface.

This mod serves as the foundational framework for Level 13–20 epic character builds and multiclassing combinations, synergizing with custom XP curve modifiers and high-tier modded gear.

---

## Implemented In-Game Features

| Feature Name & Type | In-Game Identifier | Base Stats & Modifiers | Granted Abilities, Spells & Passives (Full Mechanics) | Acquisition & Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Target_EnsnaringStrike_7**<br>*Cantrip* | `Target_EnsnaringStrike_7` | **Cantrip** () | Mechanics: `IF(not SavingThrow(Ability.Strength,SourceSpellDC(),AdvantageOnRestrained(),DisadvantageOnRestrained())):ApplyStatus(ENSNARING_STRIKE_7,100,10);DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand)` | Learned via class level or granted by equipment |
| **Target_EnsnaringStrike_8**<br>*Cantrip* | `Target_EnsnaringStrike_8` | **Cantrip** () | Mechanics: `IF(not SavingThrow(Ability.Strength,SourceSpellDC(),AdvantageOnRestrained(),DisadvantageOnRestrained())):ApplyStatus(ENSNARING_STRIKE_8,100,10);DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand)` | Learned via class level or granted by equipment |
| **Target_EnsnaringStrike_9**<br>*Cantrip* | `Target_EnsnaringStrike_9` | **Cantrip** () | Mechanics: `IF(not SavingThrow(Ability.Strength,SourceSpellDC(),AdvantageOnRestrained(),DisadvantageOnRestrained())):ApplyStatus(ENSNARING_STRIKE_9,100,10);DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand)` | Learned via class level or granted by equipment |
| **Target_Smite_Banishing_7**<br>*Cantrip* | `Target_Smite_Banishing_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Banishing_8**<br>*Cantrip* | `Target_Smite_Banishing_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Banishing_9**<br>*Cantrip* | `Target_Smite_Banishing_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Blinding_7**<br>*Cantrip* | `Target_Smite_Blinding_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Blinding_8**<br>*Cantrip* | `Target_Smite_Blinding_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Blinding_9**<br>*Cantrip* | `Target_Smite_Blinding_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Branding_7**<br>*Cantrip* | `Target_Smite_Branding_7` | **Cantrip** () | Mechanics: `DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand);DealDamage(7d6,Radiant,Magical);ApplyStatus(BRANDING_SMITE,100,10)` | Learned via class level or granted by equipment |
| **Target_Smite_Branding_8**<br>*Cantrip* | `Target_Smite_Branding_8` | **Cantrip** () | Mechanics: `DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand);DealDamage(8d6,Radiant,Magical);ApplyStatus(BRANDING_SMITE,100,10)` | Learned via class level or granted by equipment |
| **Target_Smite_Branding_9**<br>*Cantrip* | `Target_Smite_Branding_9` | **Cantrip** () | Mechanics: `DealDamage(MainMeleeWeapon,MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand);DealDamage(9d6,Radiant,Magical);ApplyStatus(BRANDING_SMITE,100,10)` | Learned via class level or granted by equipment |
| **Target_Smite_Divine_7**<br>*Cantrip* | `Target_Smite_Divine_7` | **Cantrip** () | Mechanics: `DealDamage(MainMeleeWeapon, MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand);DealDamage(8d8,Radiant,Magical);IF(Tagged('FIEND')):DealDamage(1d8,Radiant,Magical);IF(Tagged('UNDEAD')):DealDamage(1d8,Radiant,Magical)` | Learned via class level or granted by equipment |
| **Target_Smite_Divine_8**<br>*Cantrip* | `Target_Smite_Divine_8` | **Cantrip** () | Mechanics: `DealDamage(MainMeleeWeapon, MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand);DealDamage(9d8,Radiant,Magical);IF(Tagged('FIEND')):DealDamage(1d8,Radiant,Magical);IF(Tagged('UNDEAD')):DealDamage(1d8,Radiant,Magical)` | Learned via class level or granted by equipment |
| **Target_Smite_Divine_9**<br>*Cantrip* | `Target_Smite_Divine_9` | **Cantrip** () | Mechanics: `DealDamage(MainMeleeWeapon, MainMeleeWeaponDamageType);ExecuteWeaponFunctors(MainHand);DealDamage(10d8,Radiant,Magical);IF(Tagged('FIEND')):DealDamage(1d8,Radiant,Magical);IF(Tagged('UNDEAD')):DealDamage(1d8,Radiant,Magical)` | Learned via class level or granted by equipment |
| **Target_Smite_Searing_7**<br>*Cantrip* | `Target_Smite_Searing_7` | **Cantrip** () | Mechanics: `DealDamage(MainMeleeWeapon, MainMeleeWeaponDamageType); ExecuteWeaponFunctors(MainHand); DealDamage(7d6, Fire,Magical); ApplyStatus(SEARING_SMITE, 100, 10)` | Learned via class level or granted by equipment |
| **Target_Smite_Searing_8**<br>*Cantrip* | `Target_Smite_Searing_8` | **Cantrip** () | Mechanics: `DealDamage(MainMeleeWeapon, MainMeleeWeaponDamageType); ExecuteWeaponFunctors(MainHand); DealDamage(8d6, Fire,Magical); ApplyStatus(SEARING_SMITE, 100, 10)` | Learned via class level or granted by equipment |
| **Target_Smite_Searing_9**<br>*Cantrip* | `Target_Smite_Searing_9` | **Cantrip** () | Mechanics: `DealDamage(MainMeleeWeapon, MainMeleeWeaponDamageType); ExecuteWeaponFunctors(MainHand); DealDamage(9d6, Fire,Magical); ApplyStatus(SEARING_SMITE, 100, 10)` | Learned via class level or granted by equipment |
| **Target_Smite_Thunderous_7**<br>*Cantrip* | `Target_Smite_Thunderous_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Thunderous_8**<br>*Cantrip* | `Target_Smite_Thunderous_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Thunderous_9**<br>*Cantrip* | `Target_Smite_Thunderous_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Wrathful_7**<br>*Cantrip* | `Target_Smite_Wrathful_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Wrathful_8**<br>*Cantrip* | `Target_Smite_Wrathful_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Smite_Wrathful_9**<br>*Cantrip* | `Target_Smite_Wrathful_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_StaggeringSmite_7**<br>*Cantrip* | `Target_StaggeringSmite_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_StaggeringSmite_8**<br>*Cantrip* | `Target_StaggeringSmite_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_StaggeringSmite_9**<br>*Cantrip* | `Target_StaggeringSmite_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CureWounds_7**<br>*Cantrip* | `Target_CureWounds_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CureWounds_8**<br>*Cantrip* | `Target_CureWounds_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CureWounds_9**<br>*Cantrip* | `Target_CureWounds_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_7**<br>*Cantrip* | `Target_EnhanceAbility_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_8**<br>*Cantrip* | `Target_EnhanceAbility_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_9**<br>*Cantrip* | `Target_EnhanceAbility_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BearsEndurance_7**<br>*Cantrip* | `Target_EnhanceAbility_BearsEndurance_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BearsEndurance_8**<br>*Cantrip* | `Target_EnhanceAbility_BearsEndurance_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BearsEndurance_9**<br>*Cantrip* | `Target_EnhanceAbility_BearsEndurance_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BearsEndurance_7_AI**<br>*Cantrip* | `Target_EnhanceAbility_BearsEndurance_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BearsEndurance_8_AI**<br>*Cantrip* | `Target_EnhanceAbility_BearsEndurance_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BearsEndurance_9_AI**<br>*Cantrip* | `Target_EnhanceAbility_BearsEndurance_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BullsStrength_7**<br>*Cantrip* | `Target_EnhanceAbility_BullsStrength_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BullsStrength_8**<br>*Cantrip* | `Target_EnhanceAbility_BullsStrength_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BullsStrength_9**<br>*Cantrip* | `Target_EnhanceAbility_BullsStrength_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BullsStrength_7_AI**<br>*Cantrip* | `Target_EnhanceAbility_BullsStrength_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BullsStrength_8_AI**<br>*Cantrip* | `Target_EnhanceAbility_BullsStrength_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_BullsStrength_9_AI**<br>*Cantrip* | `Target_EnhanceAbility_BullsStrength_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_CatsGrace_7**<br>*Cantrip* | `Target_EnhanceAbility_CatsGrace_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_CatsGrace_8**<br>*Cantrip* | `Target_EnhanceAbility_CatsGrace_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_CatsGrace_9**<br>*Cantrip* | `Target_EnhanceAbility_CatsGrace_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_CatsGrace_7_AI**<br>*Cantrip* | `Target_EnhanceAbility_CatsGrace_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_CatsGrace_8_AI**<br>*Cantrip* | `Target_EnhanceAbility_CatsGrace_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_CatsGrace_9_AI**<br>*Cantrip* | `Target_EnhanceAbility_CatsGrace_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_EaglesSplendor_7**<br>*Cantrip* | `Target_EnhanceAbility_EaglesSplendor_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_EaglesSplendor_8**<br>*Cantrip* | `Target_EnhanceAbility_EaglesSplendor_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_EaglesSplendor_9**<br>*Cantrip* | `Target_EnhanceAbility_EaglesSplendor_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_EaglesSplendor_7_AI**<br>*Cantrip* | `Target_EnhanceAbility_EaglesSplendor_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_EaglesSplendor_8_AI**<br>*Cantrip* | `Target_EnhanceAbility_EaglesSplendor_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_EaglesSplendor_9_AI**<br>*Cantrip* | `Target_EnhanceAbility_EaglesSplendor_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_FoxsCunning_7**<br>*Cantrip* | `Target_EnhanceAbility_FoxsCunning_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_FoxsCunning_8**<br>*Cantrip* | `Target_EnhanceAbility_FoxsCunning_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_FoxsCunning_9**<br>*Cantrip* | `Target_EnhanceAbility_FoxsCunning_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_FoxsCunning_7_AI**<br>*Cantrip* | `Target_EnhanceAbility_FoxsCunning_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_FoxsCunning_8_AI**<br>*Cantrip* | `Target_EnhanceAbility_FoxsCunning_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_FoxsCunning_9_AI**<br>*Cantrip* | `Target_EnhanceAbility_FoxsCunning_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_OwlsWisdom_7**<br>*Cantrip* | `Target_EnhanceAbility_OwlsWisdom_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_OwlsWisdom_8**<br>*Cantrip* | `Target_EnhanceAbility_OwlsWisdom_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_OwlsWisdom_9**<br>*Cantrip* | `Target_EnhanceAbility_OwlsWisdom_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_OwlsWisdom_7_AI**<br>*Cantrip* | `Target_EnhanceAbility_OwlsWisdom_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_OwlsWisdom_8_AI**<br>*Cantrip* | `Target_EnhanceAbility_OwlsWisdom_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_EnhanceAbility_OwlsWisdom_9_AI**<br>*Cantrip* | `Target_EnhanceAbility_OwlsWisdom_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Goodberry_7**<br>*Cantrip* | `Target_Goodberry_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Goodberry_8**<br>*Cantrip* | `Target_Goodberry_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Goodberry_9**<br>*Cantrip* | `Target_Goodberry_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Heroism_7**<br>*Cantrip* | `Target_Heroism_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Heroism_8**<br>*Cantrip* | `Target_Heroism_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Heroism_9**<br>*Cantrip* | `Target_Heroism_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Heroism_7_AI**<br>*Cantrip* | `Target_Heroism_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Heroism_8_AI**<br>*Cantrip* | `Target_Heroism_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Heroism_9_AI**<br>*Cantrip* | `Target_Heroism_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_InflictWounds_7**<br>*Cantrip* | `Target_InflictWounds_7` | **Cantrip** () | Mechanics: `DealDamage(9d10,Necrotic,Magical)` | Learned via class level or granted by equipment |
| **Target_InflictWounds_8**<br>*Cantrip* | `Target_InflictWounds_8` | **Cantrip** () | Mechanics: `DealDamage(10d10,Necrotic,Magical)` | Learned via class level or granted by equipment |
| **Target_InflictWounds_9**<br>*Cantrip* | `Target_InflictWounds_9` | **Cantrip** () | Mechanics: `DealDamage(11d10,Necrotic,Magical)` | Learned via class level or granted by equipment |
| **Target_Invisibility_7**<br>*Cantrip* | `Target_Invisibility_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Invisibility_8**<br>*Cantrip* | `Target_Invisibility_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Invisibility_9**<br>*Cantrip* | `Target_Invisibility_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Invisibility_7_AI**<br>*Cantrip* | `Target_Invisibility_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Invisibility_8_AI**<br>*Cantrip* | `Target_Invisibility_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Invisibility_9_AI**<br>*Cantrip* | `Target_Invisibility_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Longstrider_7**<br>*Cantrip* | `Target_Longstrider_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Longstrider_8**<br>*Cantrip* | `Target_Longstrider_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Longstrider_9**<br>*Cantrip* | `Target_Longstrider_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Longstrider_7_AI**<br>*Cantrip* | `Target_Longstrider_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Longstrider_8_AI**<br>*Cantrip* | `Target_Longstrider_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Longstrider_9_AI**<br>*Cantrip* | `Target_Longstrider_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimalFriendship_7**<br>*Cantrip* | `Target_AnimalFriendship_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimalFriendship_8**<br>*Cantrip* | `Target_AnimalFriendship_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimalFriendship_9**<br>*Cantrip* | `Target_AnimalFriendship_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimalFriendship_7_AI**<br>*Cantrip* | `Target_AnimalFriendship_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimalFriendship_8_AI**<br>*Cantrip* | `Target_AnimalFriendship_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimalFriendship_9_AI**<br>*Cantrip* | `Target_AnimalFriendship_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_7**<br>*Cantrip* | `Target_Bane_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_8**<br>*Cantrip* | `Target_Bane_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_9**<br>*Cantrip* | `Target_Bane_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_7_AI**<br>*Cantrip* | `Target_Bane_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_8_AI**<br>*Cantrip* | `Target_Bane_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_9_AI**<br>*Cantrip* | `Target_Bane_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_ThiefOfFiveFates_7**<br>*Cantrip* | `Target_Bane_ThiefOfFiveFates_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_ThiefOfFiveFates_8**<br>*Cantrip* | `Target_Bane_ThiefOfFiveFates_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_ThiefOfFiveFates_9**<br>*Cantrip* | `Target_Bane_ThiefOfFiveFates_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_ThiefOfFiveFates_7_AI**<br>*Cantrip* | `Target_Bane_ThiefOfFiveFates_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_ThiefOfFiveFates_8_AI**<br>*Cantrip* | `Target_Bane_ThiefOfFiveFates_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bane_ThiefOfFiveFates_9_AI**<br>*Cantrip* | `Target_Bane_ThiefOfFiveFates_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bless_7**<br>*Cantrip* | `Target_Bless_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bless_8**<br>*Cantrip* | `Target_Bless_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bless_9**<br>*Cantrip* | `Target_Bless_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bless_7_AI**<br>*Cantrip* | `Target_Bless_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bless_8_AI**<br>*Cantrip* | `Target_Bless_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Bless_9_AI**<br>*Cantrip* | `Target_Bless_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Blindness_7**<br>*Cantrip* | `Target_Blindness_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Blindness_8**<br>*Cantrip* | `Target_Blindness_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Blindness_9**<br>*Cantrip* | `Target_Blindness_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Blindness_7_AI**<br>*Cantrip* | `Target_Blindness_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Blindness_8_AI**<br>*Cantrip* | `Target_Blindness_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Blindness_9_AI**<br>*Cantrip* | `Target_Blindness_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CharmPerson_7**<br>*Cantrip* | `Target_CharmPerson_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CharmPerson_8**<br>*Cantrip* | `Target_CharmPerson_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CharmPerson_9**<br>*Cantrip* | `Target_CharmPerson_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CharmPerson_7_AI**<br>*Cantrip* | `Target_CharmPerson_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CharmPerson_8_AI**<br>*Cantrip* | `Target_CharmPerson_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CharmPerson_9_AI**<br>*Cantrip* | `Target_CharmPerson_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DissonantWhispers_7**<br>*Cantrip* | `Target_DissonantWhispers_7` | **Cantrip** () | Mechanics: `DealDamage(9d6,Psychic,Magical);ApplyStatus(FRIGHTENED,100,2)` | Learned via class level or granted by equipment |
| **Target_DissonantWhispers_8**<br>*Cantrip* | `Target_DissonantWhispers_8` | **Cantrip** () | Mechanics: `DealDamage(10d6,Psychic,Magical);ApplyStatus(FRIGHTENED,100,2)` | Learned via class level or granted by equipment |
| **Target_DissonantWhispers_9**<br>*Cantrip* | `Target_DissonantWhispers_9` | **Cantrip** () | Mechanics: `DealDamage(11d6,Psychic,Magical);ApplyStatus(FRIGHTENED,100,2)` | Learned via class level or granted by equipment |
| **Target_FlamingSphere_Ram_7**<br>*Cantrip* | `Target_FlamingSphere_Ram_7` | **Cantrip** () | Mechanics: `DealDamage(7d6,Fire)` | Learned via class level or granted by equipment |
| **Target_FlamingSphere_Ram_8**<br>*Cantrip* | `Target_FlamingSphere_Ram_8` | **Cantrip** () | Mechanics: `DealDamage(8d6,Fire)` | Learned via class level or granted by equipment |
| **Target_FlamingSphere_Ram_9**<br>*Cantrip* | `Target_FlamingSphere_Ram_9` | **Cantrip** () | Mechanics: `DealDamage(9d6,Fire)` | Learned via class level or granted by equipment |
| **Target_HealingWord_7**<br>*Cantrip* | `Target_HealingWord_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HealingWord_8**<br>*Cantrip* | `Target_HealingWord_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HealingWord_9**<br>*Cantrip* | `Target_HealingWord_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HeatMetal_7**<br>*Cantrip* | `Target_HeatMetal_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HeatMetal_8**<br>*Cantrip* | `Target_HeatMetal_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HeatMetal_9**<br>*Cantrip* | `Target_HeatMetal_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HeatMetal_Reapply_7**<br>*Cantrip* | `Target_HeatMetal_Reapply_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HeatMetal_Reapply_8**<br>*Cantrip* | `Target_HeatMetal_Reapply_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HeatMetal_Reapply_9**<br>*Cantrip* | `Target_HeatMetal_Reapply_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HellishRebuke_7**<br>*Cantrip* | `Target_HellishRebuke_7` | **Cantrip** () | Mechanics: `IF(not HasEvasion()):DealDamage(8d10,Fire,Magical);IF(HasEvasion()):DealDamage(8d10/2,Fire,Magical)` | Learned via class level or granted by equipment |
| **Target_HellishRebuke_8**<br>*Cantrip* | `Target_HellishRebuke_8` | **Cantrip** () | Mechanics: `IF(not HasEvasion()):DealDamage(9d10,Fire,Magical);IF(HasEvasion()):DealDamage(9d10/2,Fire,Magical)` | Learned via class level or granted by equipment |
| **Target_HellishRebuke_9**<br>*Cantrip* | `Target_HellishRebuke_9` | **Cantrip** () | Mechanics: `IF(not HasEvasion()):DealDamage(10d10,Fire,Magical);IF(HasEvasion()):DealDamage(10d10/2,Fire,Magical)` | Learned via class level or granted by equipment |
| **Target_HoldPerson_7**<br>*Cantrip* | `Target_HoldPerson_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldPerson_8**<br>*Cantrip* | `Target_HoldPerson_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldPerson_9**<br>*Cantrip* | `Target_HoldPerson_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldPerson_7_AI**<br>*Cantrip* | `Target_HoldPerson_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldPerson_8_AI**<br>*Cantrip* | `Target_HoldPerson_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldPerson_9_AI**<br>*Cantrip* | `Target_HoldPerson_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FlamingSphere_7**<br>*Cantrip* | `Target_FlamingSphere_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FlamingSphere_8**<br>*Cantrip* | `Target_FlamingSphere_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FlamingSphere_9**<br>*Cantrip* | `Target_FlamingSphere_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Moonbeam_7**<br>*Cantrip* | `Target_Moonbeam_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Moonbeam_8**<br>*Cantrip* | `Target_Moonbeam_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Moonbeam_9**<br>*Cantrip* | `Target_Moonbeam_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Moonbeam_Move_7**<br>*Cantrip* | `Target_Moonbeam_Move_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Moonbeam_Move_8**<br>*Cantrip* | `Target_Moonbeam_Move_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Moonbeam_Move_9**<br>*Cantrip* | `Target_Moonbeam_Move_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CloudOfDaggers_4**<br>*Cantrip* | `Target_CloudOfDaggers_4` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CloudOfDaggers_7**<br>*Cantrip* | `Target_CloudOfDaggers_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CloudOfDaggers_8**<br>*Cantrip* | `Target_CloudOfDaggers_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CloudOfDaggers_9**<br>*Cantrip* | `Target_CloudOfDaggers_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CreateWater_7**<br>*Cantrip* | `Target_CreateWater_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CreateWater_8**<br>*Cantrip* | `Target_CreateWater_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CreateWater_9**<br>*Cantrip* | `Target_CreateWater_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DestroyWater_7**<br>*Cantrip* | `Target_DestroyWater_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DestroyWater_8**<br>*Cantrip* | `Target_DestroyWater_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DestroyWater_9**<br>*Cantrip* | `Target_DestroyWater_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FogCloud_7**<br>*Cantrip* | `Target_FogCloud_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FogCloud_8**<br>*Cantrip* | `Target_FogCloud_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FogCloud_9**<br>*Cantrip* | `Target_FogCloud_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Shatter_7**<br>*Cantrip* | `Target_Shatter_7` | **Cantrip** () | Mechanics: `DealDamage(8d8,Thunder,Magical)` | Learned via class level or granted by equipment |
| **Target_Shatter_8**<br>*Cantrip* | `Target_Shatter_8` | **Cantrip** () | Mechanics: `DealDamage(9d8,Thunder,Magical)` | Learned via class level or granted by equipment |
| **Target_Shatter_9**<br>*Cantrip* | `Target_Shatter_9` | **Cantrip** () | Mechanics: `DealDamage(10d8,Thunder,Magical)` | Learned via class level or granted by equipment |
| **Target_Sleep_7**<br>*Cantrip* | `Target_Sleep_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Sleep_8**<br>*Cantrip* | `Target_Sleep_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Sleep_9**<br>*Cantrip* | `Target_Sleep_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Sleep_7_AI**<br>*Cantrip* | `Target_Sleep_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Sleep_8_AI**<br>*Cantrip* | `Target_Sleep_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Sleep_9_AI**<br>*Cantrip* | `Target_Sleep_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_MistyStep_7**<br>*Cantrip* | `Target_MistyStep_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_MistyStep_8**<br>*Cantrip* | `Target_MistyStep_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_MistyStep_9**<br>*Cantrip* | `Target_MistyStep_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Darkness_7**<br>*Cantrip* | `Target_Darkness_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Darkness_8**<br>*Cantrip* | `Target_Darkness_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Darkness_9**<br>*Cantrip* | `Target_Darkness_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_VampiricTouch_7**<br>*Cantrip* | `Target_VampiricTouch_7` | **Cantrip** () | Mechanics: `DealDamage(7d6,Necrotic,Magical); RegainHitPoints(SELF,(DamageDone)/2)` | Learned via class level or granted by equipment |
| **Target_VampiricTouch_8**<br>*Cantrip* | `Target_VampiricTouch_8` | **Cantrip** () | Mechanics: `DealDamage(8d6,Necrotic,Magical); RegainHitPoints(SELF,(DamageDone)/2)` | Learned via class level or granted by equipment |
| **Target_VampiricTouch_9**<br>*Cantrip* | `Target_VampiricTouch_9` | **Cantrip** () | Mechanics: `DealDamage(9d6,Necrotic,Magical); RegainHitPoints(SELF,(DamageDone)/2)` | Learned via class level or granted by equipment |
| **Target_VampiricTouch_Free_7**<br>*Cantrip* | `Target_VampiricTouch_Free_7` | **Cantrip** () | Mechanics: `DealDamage(7d6,Necrotic,Magical); RegainHitPoints(SELF,(DamageDone)/2)` | Learned via class level or granted by equipment |
| **Target_VampiricTouch_Free_8**<br>*Cantrip* | `Target_VampiricTouch_Free_8` | **Cantrip** () | Mechanics: `DealDamage(8d6,Necrotic,Magical); RegainHitPoints(SELF,(DamageDone)/2)` | Learned via class level or granted by equipment |
| **Target_VampiricTouch_Free_9**<br>*Cantrip* | `Target_VampiricTouch_Free_9` | **Cantrip** () | Mechanics: `DealDamage(9d6,Necrotic,Magical); RegainHitPoints(SELF,(DamageDone)/2)` | Learned via class level or granted by equipment |
| **Target_PhantasmalForce_7**<br>*Cantrip* | `Target_PhantasmalForce_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PhantasmalForce_8**<br>*Cantrip* | `Target_PhantasmalForce_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PhantasmalForce_9**<br>*Cantrip* | `Target_PhantasmalForce_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Darkvision_7**<br>*Cantrip* | `Target_Darkvision_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Darkvision_8**<br>*Cantrip* | `Target_Darkvision_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Darkvision_9**<br>*Cantrip* | `Target_Darkvision_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CrownOfMadness_7**<br>*Cantrip* | `Target_CrownOfMadness_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CrownOfMadness_8**<br>*Cantrip* | `Target_CrownOfMadness_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CrownOfMadness_9**<br>*Cantrip* | `Target_CrownOfMadness_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Web_7**<br>*Cantrip* | `Target_Web_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Web_8**<br>*Cantrip* | `Target_Web_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Web_9**<br>*Cantrip* | `Target_Web_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_MageArmor_7**<br>*Cantrip* | `Target_MageArmor_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_MageArmor_8**<br>*Cantrip* | `Target_MageArmor_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_MageArmor_9**<br>*Cantrip* | `Target_MageArmor_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Jump_7**<br>*Cantrip* | `Target_Jump_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Jump_8**<br>*Cantrip* | `Target_Jump_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Jump_9**<br>*Cantrip* | `Target_Jump_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEvilAndGood_7**<br>*Cantrip* | `Target_ProtectionFromEvilAndGood_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEvilAndGood_8**<br>*Cantrip* | `Target_ProtectionFromEvilAndGood_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEvilAndGood_9**<br>*Cantrip* | `Target_ProtectionFromEvilAndGood_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Grease_7**<br>*Cantrip* | `Target_Grease_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Grease_8**<br>*Cantrip* | `Target_Grease_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Grease_9**<br>*Cantrip* | `Target_Grease_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HideousLaughter_7**<br>*Cantrip* | `Target_HideousLaughter_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HideousLaughter_8**<br>*Cantrip* | `Target_HideousLaughter_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HideousLaughter_9**<br>*Cantrip* | `Target_HideousLaughter_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_MagicWeapon_7**<br>*Cantrip* | `Target_MagicWeapon_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_MagicWeapon_8**<br>*Cantrip* | `Target_MagicWeapon_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_MagicWeapon_9**<br>*Cantrip* | `Target_MagicWeapon_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Counterspell_7**<br>*Cantrip* | `Target_Counterspell_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Counterspell_8**<br>*Cantrip* | `Target_Counterspell_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Counterspell_9**<br>*Cantrip* | `Target_Counterspell_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Barkskin_7**<br>*Cantrip* | `Target_Barkskin_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Barkskin_8**<br>*Cantrip* | `Target_Barkskin_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Barkskin_9**<br>*Cantrip* | `Target_Barkskin_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Entangle_7**<br>*Cantrip* | `Target_Entangle_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Entangle_8**<br>*Cantrip* | `Target_Entangle_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Entangle_9**<br>*Cantrip* | `Target_Entangle_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FaerieFire_7**<br>*Cantrip* | `Target_FaerieFire_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FaerieFire_8**<br>*Cantrip* | `Target_FaerieFire_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FaerieFire_9**<br>*Cantrip* | `Target_FaerieFire_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_LesserRestoration_7**<br>*Cantrip* | `Target_LesserRestoration_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_LesserRestoration_8**<br>*Cantrip* | `Target_LesserRestoration_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_LesserRestoration_9**<br>*Cantrip* | `Target_LesserRestoration_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromPoison_7**<br>*Cantrip* | `Target_ProtectionFromPoison_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromPoison_8**<br>*Cantrip* | `Target_ProtectionFromPoison_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromPoison_9**<br>*Cantrip* | `Target_ProtectionFromPoison_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpikeGrowth_7**<br>*Cantrip* | `Target_SpikeGrowth_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpikeGrowth_8**<br>*Cantrip* | `Target_SpikeGrowth_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpikeGrowth_9**<br>*Cantrip* | `Target_SpikeGrowth_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ArcaneLock_7**<br>*Cantrip* | `Target_ArcaneLock_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ArcaneLock_8**<br>*Cantrip* | `Target_ArcaneLock_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ArcaneLock_9**<br>*Cantrip* | `Target_ArcaneLock_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Confusion_7**<br>*Cantrip* | `Target_Confusion_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Confusion_8**<br>*Cantrip* | `Target_Confusion_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Confusion_9**<br>*Cantrip* | `Target_Confusion_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Banishment_7**<br>*Cantrip* | `Target_Banishment_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Banishment_8**<br>*Cantrip* | `Target_Banishment_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Banishment_9**<br>*Cantrip* | `Target_Banishment_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Banishment_7_AI**<br>*Cantrip* | `Target_Banishment_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Banishment_8_AI**<br>*Cantrip* | `Target_Banishment_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Banishment_9_AI**<br>*Cantrip* | `Target_Banishment_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Blight_7**<br>*Cantrip* | `Target_Blight_7` | **Cantrip** () | Mechanics: `IF(not Tagged('PLANT')):DealDamage(11d8,Necrotic,Magical);IF(Tagged('PLANT')):DealDamage(88,Necrotic,Magical)` | Learned via class level or granted by equipment |
| **Target_Blight_8**<br>*Cantrip* | `Target_Blight_8` | **Cantrip** () | Mechanics: `IF(not Tagged('PLANT')):DealDamage(12d8,Necrotic,Magical);IF(Tagged('PLANT')):DealDamage(96,Necrotic,Magical)` | Learned via class level or granted by equipment |
| **Target_Blight_9**<br>*Cantrip* | `Target_Blight_9` | **Cantrip** () | Mechanics: `IF(not Tagged('PLANT')):DealDamage(13d8,Necrotic,Magical);IF(Tagged('PLANT')):DealDamage(104,Necrotic,Magical)` | Learned via class level or granted by equipment |
| **Target_BlackTentacles_7**<br>*Cantrip* | `Target_BlackTentacles_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BlackTentacles_8**<br>*Cantrip* | `Target_BlackTentacles_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BlackTentacles_9**<br>*Cantrip* | `Target_BlackTentacles_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldMonster_7**<br>*Cantrip* | `Target_HoldMonster_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldMonster_8**<br>*Cantrip* | `Target_HoldMonster_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldMonster_9**<br>*Cantrip* | `Target_HoldMonster_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldMonster_7_AI**<br>*Cantrip* | `Target_HoldMonster_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldMonster_8_AI**<br>*Cantrip* | `Target_HoldMonster_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HoldMonster_9_AI**<br>*Cantrip* | `Target_HoldMonster_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Seeming_7**<br>*Cantrip* | `Target_Seeming_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Seeming_8**<br>*Cantrip* | `Target_Seeming_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Seeming_9**<br>*Cantrip* | `Target_Seeming_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Seeming_7_AI**<br>*Cantrip* | `Target_Seeming_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Seeming_8_AI**<br>*Cantrip* | `Target_Seeming_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Seeming_9_AI**<br>*Cantrip* | `Target_Seeming_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarBinding_7**<br>*Cantrip* | `Target_PlanarBinding_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarBinding_8**<br>*Cantrip* | `Target_PlanarBinding_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarBinding_9**<br>*Cantrip* | `Target_PlanarBinding_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DominatePerson_7**<br>*Cantrip* | `Target_DominatePerson_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DominatePerson_8**<br>*Cantrip* | `Target_DominatePerson_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DominatePerson_9**<br>*Cantrip* | `Target_DominatePerson_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Cloudkill_7**<br>*Cantrip* | `Target_Cloudkill_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Cloudkill_8**<br>*Cantrip* | `Target_Cloudkill_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Cloudkill_9**<br>*Cantrip* | `Target_Cloudkill_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Cloudkill_Recast_7**<br>*Cantrip* | `Target_Cloudkill_Recast_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Cloudkill_Recast_8**<br>*Cantrip* | `Target_Cloudkill_Recast_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Cloudkill_Recast_9**<br>*Cantrip* | `Target_Cloudkill_Recast_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CircleOfDeath_7**<br>*Cantrip* | `Target_CircleOfDeath_7` | **Cantrip** () | Mechanics: `DealDamage(10d6,Necrotic,Magical)` | Learned via class level or granted by equipment |
| **Target_CircleOfDeath_8**<br>*Cantrip* | `Target_CircleOfDeath_8` | **Cantrip** () | Mechanics: `DealDamage(12d6,Necrotic,Magical)` | Learned via class level or granted by equipment |
| **Target_CircleOfDeath_9**<br>*Cantrip* | `Target_CircleOfDeath_9` | **Cantrip** () | Mechanics: `DealDamage(14d6,Necrotic,Magical)` | Learned via class level or granted by equipment |
| **Target_GlobeOfInvulnerability_7**<br>*Cantrip* | `Target_GlobeOfInvulnerability_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlobeOfInvulnerability_8**<br>*Cantrip* | `Target_GlobeOfInvulnerability_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlobeOfInvulnerability_9**<br>*Cantrip* | `Target_GlobeOfInvulnerability_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_IrresistibleDance_7**<br>*Cantrip* | `Target_IrresistibleDance_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_IrresistibleDance_8**<br>*Cantrip* | `Target_IrresistibleDance_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_IrresistibleDance_9**<br>*Cantrip* | `Target_IrresistibleDance_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FleshToStone_7**<br>*Cantrip* | `Target_FleshToStone_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FleshToStone_8**<br>*Cantrip* | `Target_FleshToStone_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FleshToStone_9**<br>*Cantrip* | `Target_FleshToStone_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CreateUndead_7**<br>*Cantrip* | `Target_CreateUndead_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CreateUndead_8**<br>*Cantrip* | `Target_CreateUndead_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CreateUndead_9**<br>*Cantrip* | `Target_CreateUndead_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Reduce_7**<br>*Cantrip* | `Target_Reduce_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Reduce_8**<br>*Cantrip* | `Target_Reduce_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Reduce_9**<br>*Cantrip* | `Target_Reduce_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Enlarge_7**<br>*Cantrip* | `Target_Enlarge_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Enlarge_8**<br>*Cantrip* | `Target_Enlarge_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Enlarge_9**<br>*Cantrip* | `Target_Enlarge_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Knock_7**<br>*Cantrip* | `Target_Knock_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Knock_8**<br>*Cantrip* | `Target_Knock_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Knock_9**<br>*Cantrip* | `Target_Knock_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_StinkingCloud_7**<br>*Cantrip* | `Target_StinkingCloud_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_StinkingCloud_8**<br>*Cantrip* | `Target_StinkingCloud_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_StinkingCloud_9**<br>*Cantrip* | `Target_StinkingCloud_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Slow_7**<br>*Cantrip* | `Target_Slow_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Slow_8**<br>*Cantrip* | `Target_Slow_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Slow_9**<br>*Cantrip* | `Target_Slow_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Slow_7_AI**<br>*Cantrip* | `Target_Slow_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Slow_8_AI**<br>*Cantrip* | `Target_Slow_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Slow_9_AI**<br>*Cantrip* | `Target_Slow_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_IceStorm_7**<br>*Cantrip* | `Target_IceStorm_7` | **Cantrip** () | Mechanics: `DealDamage(5d8,Bludgeoning,Magical);DealDamage(4d6,Cold,Magical)` | Learned via class level or granted by equipment |
| **Target_IceStorm_8**<br>*Cantrip* | `Target_IceStorm_8` | **Cantrip** () | Mechanics: `DealDamage(6d8,Bludgeoning,Magical);DealDamage(4d6,Cold,Magical)` | Learned via class level or granted by equipment |
| **Target_IceStorm_9**<br>*Cantrip* | `Target_IceStorm_9` | **Cantrip** () | Mechanics: `DealDamage(7d8,Bludgeoning,Magical);DealDamage(4d6,Cold,Magical)` | Learned via class level or granted by equipment |
| **Target_Stoneskin_7**<br>*Cantrip* | `Target_Stoneskin_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Stoneskin_8**<br>*Cantrip* | `Target_Stoneskin_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Stoneskin_9**<br>*Cantrip* | `Target_Stoneskin_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ResilientSphere_7**<br>*Cantrip* | `Target_ResilientSphere_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ResilientSphere_8**<br>*Cantrip* | `Target_ResilientSphere_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ResilientSphere_9**<br>*Cantrip* | `Target_ResilientSphere_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Invisibility_Greater_7**<br>*Cantrip* | `Target_Invisibility_Greater_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Invisibility_Greater_8**<br>*Cantrip* | `Target_Invisibility_Greater_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Invisibility_Greater_9**<br>*Cantrip* | `Target_Invisibility_Greater_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Polymorph_7**<br>*Cantrip* | `Target_Polymorph_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Polymorph_8**<br>*Cantrip* | `Target_Polymorph_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Polymorph_9**<br>*Cantrip* | `Target_Polymorph_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PhantasmalKiller_7**<br>*Cantrip* | `Target_PhantasmalKiller_7` | **Cantrip** () | Mechanics: `ApplyStatus(PHANTASMAL_KILLER_7,100,10)` | Learned via class level or granted by equipment |
| **Target_PhantasmalKiller_8**<br>*Cantrip* | `Target_PhantasmalKiller_8` | **Cantrip** () | Mechanics: `ApplyStatus(PHANTASMAL_KILLER_8,100,10)` | Learned via class level or granted by equipment |
| **Target_PhantasmalKiller_9**<br>*Cantrip* | `Target_PhantasmalKiller_9` | **Cantrip** () | Mechanics: `ApplyStatus(PHANTASMAL_KILLER_9,100,10)` | Learned via class level or granted by equipment |
| **Target_FeignDeath_7**<br>*Cantrip* | `Target_FeignDeath_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FeignDeath_8**<br>*Cantrip* | `Target_FeignDeath_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FeignDeath_9**<br>*Cantrip* | `Target_FeignDeath_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Haste_7**<br>*Cantrip* | `Target_Haste_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Haste_8**<br>*Cantrip* | `Target_Haste_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Haste_9**<br>*Cantrip* | `Target_Haste_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GaseousForm_7**<br>*Cantrip* | `Target_GaseousForm_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GaseousForm_8**<br>*Cantrip* | `Target_GaseousForm_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GaseousForm_9**<br>*Cantrip* | `Target_GaseousForm_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SleetStorm_7**<br>*Cantrip* | `Target_SleetStorm_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SleetStorm_8**<br>*Cantrip* | `Target_SleetStorm_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SleetStorm_9**<br>*Cantrip* | `Target_SleetStorm_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HypnoticPattern_7**<br>*Cantrip* | `Target_HypnoticPattern_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HypnoticPattern_8**<br>*Cantrip* | `Target_HypnoticPattern_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HypnoticPattern_9**<br>*Cantrip* | `Target_HypnoticPattern_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CallLightning_7**<br>*Cantrip* | `Target_CallLightning_7` | **Cantrip** () | Mechanics: `DealDamage(7d10,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Target_CallLightning_8**<br>*Cantrip* | `Target_CallLightning_8` | **Cantrip** () | Mechanics: `DealDamage(8d10,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Target_CallLightning_9**<br>*Cantrip* | `Target_CallLightning_9` | **Cantrip** () | Mechanics: `DealDamage(9d10,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Target_CallLightning_LightningBolt_7**<br>*Cantrip* | `Target_CallLightning_LightningBolt_7` | **Cantrip** () | Mechanics: `DealDamage(7d10,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Target_CallLightning_LightningBolt_8**<br>*Cantrip* | `Target_CallLightning_LightningBolt_8` | **Cantrip** () | Mechanics: `DealDamage(8d10,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Target_CallLightning_LightningBolt_9**<br>*Cantrip* | `Target_CallLightning_LightningBolt_9` | **Cantrip** () | Mechanics: `DealDamage(9d10,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Target_RemoveCurse_7**<br>*Cantrip* | `Target_RemoveCurse_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_RemoveCurse_8**<br>*Cantrip* | `Target_RemoveCurse_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_RemoveCurse_9**<br>*Cantrip* | `Target_RemoveCurse_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_7**<br>*Cantrip* | `Target_BestowCurse_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_8**<br>*Cantrip* | `Target_BestowCurse_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_9**<br>*Cantrip* | `Target_BestowCurse_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Strength_7**<br>*Cantrip* | `Target_BestowCurse_Ability_Strength_7` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_STRENGTH,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Strength_8**<br>*Cantrip* | `Target_BestowCurse_Ability_Strength_8` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_STRENGTH,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Strength_9**<br>*Cantrip* | `Target_BestowCurse_Ability_Strength_9` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_STRENGTH,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Dexterity_7**<br>*Cantrip* | `Target_BestowCurse_Ability_Dexterity_7` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_DEXTERITY,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Dexterity_8**<br>*Cantrip* | `Target_BestowCurse_Ability_Dexterity_8` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_DEXTERITY,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Dexterity_9**<br>*Cantrip* | `Target_BestowCurse_Ability_Dexterity_9` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_DEXTERITY,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Constitution_7**<br>*Cantrip* | `Target_BestowCurse_Ability_Constitution_7` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_CONSTITUTION,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Constitution_8**<br>*Cantrip* | `Target_BestowCurse_Ability_Constitution_8` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_CONSTITUTION,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Constitution_9**<br>*Cantrip* | `Target_BestowCurse_Ability_Constitution_9` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_CONSTITUTION,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Intelligence_7**<br>*Cantrip* | `Target_BestowCurse_Ability_Intelligence_7` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_INTELLIGENCE,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Intelligence_8**<br>*Cantrip* | `Target_BestowCurse_Ability_Intelligence_8` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_INTELLIGENCE,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Intelligence_9**<br>*Cantrip* | `Target_BestowCurse_Ability_Intelligence_9` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_INTELLIGENCE,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Wisdom_7**<br>*Cantrip* | `Target_BestowCurse_Ability_Wisdom_7` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_WISDOM,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Wisdom_8**<br>*Cantrip* | `Target_BestowCurse_Ability_Wisdom_8` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_WISDOM,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Wisdom_9**<br>*Cantrip* | `Target_BestowCurse_Ability_Wisdom_9` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_WISDOM,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Charisma_7**<br>*Cantrip* | `Target_BestowCurse_Ability_Charisma_7` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_CHARISMA,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Charisma_8**<br>*Cantrip* | `Target_BestowCurse_Ability_Charisma_8` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_CHARISMA,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Charisma_9**<br>*Cantrip* | `Target_BestowCurse_Ability_Charisma_9` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ABILITY_CHARISMA,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Attack_7**<br>*Cantrip* | `Target_BestowCurse_Attack_7` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ATTACK,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Attack_8**<br>*Cantrip* | `Target_BestowCurse_Attack_8` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ATTACK,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_Attack_9**<br>*Cantrip* | `Target_BestowCurse_Attack_9` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_ATTACK,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_ExtraDamage_7**<br>*Cantrip* | `Target_BestowCurse_ExtraDamage_7` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_EXTRA_DAMAGE, 100, 100);ApplyStatus(SELF, CURSE_EXTRA_DAMAGE_OWNER, 100, 100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_ExtraDamage_8**<br>*Cantrip* | `Target_BestowCurse_ExtraDamage_8` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_EXTRA_DAMAGE, 100, 100);ApplyStatus(SELF, CURSE_EXTRA_DAMAGE_OWNER, 100, 100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_ExtraDamage_9**<br>*Cantrip* | `Target_BestowCurse_ExtraDamage_9` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_EXTRA_DAMAGE, 100, 100);ApplyStatus(SELF, CURSE_EXTRA_DAMAGE_OWNER, 100, 100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_SkipTurn_7**<br>*Cantrip* | `Target_BestowCurse_SkipTurn_7` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_SKIP_TURN,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_SkipTurn_8**<br>*Cantrip* | `Target_BestowCurse_SkipTurn_8` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_SKIP_TURN,100,100)` | Learned via class level or granted by equipment |
| **Target_BestowCurse_SkipTurn_9**<br>*Cantrip* | `Target_BestowCurse_SkipTurn_9` | **Cantrip** () | Mechanics: `ApplyStatus(CURSE_SKIP_TURN,100,100)` | Learned via class level or granted by equipment |
| **Target_AnimateDead_Ghoul_7**<br>*Level 7 Spell* | `Target_AnimateDead_Ghoul_7` | **Level 7 Spell** () | Create 5 ghouls that specialise in melee combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Ghoul_8**<br>*Level 8 Spell* | `Target_AnimateDead_Ghoul_8` | **Level 8 Spell** () | Create 7 ghouls that specialise in melee combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Ghoul_9**<br>*Level 9 Spell* | `Target_AnimateDead_Ghoul_9` | **Level 9 Spell** () | Create 9 ghouls that specialise in melee combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Ghoul_7_AI**<br>*Cantrip* | `Target_AnimateDead_Ghoul_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Ghoul_8_AI**<br>*Cantrip* | `Target_AnimateDead_Ghoul_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Ghoul_9_AI**<br>*Cantrip* | `Target_AnimateDead_Ghoul_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_FlyingGhoul_7**<br>*Level 7 Spell* | `Target_AnimateDead_FlyingGhoul_7` | **Level 7 Spell** () | Create 5 flying ghouls that specialise in ranged combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_FlyingGhoul_8**<br>*Level 8 Spell* | `Target_AnimateDead_FlyingGhoul_8` | **Level 8 Spell** () | Create 7 flying ghouls that specialise in ranged combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_FlyingGhoul_9**<br>*Level 9 Spell* | `Target_AnimateDead_FlyingGhoul_9` | **Level 9 Spell** () | Create 9 flying ghouls that specialise in ranged combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_FlyingGhoul_7_AI**<br>*Cantrip* | `Target_AnimateDead_FlyingGhoul_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_FlyingGhoul_8_AI**<br>*Cantrip* | `Target_AnimateDead_FlyingGhoul_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_FlyingGhoul_9_AI**<br>*Cantrip* | `Target_AnimateDead_FlyingGhoul_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Zombie_5**<br>*Level 5 Spell* | `Target_AnimateDead_Zombie_5` | **Level 5 Spell** () | Create 5 zombies that specialise in melee combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Zombie_6**<br>*Level 6 Spell* | `Target_AnimateDead_Zombie_6` | **Level 6 Spell** () | Create 7 zombies that specialise in melee combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Zombie_7**<br>*Level 7 Spell* | `Target_AnimateDead_Zombie_7` | **Level 7 Spell** () | Create 9 zombies that specialise in melee combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Zombie_8**<br>*Level 8 Spell* | `Target_AnimateDead_Zombie_8` | **Level 8 Spell** () | Create 11 zombies that specialise in melee combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Zombie_9**<br>*Level 9 Spell* | `Target_AnimateDead_Zombie_9` | **Level 9 Spell** () | Create 13 zombies that specialise in melee combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Zombie_5_AI**<br>*Cantrip* | `Target_AnimateDead_Zombie_5_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Zombie_6_AI**<br>*Cantrip* | `Target_AnimateDead_Zombie_6_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Zombie_7_AI**<br>*Cantrip* | `Target_AnimateDead_Zombie_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Zombie_8_AI**<br>*Cantrip* | `Target_AnimateDead_Zombie_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Zombie_9_AI**<br>*Cantrip* | `Target_AnimateDead_Zombie_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Skeleton_5**<br>*Level 5 Spell* | `Target_AnimateDead_Skeleton_5` | **Level 5 Spell** () | Create 5 skeletons that specialise in ranged combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Skeleton_6**<br>*Level 6 Spell* | `Target_AnimateDead_Skeleton_6` | **Level 6 Spell** () | Create 7 skeletons that specialise in ranged combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Skeleton_7**<br>*Level 7 Spell* | `Target_AnimateDead_Skeleton_7` | **Level 7 Spell** () | Create 9 skeletons that specialise in ranged combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Skeleton_8**<br>*Level 8 Spell* | `Target_AnimateDead_Skeleton_8` | **Level 8 Spell** () | Create 11 skeletons that specialise in ranged combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Skeleton_9**<br>*Level 9 Spell* | `Target_AnimateDead_Skeleton_9` | **Level 9 Spell** () | Create 13 skeletons that specialise in ranged combat. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Skeleton_5_AI**<br>*Cantrip* | `Target_AnimateDead_Skeleton_5_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Skeleton_6_AI**<br>*Cantrip* | `Target_AnimateDead_Skeleton_6_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Skeleton_7_AI**<br>*Cantrip* | `Target_AnimateDead_Skeleton_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Skeleton_8_AI**<br>*Cantrip* | `Target_AnimateDead_Skeleton_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_AnimateDead_Skeleton_9_AI**<br>*Cantrip* | `Target_AnimateDead_Skeleton_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Eyebite_Asleep_7**<br>*Cantrip* | `Target_Eyebite_Asleep_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Eyebite_Asleep_8**<br>*Cantrip* | `Target_Eyebite_Asleep_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Eyebite_Asleep_9**<br>*Cantrip* | `Target_Eyebite_Asleep_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Eyebite_Panicked_7**<br>*Cantrip* | `Target_Eyebite_Panicked_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Eyebite_Panicked_8**<br>*Cantrip* | `Target_Eyebite_Panicked_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Eyebite_Panicked_9**<br>*Cantrip* | `Target_Eyebite_Panicked_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Eyebite_Sickened_7**<br>*Cantrip* | `Target_Eyebite_Sickened_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Eyebite_Sickened_8**<br>*Cantrip* | `Target_Eyebite_Sickened_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Eyebite_Sickened_9**<br>*Cantrip* | `Target_Eyebite_Sickened_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Cold_7**<br>*Cantrip* | `Target_ProtectionFromEnergy_Cold_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Cold_8**<br>*Cantrip* | `Target_ProtectionFromEnergy_Cold_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Cold_9**<br>*Cantrip* | `Target_ProtectionFromEnergy_Cold_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Fire_7**<br>*Cantrip* | `Target_ProtectionFromEnergy_Fire_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Fire_8**<br>*Cantrip* | `Target_ProtectionFromEnergy_Fire_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Fire_9**<br>*Cantrip* | `Target_ProtectionFromEnergy_Fire_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Lightning_7**<br>*Cantrip* | `Target_ProtectionFromEnergy_Lightning_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Lightning_8**<br>*Cantrip* | `Target_ProtectionFromEnergy_Lightning_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Lightning_9**<br>*Cantrip* | `Target_ProtectionFromEnergy_Lightning_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Thunder_7**<br>*Cantrip* | `Target_ProtectionFromEnergy_Thunder_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Thunder_8**<br>*Cantrip* | `Target_ProtectionFromEnergy_Thunder_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Thunder_9**<br>*Cantrip* | `Target_ProtectionFromEnergy_Thunder_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Acid_7**<br>*Cantrip* | `Target_ProtectionFromEnergy_Acid_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Acid_8**<br>*Cantrip* | `Target_ProtectionFromEnergy_Acid_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Acid_9**<br>*Cantrip* | `Target_ProtectionFromEnergy_Acid_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Acid_7**<br>*Cantrip* | `Target_GlyphOfWarding_Acid_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Acid_8**<br>*Cantrip* | `Target_GlyphOfWarding_Acid_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Acid_9**<br>*Cantrip* | `Target_GlyphOfWarding_Acid_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Cold_7**<br>*Cantrip* | `Target_GlyphOfWarding_Cold_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Cold_8**<br>*Cantrip* | `Target_GlyphOfWarding_Cold_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Cold_9**<br>*Cantrip* | `Target_GlyphOfWarding_Cold_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Fire_7**<br>*Cantrip* | `Target_GlyphOfWarding_Fire_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Fire_8**<br>*Cantrip* | `Target_GlyphOfWarding_Fire_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Fire_9**<br>*Cantrip* | `Target_GlyphOfWarding_Fire_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Lightning_7**<br>*Cantrip* | `Target_GlyphOfWarding_Lightning_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Lightning_8**<br>*Cantrip* | `Target_GlyphOfWarding_Lightning_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Lightning_9**<br>*Cantrip* | `Target_GlyphOfWarding_Lightning_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Thunder_7**<br>*Cantrip* | `Target_GlyphOfWarding_Thunder_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Thunder_8**<br>*Cantrip* | `Target_GlyphOfWarding_Thunder_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Thunder_9**<br>*Cantrip* | `Target_GlyphOfWarding_Thunder_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Detonation_7**<br>*Cantrip* | `Target_GlyphOfWarding_Detonation_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Detonation_8**<br>*Cantrip* | `Target_GlyphOfWarding_Detonation_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Detonation_9**<br>*Cantrip* | `Target_GlyphOfWarding_Detonation_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Sleep_7**<br>*Cantrip* | `Target_GlyphOfWarding_Sleep_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Sleep_8**<br>*Cantrip* | `Target_GlyphOfWarding_Sleep_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Sleep_9**<br>*Cantrip* | `Target_GlyphOfWarding_Sleep_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_Container_7**<br>*Cantrip* | `Target_ConjureElementals_Minor_Container_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_Container_8**<br>*Cantrip* | `Target_ConjureElementals_Minor_Container_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_Container_9**<br>*Cantrip* | `Target_ConjureElementals_Minor_Container_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_Azer_7**<br>*Level 7 Spell* | `Target_ConjureElementals_Minor_Azer_7` | **Level 7 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_Azer_8**<br>*Level 8 Spell* | `Target_ConjureElementals_Minor_Azer_8` | **Level 8 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_Azer_9**<br>*Level 9 Spell* | `Target_ConjureElementals_Minor_Azer_9` | **Level 9 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_IceMephit_7**<br>*Level 7 Spell* | `Target_ConjureElementals_Minor_IceMephit_7` | **Level 7 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_IceMephit_8**<br>*Level 8 Spell* | `Target_ConjureElementals_Minor_IceMephit_8` | **Level 8 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_IceMephit_9**<br>*Level 9 Spell* | `Target_ConjureElementals_Minor_IceMephit_9` | **Level 9 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_MudMephit_7**<br>*Level 7 Spell* | `Target_ConjureElementals_Minor_MudMephit_7` | **Level 7 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_MudMephit_8**<br>*Level 8 Spell* | `Target_ConjureElementals_Minor_MudMephit_8` | **Level 8 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureElementals_Minor_MudMephit_9**<br>*Level 9 Spell* | `Target_ConjureElementals_Minor_MudMephit_9` | **Level 9 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Fly_7**<br>*Cantrip* | `Target_Fly_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Fly_8**<br>*Cantrip* | `Target_Fly_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Fly_9**<br>*Cantrip* | `Target_Fly_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_7**<br>*Cantrip* | `Target_FindFamiliar_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_8**<br>*Cantrip* | `Target_FindFamiliar_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_9**<br>*Cantrip* | `Target_FindFamiliar_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Cat_7**<br>*Cantrip* | `Target_FindFamiliar_Cat_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Cat_8**<br>*Cantrip* | `Target_FindFamiliar_Cat_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Cat_9**<br>*Cantrip* | `Target_FindFamiliar_Cat_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Crab_7**<br>*Cantrip* | `Target_FindFamiliar_Crab_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Crab_8**<br>*Cantrip* | `Target_FindFamiliar_Crab_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Crab_9**<br>*Cantrip* | `Target_FindFamiliar_Crab_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Frog_7**<br>*Cantrip* | `Target_FindFamiliar_Frog_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Frog_8**<br>*Cantrip* | `Target_FindFamiliar_Frog_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Frog_9**<br>*Cantrip* | `Target_FindFamiliar_Frog_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Rat_7**<br>*Cantrip* | `Target_FindFamiliar_Rat_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Rat_8**<br>*Cantrip* | `Target_FindFamiliar_Rat_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Rat_9**<br>*Cantrip* | `Target_FindFamiliar_Rat_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Raven_7**<br>*Cantrip* | `Target_FindFamiliar_Raven_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Raven_8**<br>*Cantrip* | `Target_FindFamiliar_Raven_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Raven_9**<br>*Cantrip* | `Target_FindFamiliar_Raven_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Spider_7**<br>*Cantrip* | `Target_FindFamiliar_Spider_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Spider_8**<br>*Cantrip* | `Target_FindFamiliar_Spider_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FindFamiliar_Spider_9**<br>*Cantrip* | `Target_FindFamiliar_Spider_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FreezingSphere_7**<br>*Level 7 Spell* | `Target_FreezingSphere_7` | **Level 7 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FreezingSphere_8**<br>*Level 8 Spell* | `Target_FreezingSphere_8` | **Level 8 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FreezingSphere_9**<br>*Level 9 Spell* | `Target_FreezingSphere_9` | **Level 9 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FreezingSphere_Throw_7**<br>*Level 7 Spell* | `Target_FreezingSphere_Throw_7` | **Level 7 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FreezingSphere_Throw_8**<br>*Level 8 Spell* | `Target_FreezingSphere_Throw_8` | **Level 8 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FreezingSphere_Throw_9**<br>*Level 9 Spell* | `Target_FreezingSphere_Throw_9` | **Level 9 Spell** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Daylight_7**<br>*Cantrip* | `Target_Daylight_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Daylight_8**<br>*Cantrip* | `Target_Daylight_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Daylight_9**<br>*Cantrip* | `Target_Daylight_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Daylight_Container_7**<br>*Cantrip* | `Target_Daylight_Container_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Daylight_Container_8**<br>*Cantrip* | `Target_Daylight_Container_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Daylight_Container_9**<br>*Cantrip* | `Target_Daylight_Container_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Daylight_Enchantment_7**<br>*Cantrip* | `Target_Daylight_Enchantment_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Daylight_Enchantment_8**<br>*Cantrip* | `Target_Daylight_Enchantment_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Daylight_Enchantment_9**<br>*Cantrip* | `Target_Daylight_Enchantment_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DominateBeast_7**<br>*Cantrip* | `Target_DominateBeast_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DominateBeast_8**<br>*Cantrip* | `Target_DominateBeast_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DominateBeast_9**<br>*Cantrip* | `Target_DominateBeast_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_InsectPlague_7**<br>*Cantrip* | `Target_InsectPlague_7` | **Cantrip** () | Mechanics: `DealDamage(6d10,Piercing,Magical)` | Learned via class level or granted by equipment |
| **Target_InsectPlague_8**<br>*Cantrip* | `Target_InsectPlague_8` | **Cantrip** () | Mechanics: `DealDamage(7d10,Piercing,Magical)` | Learned via class level or granted by equipment |
| **Target_InsectPlague_9**<br>*Cantrip* | `Target_InsectPlague_9` | **Cantrip** () | Mechanics: `DealDamage(8d10,Piercing,Magical)` | Learned via class level or granted by equipment |
| **Target_Heal_7**<br>*Cantrip* | `Target_Heal_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Heal_8**<br>*Cantrip* | `Target_Heal_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Heal_9**<br>*Cantrip* | `Target_Heal_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GreaterRestoration_7**<br>*Cantrip* | `Target_GreaterRestoration_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GreaterRestoration_8**<br>*Cantrip* | `Target_GreaterRestoration_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GreaterRestoration_9**<br>*Cantrip* | `Target_GreaterRestoration_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureWoodlandBeings_7**<br>*Cantrip* | `Target_ConjureWoodlandBeings_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureWoodlandBeings_8**<br>*Cantrip* | `Target_ConjureWoodlandBeings_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ConjureWoodlandBeings_9**<br>*Cantrip* | `Target_ConjureWoodlandBeings_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GraspingVine_7**<br>*Cantrip* | `Target_GraspingVine_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GraspingVine_8**<br>*Cantrip* | `Target_GraspingVine_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GraspingVine_9**<br>*Cantrip* | `Target_GraspingVine_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlantGrowth_7**<br>*Cantrip* | `Target_PlantGrowth_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlantGrowth_8**<br>*Cantrip* | `Target_PlantGrowth_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlantGrowth_9**<br>*Cantrip* | `Target_PlantGrowth_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FreedomOfMovement_7**<br>*Cantrip* | `Target_FreedomOfMovement_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FreedomOfMovement_8**<br>*Cantrip* | `Target_FreedomOfMovement_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FreedomOfMovement_9**<br>*Cantrip* | `Target_FreedomOfMovement_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CureWounds_Mass_7**<br>*Cantrip* | `Target_CureWounds_Mass_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CureWounds_Mass_8**<br>*Cantrip* | `Target_CureWounds_Mass_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CureWounds_Mass_9**<br>*Cantrip* | `Target_CureWounds_Mass_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CureWounds_Mass_7_AI**<br>*Cantrip* | `Target_CureWounds_Mass_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CureWounds_Mass_8_AI**<br>*Cantrip* | `Target_CureWounds_Mass_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CureWounds_Mass_9_AI**<br>*Cantrip* | `Target_CureWounds_Mass_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_BlindingSickness_7**<br>*Cantrip* | `Target_Contagion_BlindingSickness_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_BlindingSickness_8**<br>*Cantrip* | `Target_Contagion_BlindingSickness_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_BlindingSickness_9**<br>*Cantrip* | `Target_Contagion_BlindingSickness_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_FilthFever_7**<br>*Cantrip* | `Target_Contagion_FilthFever_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_FilthFever_8**<br>*Cantrip* | `Target_Contagion_FilthFever_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_FilthFever_9**<br>*Cantrip* | `Target_Contagion_FilthFever_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_FleshRot_7**<br>*Cantrip* | `Target_Contagion_FleshRot_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_FleshRot_8**<br>*Cantrip* | `Target_Contagion_FleshRot_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_FleshRot_9**<br>*Cantrip* | `Target_Contagion_FleshRot_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_Mindfire_7**<br>*Cantrip* | `Target_Contagion_Mindfire_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_Mindfire_8**<br>*Cantrip* | `Target_Contagion_Mindfire_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_Mindfire_9**<br>*Cantrip* | `Target_Contagion_Mindfire_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_Seizure_7**<br>*Cantrip* | `Target_Contagion_Seizure_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_Seizure_8**<br>*Cantrip* | `Target_Contagion_Seizure_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_Seizure_9**<br>*Cantrip* | `Target_Contagion_Seizure_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_SlimyDoom_7**<br>*Cantrip* | `Target_Contagion_SlimyDoom_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_SlimyDoom_8**<br>*Cantrip* | `Target_Contagion_SlimyDoom_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Contagion_SlimyDoom_9**<br>*Cantrip* | `Target_Contagion_SlimyDoom_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DeathWard_7**<br>*Cantrip* | `Target_DeathWard_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DeathWard_8**<br>*Cantrip* | `Target_DeathWard_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_DeathWard_9**<br>*Cantrip* | `Target_DeathWard_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GuardianOfFaith_7**<br>*Cantrip* | `Target_GuardianOfFaith_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GuardianOfFaith_8**<br>*Cantrip* | `Target_GuardianOfFaith_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GuardianOfFaith_9**<br>*Cantrip* | `Target_GuardianOfFaith_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Harm_7**<br>*Cantrip* | `Target_Harm_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Harm_8**<br>*Cantrip* | `Target_Harm_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Harm_9**<br>*Cantrip* | `Target_Harm_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Djinni_7**<br>*Cantrip* | `Target_PlanarAlly_Djinni_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Djinni_8**<br>*Cantrip* | `Target_PlanarAlly_Djinni_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Djinni_9**<br>*Cantrip* | `Target_PlanarAlly_Djinni_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Deva_7**<br>*Cantrip* | `Target_PlanarAlly_Deva_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Deva_8**<br>*Cantrip* | `Target_PlanarAlly_Deva_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Deva_9**<br>*Cantrip* | `Target_PlanarAlly_Deva_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Deva_Banite_7**<br>*Cantrip* | `Target_PlanarAlly_Deva_Banite_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Deva_Banite_8**<br>*Cantrip* | `Target_PlanarAlly_Deva_Banite_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Deva_Banite_9**<br>*Cantrip* | `Target_PlanarAlly_Deva_Banite_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Cambion_7**<br>*Cantrip* | `Target_PlanarAlly_Cambion_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Cambion_8**<br>*Cantrip* | `Target_PlanarAlly_Cambion_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_PlanarAlly_Cambion_9**<br>*Cantrip* | `Target_PlanarAlly_Cambion_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FlameStrike_7**<br>*Cantrip* | `Target_FlameStrike_7` | **Cantrip** () | Mechanics: `DealDamage(7d6,Fire);DealDamage(7d6,Radiant,Magical)` | Learned via class level or granted by equipment |
| **Target_FlameStrike_8**<br>*Cantrip* | `Target_FlameStrike_8` | **Cantrip** () | Mechanics: `DealDamage(8d6,Fire);DealDamage(8d6,Radiant,Magical)` | Learned via class level or granted by equipment |
| **Target_FlameStrike_9**<br>*Cantrip* | `Target_FlameStrike_9` | **Cantrip** () | Mechanics: `DealDamage(9d6,Fire);DealDamage(9d6,Radiant,Magical)` | Learned via class level or granted by equipment |
| **Target_SpeakWithDead_7**<br>*Cantrip* | `Target_SpeakWithDead_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpeakWithDead_8**<br>*Cantrip* | `Target_SpeakWithDead_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpeakWithDead_9**<br>*Cantrip* | `Target_SpeakWithDead_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Greataxe_7**<br>*Cantrip* | `Target_SpiritualWeapon_Greataxe_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Greataxe_8**<br>*Cantrip* | `Target_SpiritualWeapon_Greataxe_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Greataxe_9**<br>*Cantrip* | `Target_SpiritualWeapon_Greataxe_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Greatsword_7**<br>*Cantrip* | `Target_SpiritualWeapon_Greatsword_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Greatsword_8**<br>*Cantrip* | `Target_SpiritualWeapon_Greatsword_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Greatsword_9**<br>*Cantrip* | `Target_SpiritualWeapon_Greatsword_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Halberd_7**<br>*Cantrip* | `Target_SpiritualWeapon_Halberd_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Halberd_8**<br>*Cantrip* | `Target_SpiritualWeapon_Halberd_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Halberd_9**<br>*Cantrip* | `Target_SpiritualWeapon_Halberd_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Maul_7**<br>*Cantrip* | `Target_SpiritualWeapon_Maul_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Maul_8**<br>*Cantrip* | `Target_SpiritualWeapon_Maul_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Maul_9**<br>*Cantrip* | `Target_SpiritualWeapon_Maul_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Spear_7**<br>*Cantrip* | `Target_SpiritualWeapon_Spear_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Spear_8**<br>*Cantrip* | `Target_SpiritualWeapon_Spear_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Spear_9**<br>*Cantrip* | `Target_SpiritualWeapon_Spear_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Trident_7**<br>*Cantrip* | `Target_SpiritualWeapon_Trident_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Trident_8**<br>*Cantrip* | `Target_SpiritualWeapon_Trident_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SpiritualWeapon_Trident_9**<br>*Cantrip* | `Target_SpiritualWeapon_Trident_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CalmEmotions_7**<br>*Cantrip* | `Target_CalmEmotions_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CalmEmotions_8**<br>*Cantrip* | `Target_CalmEmotions_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_CalmEmotions_9**<br>*Cantrip* | `Target_CalmEmotions_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Silence_7**<br>*Cantrip* | `Target_Silence_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Silence_8**<br>*Cantrip* | `Target_Silence_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Silence_9**<br>*Cantrip* | `Target_Silence_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_WardingBond_7**<br>*Cantrip* | `Target_WardingBond_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_WardingBond_8**<br>*Cantrip* | `Target_WardingBond_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_WardingBond_9**<br>*Cantrip* | `Target_WardingBond_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Container_7**<br>*Cantrip* | `Target_Command_Container_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Container_8**<br>*Cantrip* | `Target_Command_Container_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Container_9**<br>*Cantrip* | `Target_Command_Container_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Halt_7**<br>*Cantrip* | `Target_Command_Halt_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Halt_8**<br>*Cantrip* | `Target_Command_Halt_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Halt_9**<br>*Cantrip* | `Target_Command_Halt_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Halt_7_AI**<br>*Cantrip* | `Target_Command_Halt_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Halt_8_AI**<br>*Cantrip* | `Target_Command_Halt_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Halt_9_AI**<br>*Cantrip* | `Target_Command_Halt_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Approach_7**<br>*Cantrip* | `Target_Command_Approach_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Approach_8**<br>*Cantrip* | `Target_Command_Approach_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Approach_9**<br>*Cantrip* | `Target_Command_Approach_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Approach_7_AI**<br>*Cantrip* | `Target_Command_Approach_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Approach_8_AI**<br>*Cantrip* | `Target_Command_Approach_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Approach_9_AI**<br>*Cantrip* | `Target_Command_Approach_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Drop_7**<br>*Cantrip* | `Target_Command_Drop_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Drop_8**<br>*Cantrip* | `Target_Command_Drop_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Drop_9**<br>*Cantrip* | `Target_Command_Drop_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Drop_7_AI**<br>*Cantrip* | `Target_Command_Drop_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Drop_8_AI**<br>*Cantrip* | `Target_Command_Drop_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Drop_9_AI**<br>*Cantrip* | `Target_Command_Drop_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Flee_7**<br>*Cantrip* | `Target_Command_Flee_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Flee_8**<br>*Cantrip* | `Target_Command_Flee_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Flee_9**<br>*Cantrip* | `Target_Command_Flee_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Flee_7_AI**<br>*Cantrip* | `Target_Command_Flee_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Flee_8_AI**<br>*Cantrip* | `Target_Command_Flee_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Flee_9_AI**<br>*Cantrip* | `Target_Command_Flee_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Grovel_7**<br>*Cantrip* | `Target_Command_Grovel_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Grovel_8**<br>*Cantrip* | `Target_Command_Grovel_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Grovel_9**<br>*Cantrip* | `Target_Command_Grovel_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Grovel_7_AI**<br>*Cantrip* | `Target_Command_Grovel_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Grovel_8_AI**<br>*Cantrip* | `Target_Command_Grovel_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Command_Grovel_9_AI**<br>*Cantrip* | `Target_Command_Grovel_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Sanctuary_7**<br>*Cantrip* | `Target_Sanctuary_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Sanctuary_8**<br>*Cantrip* | `Target_Sanctuary_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Sanctuary_9**<br>*Cantrip* | `Target_Sanctuary_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ShieldOfFaith_7**<br>*Cantrip* | `Target_ShieldOfFaith_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ShieldOfFaith_8**<br>*Cantrip* | `Target_ShieldOfFaith_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ShieldOfFaith_9**<br>*Cantrip* | `Target_ShieldOfFaith_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BardicInspiration**<br>*Cantrip* | `Target_BardicInspiration` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BardicInspiration_Combat**<br>*Cantrip* | `Target_BardicInspiration_Combat` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Peerless Skill**<br>*Cantrip* | `Target_PeerlessSkill` | **Cantrip** () | When you make an ability check, you can expend one use of Bardic Inspiration and add the number rolled to your ability check. | Learned via class level or granted by equipment |
| **Target_AnimateDead_Signature**<br>*Cantrip* | `Target_AnimateDead_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_Signature**<br>*Cantrip* | `Target_BestowCurse_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Strength_Signature**<br>*Cantrip* | `Target_BestowCurse_Ability_Strength_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Dexterity_Signature**<br>*Cantrip* | `Target_BestowCurse_Ability_Dexterity_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Constitution_Signature**<br>*Cantrip* | `Target_BestowCurse_Ability_Constitution_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Intelligence_Signature**<br>*Cantrip* | `Target_BestowCurse_Ability_Intelligence_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Wisdom_Signature**<br>*Cantrip* | `Target_BestowCurse_Ability_Wisdom_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_Ability_Charisma_Signature**<br>*Cantrip* | `Target_BestowCurse_Ability_Charisma_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_Attack_Signature**<br>*Cantrip* | `Target_BestowCurse_Attack_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_ExtraDamage_Signature**<br>*Cantrip* | `Target_BestowCurse_ExtraDamage_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_BestowCurse_SkipTurn_Signature**<br>*Cantrip* | `Target_BestowCurse_SkipTurn_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Counterspell_Signature**<br>*Cantrip* | `Target_Counterspell_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_FeignDeath_Signature**<br>*Cantrip* | `Target_FeignDeath_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Fly_Signature**<br>*Cantrip* | `Target_Fly_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GaseousForm_Signature**<br>*Cantrip* | `Target_GaseousForm_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Signature**<br>*Cantrip* | `Target_GlyphOfWarding_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Acid_Signature**<br>*Cantrip* | `Target_GlyphOfWarding_Acid_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Cold_Signature**<br>*Cantrip* | `Target_GlyphOfWarding_Cold_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Fire_Signature**<br>*Cantrip* | `Target_GlyphOfWarding_Fire_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Lightning_Signature**<br>*Cantrip* | `Target_GlyphOfWarding_Lightning_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Thunder_Signature**<br>*Cantrip* | `Target_GlyphOfWarding_Thunder_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Detonation_Signature**<br>*Cantrip* | `Target_GlyphOfWarding_Detonation_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_GlyphOfWarding_Sleep_Signature**<br>*Cantrip* | `Target_GlyphOfWarding_Sleep_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Haste_Signature**<br>*Cantrip* | `Target_Haste_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_HypnoticPattern_Signature**<br>*Cantrip* | `Target_HypnoticPattern_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Signature**<br>*Cantrip* | `Target_ProtectionFromEnergy_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Acid_Signature**<br>*Cantrip* | `Target_ProtectionFromEnergy_Acid_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Cold_Signature**<br>*Cantrip* | `Target_ProtectionFromEnergy_Cold_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Fire_Signature**<br>*Cantrip* | `Target_ProtectionFromEnergy_Fire_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Lightning_Signature**<br>*Cantrip* | `Target_ProtectionFromEnergy_Lightning_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_ProtectionFromEnergy_Thunder_Signature**<br>*Cantrip* | `Target_ProtectionFromEnergy_Thunder_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_RemoveCurse_Signature**<br>*Cantrip* | `Target_RemoveCurse_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_SleetStorm_Signature**<br>*Cantrip* | `Target_SleetStorm_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_Slow_Signature**<br>*Cantrip* | `Target_Slow_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_StinkingCloud_Signature**<br>*Cantrip* | `Target_StinkingCloud_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Target_VampiricTouch_Signature**<br>*Cantrip* | `Target_VampiricTouch_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Primal Champion**<br>*Passive Feature* | `PrimalChampion` | Properties: `Highlighted`<br>Boosts: `Ability(Strength, 4);Ability(Constitution, 4)` | Your Strength and Constitution scores increase by 4. Your maximum for those scores is now 24. | Granted by class, feat, or gear set bonus |
| **Slippery Mind**<br>*Passive Feature* | `SlipperyMind` | Properties: `Highlighted`<br>Boosts: `ProficiencyBonus(SavingThrow, Wisdom)` | You gain Proficiency in Wisdom Saving Throws. | Granted by class, feat, or gear set bonus |
| **Retaliation**<br>*Passive Feature* | `Retaliation` | Properties: `Highlighted`<br>Boosts: `UnlockInterrupt(Interrupt_Retaliation)` | When a creature hits you with a melee attack, you can use your reaction to make a melee weapon attack against that creature. | Granted by class, feat, or gear set bonus |
| **Brutal Critical (2)**<br>*Passive Feature* | `BrutalCritical_2` | Properties: `Highlighted`<br>Boosts: `CriticalHitExtraDice(2, MeleeWeaponAttack);CriticalHitExtraDice(2, MeleeUnarmedAttack);` | You can roll two additional weapon damage die when determining the extra damage for a critical hit with a melee attack. | Granted by class, feat, or gear set bonus |
| **Brutal Critical (3)**<br>*Passive Feature* | `BrutalCritical_3` | Properties: `Highlighted`<br>Boosts: `CriticalHitExtraDice(3, MeleeWeaponAttack);CriticalHitExtraDice(3, MeleeUnarmedAttack);` | You can roll three additional weapon damage die when determining the extra damage for a critical hit with a melee attack. | Granted by class, feat, or gear set bonus |
| **Persistent Rage**<br>*Passive Feature* | `PersistentRage` | Properties: `Highlighted` | Your rage is so fierce that it ends early only if you fall unconscious or if you choose to end it. | Granted by class, feat, or gear set bonus |
| **Extra Attack (3)**<br>*Passive Feature* | `ExtraAttack_3` | Properties: `Highlighted` | The number of additional attacks increased to three. | Granted by class, feat, or gear set bonus |
| **Battle Magic**<br>*Passive Feature* | `BattleMagic` | Properties: `Highlighted` | When you use your action to cast a bard spell, you can make one weapon attack as a bonus action. | Granted by class, feat, or gear set bonus |
| **Improved War Magic**<br>*Passive Feature* | `WarMagicImproved` | Properties: `Highlighted` | When you use your action to cast a spell, you can make one weapon attack as a bonus action. | Granted by class, feat, or gear set bonus |
| **h4f0be183g0e15g446eg9f6cg27a8c586ba42;4;2**<br>*Passive Feature* | `UnlockedSpellSlotLevel4` | Passive buff/modifier | Passive feature mechanics | Granted by class, feat, or gear set bonus |
| **h4f0be183g0e15g446eg9f6cg27a8c586ba42;5;2**<br>*Passive Feature* | `UnlockedSpellSlotLevel5` | Passive buff/modifier | Passive feature mechanics | Granted by class, feat, or gear set bonus |
| **Thousand Forms**<br>*Passive Feature* | `ThousandForms` | Properties: `Highlighted`<br>Boosts: `UnlockSpell(Shout_DisguiseSelf)` | By 14th level, you have learned to use magic to alter your physical form in more subtle ways. You can cast the Alter Self spell at will. | Granted by class, feat, or gear set bonus |
| **Peerless Skill**<br>*Passive Feature* | `PeerlessSkill` | Properties: `Highlighted`<br>Boosts: `UnlockSpell(Target_PeerlessSkill)` | When you make an ability check, you can expend one use of Bardic Inspiration and add the number rolled to your ability check. | Granted by class, feat, or gear set bonus |
| **Corona of Light**<br>*Passive Feature* | `CoronaOfLight` | Properties: `Highlighted`<br>Boosts: `UnlockSpell(Shout_CoronaOfLight)` | You can use your action to activate an aura of sunlight that lasts for 1 minute or until you dismiss it using another action. You emit bright light in a [15]60 foot radius. | Granted by class, feat, or gear set bonus |
| **Stormborn**<br>*Passive Feature* | `Stormborn` | Properties: `Highlighted`<br>Boosts: `UnlockSpell(Projectile_Fly_Spell)` | You have a flying speed equal to your current walking speed. | Granted by class, feat, or gear set bonus |
| **Avatar of Battle**<br>*Passive Feature* | `AvatarOfBattle` | Properties: `Highlighted`<br>Boosts: `Resistance(Bludgeoning,ResistantToNonMagical);Resistance(Piercing,ResistantToNonMagical);Resistance(Slashing,ResistantToNonMagical)` | You gain resistance to bludgeoning, piercing, and slashing damage from nonmagical attacks. | Granted by class, feat, or gear set bonus |
| **Indomitable (2)**<br>*Passive Feature* | `Indomitable_2` | Properties: `Highlighted`<br>Boosts: `UnlockInterrupt(Interrupt_Indomitable);ActionResource(Interrupt_Indomitable,2,0)` | UnlockInterrupt(Interrupt_Indomitable);ActionResource(Interrupt_Indomitable,2,0) | Granted by class, feat, or gear set bonus |
| **Indomitable (3)**<br>*Passive Feature* | `Indomitable_3` | Properties: `Highlighted`<br>Boosts: `UnlockInterrupt(Interrupt_Indomitable);ActionResource(Interrupt_Indomitable,3,0)` | UnlockInterrupt(Interrupt_Indomitable);ActionResource(Interrupt_Indomitable,3,0) | Granted by class, feat, or gear set bonus |
| **Relentless**<br>*Passive Feature* | `Relentless` | Properties: `Highlighted;OncePerCombat` | When you roll initiative and have no superiority dice remaining, you regain 1 superiority die. | Granted by class, feat, or gear set bonus |
| **Tongue of the Sun and Moon**<br>*Passive Feature* | `TongueOfTheSunAndMoon` | Properties: `Highlighted`<br>Boosts: `Tag(COMPREHEND_LANGUAGES)` | You learn to touch the ki of other minds so that you understand all spoken languages. | Granted by class, feat, or gear set bonus |
| **Perfect Self**<br>*Passive Feature* | `PerfectSelf` | Properties: `Highlighted;OncePerCombat` | When you roll for initiative and have no ki points remaining, you regain 4 ki points. | Granted by class, feat, or gear set bonus |
| **Superior Critical**<br>*Passive Feature* | `SuperiorCritical` | Properties: `Highlighted`<br>Boosts: `ReduceCriticalAttackThreshold(2)` | Your weapon attacks score a critical hit on a roll of 18-20. | Granted by class, feat, or gear set bonus |
| **Survivor**<br>*Passive Feature* | `Survivor` | Properties: `Highlighted` | At the start of each of your turns, you regain hit points equal to 5 + your Constitution modifier if you have no more than half of your hit points left. You don't gain this benefit if you have 0 hit points. | Granted by class, feat, or gear set bonus |
| **Sorcerous Restoration**<br>*Passive Feature* | `SorcerousRestoration` | Properties: `Highlighted` | You regain 4 expended sorcery points whenever you finish a short rest. | Granted by class, feat, or gear set bonus |
| **Wind Soul**<br>*Passive Feature* | `WindSoul` | Properties: `Highlighted`<br>Boosts: `Resistance(Lightning, Immune);Resistance(Thunder, Immune);ActionResource(Movement, 9, 0);UnlockSpell(Projectile_Fly_Spell)` | You gain immunity to lightning and thunder damage. You also gain a magical flying speed of 60 feet. | Granted by class, feat, or gear set bonus |
| **Spell Resistance**<br>*Passive Feature* | `SpellResistance` | Properties: `Highlighted`<br>Boosts: `SpellResistance(Resistant); IF(IsSpell()):Advantage(AllSavingThrows)` | You have advantage on saving throws against spells. Furthermore, you have resistance against the damage of spells. | Granted by class, feat, or gear set bonus |
| **Superior Inspiration**<br>*Passive Feature* | `SuperiorInspiration` | Properties: `Highlighted;OncePerCombat` | When you enter combat and have no uses of Bardic Inspiration left, you regain one use. | Granted by class, feat, or gear set bonus |
| **Fungal Body**<br>*Passive Feature* | `FungalBody` | Properties: `Highlighted`<br>Boosts: `StatusImmunity(SG_Blinded);StatusImmunity(SG_Frightened);StatusImmunity(SG_Poisoned);CriticalHit(AttackTarget,Success,Never)` | The fungal spores in your body alter you: you can't be blinded, deafened, frightened, or poisoned, and any critical hit against you counts as a normal hit instead, unless you're incapacitated. | Granted by class, feat, or gear set bonus |
| **Eldritch Master**<br>*Passive Feature* | `EldritchMaster` | Properties: `Highlighted`<br>Boosts: `UnlockSpell(Shout_EldritchMaster)` | While not in combat, you can draw on your inner reserve of mystical power while entreating your patron to regain all your expended spell slots. Once you regain spell slots with this feature, you must finish a long rest before you can do so again. | Granted by class, feat, or gear set bonus |
| **Blindsense**<br>*Passive Feature* | `Blindsense` | Properties: `IsToggled;ToggledDefaultOn;Highlighted` | You are aware of the location of any hidden or invisible creature nearby. | Granted by class, feat, or gear set bonus |
| **Elusive**<br>*Passive Feature* | `Elusive` | Properties: `Highlighted` | You are so evasive that attackers rarely gain the upper hand against you. No attack roll has advantage against you while you aren't incapacitated. (currently non-functional) | Granted by class, feat, or gear set bonus |
| **Wall_WallOfStone_7**<br>*Cantrip* | `Wall_WallOfStone_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfStone_8**<br>*Cantrip* | `Wall_WallOfStone_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfStone_9**<br>*Cantrip* | `Wall_WallOfStone_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfIce_7**<br>*Cantrip* | `Wall_WallOfIce_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfIce_8**<br>*Cantrip* | `Wall_WallOfIce_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfIce_9**<br>*Cantrip* | `Wall_WallOfIce_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfFire_7**<br>*Cantrip* | `Wall_WallOfFire_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfFire_8**<br>*Cantrip* | `Wall_WallOfFire_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfFire_9**<br>*Cantrip* | `Wall_WallOfFire_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfThorns_7**<br>*Cantrip* | `Wall_WallOfThorns_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfThorns_8**<br>*Cantrip* | `Wall_WallOfThorns_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_WallOfThorns_9**<br>*Cantrip* | `Wall_WallOfThorns_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_BladeBarrier_7**<br>*Cantrip* | `Wall_BladeBarrier_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_BladeBarrier_8**<br>*Cantrip* | `Wall_BladeBarrier_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Wall_BladeBarrier_9**<br>*Cantrip* | `Wall_BladeBarrier_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_BurningHands_7**<br>*Cantrip* | `Zone_BurningHands_7` | **Cantrip** () | Mechanics: `DealDamage(9d6,Fire,Magical)` | Learned via class level or granted by equipment |
| **Zone_BurningHands_8**<br>*Cantrip* | `Zone_BurningHands_8` | **Cantrip** () | Mechanics: `DealDamage(10d6,Fire,Magical)` | Learned via class level or granted by equipment |
| **Zone_BurningHands_9**<br>*Cantrip* | `Zone_BurningHands_9` | **Cantrip** () | Mechanics: `DealDamage(11d6,Fire,Magical)` | Learned via class level or granted by equipment |
| **Zone_ColorSpray_7**<br>*Cantrip* | `Zone_ColorSpray_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_ColorSpray_8**<br>*Cantrip* | `Zone_ColorSpray_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_ColorSpray_9**<br>*Cantrip* | `Zone_ColorSpray_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_Thunderwave_7**<br>*Cantrip* | `Zone_Thunderwave_7` | **Cantrip** () | Mechanics: `DealDamage(8d8,Thunder,Magical);Force(8,OriginToTarget)` | Learned via class level or granted by equipment |
| **Zone_Thunderwave_8**<br>*Cantrip* | `Zone_Thunderwave_8` | **Cantrip** () | Mechanics: `DealDamage(9d8,Thunder,Magical);Force(8,OriginToTarget)` | Learned via class level or granted by equipment |
| **Zone_Thunderwave_9**<br>*Cantrip* | `Zone_Thunderwave_9` | **Cantrip** () | Mechanics: `DealDamage(10d8,Thunder,Magical);Force(8,OriginToTarget)` | Learned via class level or granted by equipment |
| **Zone_ConeOfCold_7**<br>*Cantrip* | `Zone_ConeOfCold_7` | **Cantrip** () | Mechanics: `DealDamage(10d8,Cold,Magical)` | Learned via class level or granted by equipment |
| **Zone_ConeOfCold_8**<br>*Cantrip* | `Zone_ConeOfCold_8` | **Cantrip** () | Mechanics: `DealDamage(11d8,Cold,Magical)` | Learned via class level or granted by equipment |
| **Zone_ConeOfCold_9**<br>*Cantrip* | `Zone_ConeOfCold_9` | **Cantrip** () | Mechanics: `DealDamage(12d8,Cold,Magical)` | Learned via class level or granted by equipment |
| **Zone_GustOfWind_7**<br>*Cantrip* | `Zone_GustOfWind_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_GustOfWind_8**<br>*Cantrip* | `Zone_GustOfWind_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_GustOfWind_9**<br>*Cantrip* | `Zone_GustOfWind_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_Fear_7**<br>*Cantrip* | `Zone_Fear_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_Fear_8**<br>*Cantrip* | `Zone_Fear_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_Fear_9**<br>*Cantrip* | `Zone_Fear_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_LightningBolt_7**<br>*Cantrip* | `Zone_LightningBolt_7` | **Cantrip** () | Mechanics: `DealDamage(12d6,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Zone_LightningBolt_8**<br>*Cantrip* | `Zone_LightningBolt_8` | **Cantrip** () | Mechanics: `DealDamage(13d6,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Zone_LightningBolt_9**<br>*Cantrip* | `Zone_LightningBolt_9` | **Cantrip** () | Mechanics: `DealDamage(14d6,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Zone_ConjureBarrage_Melee_4**<br>*Cantrip* | `Zone_ConjureBarrage_Melee_4` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_ConjureBarrage_Melee_5**<br>*Cantrip* | `Zone_ConjureBarrage_Melee_5` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_ConjureBarrage_Ranged_4**<br>*Cantrip* | `Zone_ConjureBarrage_Ranged_4` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_ConjureBarrage_Ranged_5**<br>*Cantrip* | `Zone_ConjureBarrage_Ranged_5` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_Sunbeam_7**<br>*Cantrip* | `Zone_Sunbeam_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_Sunbeam_8**<br>*Cantrip* | `Zone_Sunbeam_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_Sunbeam_9**<br>*Cantrip* | `Zone_Sunbeam_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_Fear_Signature**<br>*Cantrip* | `Zone_Fear_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Zone_LightningBolt_Signature**<br>*Cantrip* | `Zone_LightningBolt_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Teleportation_DimensionDoor_7**<br>*Cantrip* | `Teleportation_DimensionDoor_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Teleportation_DimensionDoor_8**<br>*Cantrip* | `Teleportation_DimensionDoor_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Teleportation_DimensionDoor_9**<br>*Cantrip* | `Teleportation_DimensionDoor_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Teleportation_ArcaneGate_7**<br>*Cantrip* | `Teleportation_ArcaneGate_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Teleportation_ArcaneGate_8**<br>*Cantrip* | `Teleportation_ArcaneGate_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Teleportation_ArcaneGate_9**<br>*Cantrip* | `Teleportation_ArcaneGate_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Teleportation_Revivify_7**<br>*Cantrip* | `Teleportation_Revivify_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Teleportation_Revivify_8**<br>*Cantrip* | `Teleportation_Revivify_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Teleportation_Revivify_9**<br>*Cantrip* | `Teleportation_Revivify_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_EnsnaringStrike_7**<br>*Cantrip* | `Projectile_Projectile_EnsnaringStrike_7` | **Cantrip** () | Mechanics: `IF(not SavingThrow(Ability.Strength,SourceSpellDC(),AdvantageOnRestrained(),DisadvantageOnRestrained())):ApplyStatus(ENSNARING_STRIKE_7,100,10);DealDamage(MainRangedWeapon,MainRangedWeaponDamageType);ExecuteWeaponFunctors(MainHand)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_EnsnaringStrike_8**<br>*Cantrip* | `Projectile_Projectile_EnsnaringStrike_8` | **Cantrip** () | Mechanics: `IF(not SavingThrow(Ability.Strength,SourceSpellDC(),AdvantageOnRestrained(),DisadvantageOnRestrained())):ApplyStatus(ENSNARING_STRIKE_8,100,10);DealDamage(MainRangedWeapon,MainRangedWeaponDamageType);ExecuteWeaponFunctors(MainHand)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_EnsnaringStrike_9**<br>*Cantrip* | `Projectile_Projectile_EnsnaringStrike_9` | **Cantrip** () | Mechanics: `IF(not SavingThrow(Ability.Strength,SourceSpellDC(),AdvantageOnRestrained(),DisadvantageOnRestrained())):ApplyStatus(ENSNARING_STRIKE_9,100,10);DealDamage(MainRangedWeapon,MainRangedWeaponDamageType);ExecuteWeaponFunctors(MainHand)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_Smite_Branding_7**<br>*Cantrip* | `Projectile_Projectile_Smite_Branding_7` | **Cantrip** () | Mechanics: `DealDamage(MainRangedWeapon,MainRangedWeaponDamageType);ExecuteWeaponFunctors(MainHand);DealDamage(7d6,Radiant);AOE:ApplyStatus(BRANDING_SMITE,100,10)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_Smite_Branding_8**<br>*Cantrip* | `Projectile_Projectile_Smite_Branding_8` | **Cantrip** () | Mechanics: `DealDamage(MainRangedWeapon,MainRangedWeaponDamageType);ExecuteWeaponFunctors(MainHand);DealDamage(8d6,Radiant);AOE:ApplyStatus(BRANDING_SMITE,100,10)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_Smite_Branding_9**<br>*Cantrip* | `Projectile_Projectile_Smite_Branding_9` | **Cantrip** () | Mechanics: `DealDamage(MainRangedWeapon,MainRangedWeaponDamageType);ExecuteWeaponFunctors(MainHand);DealDamage(9d6,Radiant);AOE:ApplyStatus(BRANDING_SMITE,100,10)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_AcidArrow_7**<br>*Cantrip* | `Projectile_Projectile_AcidArrow_7` | **Cantrip** () | Mechanics: `ApplyStatus(ACID_ARROW_7,100,1);DealDamage(9d4,Acid,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_AcidArrow_8**<br>*Cantrip* | `Projectile_Projectile_AcidArrow_8` | **Cantrip** () | Mechanics: `ApplyStatus(ACID_ARROW_8,100,1);DealDamage(10d4,Acid,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_AcidArrow_9**<br>*Cantrip* | `Projectile_Projectile_AcidArrow_9` | **Cantrip** () | Mechanics: `ApplyStatus(ACID_ARROW_9,100,1);DealDamage(11d4,Acid,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Acid_7**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Acid_7` | **Cantrip** () | Mechanics: `DealDamage(8d8,Acid,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Acid_8**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Acid_8` | **Cantrip** () | Mechanics: `DealDamage(9d8,Acid,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Acid_9**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Acid_9` | **Cantrip** () | Mechanics: `DealDamage(10d8,Acid,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Cold_7**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Cold_7` | **Cantrip** () | Mechanics: `DealDamage(8d8,Cold,Magical);RemoveStatus(BURNING)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Cold_8**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Cold_8` | **Cantrip** () | Mechanics: `DealDamage(9d8,Cold,Magical);RemoveStatus(BURNING)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Cold_9**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Cold_9` | **Cantrip** () | Mechanics: `DealDamage(10d8,Cold,Magical);RemoveStatus(BURNING)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Fire_7**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Fire_7` | **Cantrip** () | Mechanics: `DealDamage(8d8,Fire,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Fire_8**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Fire_8` | **Cantrip** () | Mechanics: `DealDamage(9d8,Fire,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Fire_9**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Fire_9` | **Cantrip** () | Mechanics: `DealDamage(10d8,Fire,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Lightning_7**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Lightning_7` | **Cantrip** () | Mechanics: `DealDamage(8d8,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Lightning_8**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Lightning_8` | **Cantrip** () | Mechanics: `DealDamage(9d8,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Lightning_9**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Lightning_9` | **Cantrip** () | Mechanics: `DealDamage(10d8,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Poison_7**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Poison_7` | **Cantrip** () | Mechanics: `DealDamage(8d8,Poison,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Poison_8**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Poison_8` | **Cantrip** () | Mechanics: `DealDamage(9d8,Poison,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Poison_9**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Poison_9` | **Cantrip** () | Mechanics: `DealDamage(10d8,Poison,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Thunder_7**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Thunder_7` | **Cantrip** () | Mechanics: `DealDamage(9d8,Thunder,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Thunder_8**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Thunder_8` | **Cantrip** () | Mechanics: `DealDamage(10d8,Thunder,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChromaticOrb_Thunder_9**<br>*Cantrip* | `Projectile_Projectile_ChromaticOrb_Thunder_9` | **Cantrip** () | Mechanics: `DealDamage(11d8,Thunder,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_GuidingBolt_7**<br>*Cantrip* | `Projectile_Projectile_GuidingBolt_7` | **Cantrip** () | Mechanics: `DealDamage(10d6,Radiant,Magical); ApplyStatus(GUIDING_BOLT, 100, 2)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_GuidingBolt_8**<br>*Cantrip* | `Projectile_Projectile_GuidingBolt_8` | **Cantrip** () | Mechanics: `DealDamage(11d6,Radiant,Magical); ApplyStatus(GUIDING_BOLT, 100, 2)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_GuidingBolt_9**<br>*Cantrip* | `Projectile_Projectile_GuidingBolt_9` | **Cantrip** () | Mechanics: `DealDamage(12d6,Radiant,Magical); ApplyStatus(GUIDING_BOLT, 100, 2)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_HailOfThorns_3**<br>*Cantrip* | `Projectile_Projectile_HailOfThorns_3` | **Cantrip** () | Mechanics: `TARGET:IF(Attack(AttackType.RangedWeaponAttack)):DealDamage(MainRangedWeapon, MainRangedWeaponDamageType);TARGET:AOE:IF(not HasStatus('SHIELD_MASTER') or not HasActionResource('ReactionActionPoint', 1, 0, false)):DealDamage(3d10,Piercing,Magical);TARGET:AOE:IF(HasStatus('SHIELD_MASTER') and HasActionResource('ReactionActionPoint', 1, 0, false)):DealDamage(3d10/2,Piercing,Magical);TARGET:AOE:IF(HasStatus('SHIELD_MASTER') and HasActionResource('ReactionActionPoint', 1, 0, false)):RemoveStatus(SHIELD_MASTER)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_HailOfThorns_4**<br>*Cantrip* | `Projectile_Projectile_HailOfThorns_4` | **Cantrip** () | Mechanics: `TARGET:IF(Attack(AttackType.RangedWeaponAttack)):DealDamage(MainRangedWeapon, MainRangedWeaponDamageType);TARGET:AOE:IF(not HasStatus('SHIELD_MASTER') or not HasActionResource('ReactionActionPoint', 1, 0, false)):DealDamage(4d10,Piercing,Magical);TARGET:AOE:IF(HasStatus('SHIELD_MASTER') and HasActionResource('ReactionActionPoint', 1, 0, false)):DealDamage(4d10/2,Piercing,Magical);TARGET:AOE:IF(HasStatus('SHIELD_MASTER') and HasActionResource('ReactionActionPoint', 1, 0, false)):RemoveStatus(SHIELD_MASTER)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_HailOfThorns_7**<br>*Cantrip* | `Projectile_Projectile_HailOfThorns_7` | **Cantrip** () | Mechanics: `TARGET:IF(Attack(AttackType.RangedWeaponAttack)):DealDamage(MainRangedWeapon,MainRangedWeaponDamageType);TARGET:AOE:IF(not HasStatus('SHIELD_MASTER')or not HasActionResource('ReactionActionPoint',1,0,false)):DealDamage(7d10,Piercing,Magical);TARGET:AOE:IF(HasStatus('SHIELD_MASTER')and HasActionResource('ReactionActionPoint',1,0,false)):DealDamage(7d10/2,Piercing,Magical);TARGET:AOE:IF(HasStatus('SHIELD_MASTER')and HasActionResource('ReactionActionPoint',1,0,false)):RemoveStatus(SHIELD_MASTER)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_HailOfThorns_8**<br>*Cantrip* | `Projectile_Projectile_HailOfThorns_8` | **Cantrip** () | Mechanics: `TARGET:IF(Attack(AttackType.RangedWeaponAttack)):DealDamage(MainRangedWeapon,MainRangedWeaponDamageType);TARGET:AOE:IF(not HasStatus('SHIELD_MASTER')or not HasActionResource('ReactionActionPoint',1,0,false)):DealDamage(8d10,Piercing,Magical);TARGET:AOE:IF(HasStatus('SHIELD_MASTER')and HasActionResource('ReactionActionPoint',1,0,false)):DealDamage(8d10/2,Piercing,Magical);TARGET:AOE:IF(HasStatus('SHIELD_MASTER')and HasActionResource('ReactionActionPoint',1,0,false)):RemoveStatus(SHIELD_MASTER)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_HailOfThorns_9**<br>*Cantrip* | `Projectile_Projectile_HailOfThorns_9` | **Cantrip** () | Mechanics: `TARGET:IF(Attack(AttackType.RangedWeaponAttack)):DealDamage(MainRangedWeapon,MainRangedWeaponDamageType);TARGET:AOE:IF(not HasStatus('SHIELD_MASTER')or not HasActionResource('ReactionActionPoint',1,0,false)):DealDamage(9d10,Piercing,Magical);TARGET:AOE:IF(HasStatus('SHIELD_MASTER')and HasActionResource('ReactionActionPoint',1,0,false)):DealDamage(9d10/2,Piercing,Magical);TARGET:AOE:IF(HasStatus('SHIELD_MASTER')and HasActionResource('ReactionActionPoint',1,0,false)):RemoveStatus(SHIELD_MASTER)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_WitchBolt_7**<br>*Cantrip* | `Projectile_Projectile_WitchBolt_7` | **Cantrip** () | Mechanics: `ApplyStatus(WITCH_BOLT,100,10);DealDamage(7d12,Lightning,Magical);ApplyStatus(AI_HELPER_WITCHBOLT,100,2)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_WitchBolt_8**<br>*Cantrip* | `Projectile_Projectile_WitchBolt_8` | **Cantrip** () | Mechanics: `ApplyStatus(WITCH_BOLT,100,10);DealDamage(8d12,Lightning,Magical);ApplyStatus(AI_HELPER_WITCHBOLT,100,2)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_WitchBolt_9**<br>*Cantrip* | `Projectile_Projectile_WitchBolt_9` | **Cantrip** () | Mechanics: `ApplyStatus(WITCH_BOLT,100,10);DealDamage(9d12,Lightning,Magical);ApplyStatus(AI_HELPER_WITCHBOLT,100,2)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_MagicMissile_7**<br>*Cantrip* | `Projectile_Projectile_MagicMissile_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_MagicMissile_7_AI**<br>*Cantrip* | `Projectile_Projectile_MagicMissile_7_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_MagicMissile_8**<br>*Cantrip* | `Projectile_Projectile_MagicMissile_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_MagicMissile_8_AI**<br>*Cantrip* | `Projectile_Projectile_MagicMissile_8_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_MagicMissile_9**<br>*Cantrip* | `Projectile_Projectile_MagicMissile_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_MagicMissile_9_AI**<br>*Cantrip* | `Projectile_Projectile_MagicMissile_9_AI` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_RayOfSickness_7**<br>*Cantrip* | `Projectile_Projectile_RayOfSickness_7` | **Cantrip** () | Mechanics: `IF(not SavingThrow(Ability.Constitution,SourceSpellDC(),AdvantageOnPoisoned())):ApplyStatus(POISONED,100,2);DealDamage(8d8,Poison,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_RayOfSickness_8**<br>*Cantrip* | `Projectile_Projectile_RayOfSickness_8` | **Cantrip** () | Mechanics: `IF(not SavingThrow(Ability.Constitution,SourceSpellDC(),AdvantageOnPoisoned())):ApplyStatus(POISONED,100,2);DealDamage(9d8,Poison,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_RayOfSickness_9**<br>*Cantrip* | `Projectile_Projectile_RayOfSickness_9` | **Cantrip** () | Mechanics: `IF(not SavingThrow(Ability.Constitution,SourceSpellDC(),AdvantageOnPoisoned())):ApplyStatus(POISONED,100,2);DealDamage(10d8,Poison,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ScorchingRay_7**<br>*Cantrip* | `Projectile_Projectile_ScorchingRay_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_ScorchingRay_8**<br>*Cantrip* | `Projectile_Projectile_ScorchingRay_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_ScorchingRay_9**<br>*Cantrip* | `Projectile_Projectile_ScorchingRay_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_WildMagic_Heal_7**<br>*Cantrip* | `Projectile_Projectile_WildMagic_Heal_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_WildMagic_Heal_8**<br>*Cantrip* | `Projectile_Projectile_WildMagic_Heal_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_WildMagic_Heal_9**<br>*Cantrip* | `Projectile_Projectile_WildMagic_Heal_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_RayOfEnfeeblement_7**<br>*Cantrip* | `Projectile_Projectile_RayOfEnfeeblement_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_RayOfEnfeeblement_8**<br>*Cantrip* | `Projectile_Projectile_RayOfEnfeeblement_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_RayOfEnfeeblement_9**<br>*Cantrip* | `Projectile_Projectile_RayOfEnfeeblement_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Projectile_Projectile_Fireball_7**<br>*Cantrip* | `Projectile_Projectile_Fireball_7` | **Cantrip** () | Mechanics: `DealDamage(12d6,Fire,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_Fireball_8**<br>*Cantrip* | `Projectile_Projectile_Fireball_8` | **Cantrip** () | Mechanics: `DealDamage(13d6,Fire,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_Fireball_9**<br>*Cantrip* | `Projectile_Projectile_Fireball_9` | **Cantrip** () | Mechanics: `DealDamage(14d6,Fire,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_Disintegrate_7**<br>*Cantrip* | `Projectile_Projectile_Disintegrate_7` | **Cantrip** () | Mechanics: `DealDamage(13d6+40,Force,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_Disintegrate_8**<br>*Cantrip* | `Projectile_Projectile_Disintegrate_8` | **Cantrip** () | Mechanics: `DealDamage(16d6+40,Force,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_Disintegrate_9**<br>*Cantrip* | `Projectile_Projectile_Disintegrate_9` | **Cantrip** () | Mechanics: `DealDamage(19d6+40,Force,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChainLightning_7**<br>*Cantrip* | `Projectile_Projectile_ChainLightning_7` | **Cantrip** () | Mechanics: `DealDamage(10d8,Lightning,Magical);SpawnExtraProjectiles(Projectile_ChainLightning_Explosion_7)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChainLightning_8**<br>*Cantrip* | `Projectile_Projectile_ChainLightning_8` | **Cantrip** () | Mechanics: `DealDamage(10d8,Lightning,Magical);SpawnExtraProjectiles(Projectile_ChainLightning_Explosion_8)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChainLightning_9**<br>*Cantrip* | `Projectile_Projectile_ChainLightning_9` | **Cantrip** () | Mechanics: `DealDamage(10d8,Lightning,Magical);SpawnExtraProjectiles(Projectile_ChainLightning_Explosion_9)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChainLightning_Explosion_7**<br>*Cantrip* | `Projectile_Projectile_ChainLightning_Explosion_7` | **Cantrip** () | Mechanics: `DealDamage(10d8,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChainLightning_Explosion_8**<br>*Cantrip* | `Projectile_Projectile_ChainLightning_Explosion_8` | **Cantrip** () | Mechanics: `DealDamage(10d8,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_ChainLightning_Explosion_9**<br>*Cantrip* | `Projectile_Projectile_ChainLightning_Explosion_9` | **Cantrip** () | Mechanics: `DealDamage(10d8,Lightning,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_IceKnife_7**<br>*Cantrip* | `Projectile_Projectile_IceKnife_7` | **Cantrip** () | Mechanics: `TARGET:DealDamage(1d10,Piercing);TARGET:AOE:IF(not SavingThrow(Ability.Dexterity, SourceSpellDC())):DealDamage(8d6, Cold,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_IceKnife_8**<br>*Cantrip* | `Projectile_Projectile_IceKnife_8` | **Cantrip** () | Mechanics: `TARGET:DealDamage(1d10,Piercing);TARGET:AOE:IF(not SavingThrow(Ability.Dexterity, SourceSpellDC())):DealDamage(9d6, Cold,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_IceKnife_9**<br>*Cantrip* | `Projectile_Projectile_IceKnife_9` | **Cantrip** () | Mechanics: `TARGET:DealDamage(1d10,Piercing);TARGET:AOE:IF(not SavingThrow(Ability.Dexterity, SourceSpellDC())):DealDamage(10d6, Cold,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_FreezingSphere_Hurl_7**<br>*Level 7 Spell* | `Projectile_Projectile_FreezingSphere_Hurl_7` | **Level 7 Spell** () | Mechanics: `DealDamage(11d6,Cold,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_FreezingSphere_Hurl_8**<br>*Level 8 Spell* | `Projectile_Projectile_FreezingSphere_Hurl_8` | **Level 8 Spell** () | Mechanics: `DealDamage(12d6,Cold,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_FreezingSphere_Hurl_9**<br>*Level 9 Spell* | `Projectile_Projectile_FreezingSphere_Hurl_9` | **Level 9 Spell** () | Mechanics: `DealDamage(13d6,Cold,Magical)` | Learned via class level or granted by equipment |
| **Projectile_Projectile_Fireball_Signature**<br>*Cantrip* | `Projectile_Projectile_Fireball_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **WPN_Scimitar_FlameBlade_8**<br>*Weapon* | `WPN_Scimitar_FlameBlade_8` | Damage: **6d6 ** | None | In-game inventory / Mod container |
| **Arcane Recovery: Level 6;1;2**<br>*Cantrip* | `Shout_ArcaneRecovery_6` | **Cantrip** () | Recover a Level [1] spell slot. | Learned via class level or granted by equipment |
| **Arcane Recovery: Level 7;1;2**<br>*Cantrip* | `Shout_ArcaneRecovery_7` | **Cantrip** () | Recover a Level [1] spell slot. | Learned via class level or granted by equipment |
| **Arcane Recovery: Level 8;1;2**<br>*Cantrip* | `Shout_ArcaneRecovery_8` | **Cantrip** () | Recover a Level [1] spell slot. | Learned via class level or granted by equipment |
| **Arcane Recovery: Level 9;1;2**<br>*Cantrip* | `Shout_ArcaneRecovery_9` | **Cantrip** () | Recover a Level [1] spell slot. | Learned via class level or granted by equipment |
| **Shout_ArmorOfAgathys_7**<br>*Cantrip* | `Shout_ArmorOfAgathys_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_ArmorOfAgathys_8**<br>*Cantrip* | `Shout_ArmorOfAgathys_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_ArmorOfAgathys_9**<br>*Cantrip* | `Shout_ArmorOfAgathys_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FalseLife_7**<br>*Cantrip* | `Shout_FalseLife_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FalseLife_8**<br>*Cantrip* | `Shout_FalseLife_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FalseLife_9**<br>*Cantrip* | `Shout_FalseLife_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_HellishRebuke_7**<br>*Cantrip* | `Shout_HellishRebuke_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_HellishRebuke_8**<br>*Cantrip* | `Shout_HellishRebuke_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_HellishRebuke_9**<br>*Cantrip* | `Shout_HellishRebuke_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **h59a6b918g832dg4a3bg9bc3g96d03ddf0fa7;3;2**<br>*Cantrip* | `Shout_NaturalRecovery_6` | **Cantrip** () | Recover a Level [1] spell slot. | Learned via class level or granted by equipment |
| **h59a6b918g832dg4a3bg9bc3g96d03ddf0fa7;3;2**<br>*Cantrip* | `Shout_NaturalRecovery_7` | **Cantrip** () | Recover a Level [1] spell slot. | Learned via class level or granted by equipment |
| **h59a6b918g832dg4a3bg9bc3g96d03ddf0fa7;3;2**<br>*Cantrip* | `Shout_NaturalRecovery_8` | **Cantrip** () | Recover a Level [1] spell slot. | Learned via class level or granted by equipment |
| **h59a6b918g832dg4a3bg9bc3g96d03ddf0fa7;3;2**<br>*Cantrip* | `Shout_NaturalRecovery_9` | **Cantrip** () | Recover a Level [1] spell slot. | Learned via class level or granted by equipment |
| **hcf772685g3930g428fg9e15g440dcf348ac4;1;2**<br>*Cantrip* | `Shout_WildShape_Combat_Heal_7` | **Cantrip** () | hcbc3105dgeaf4g432bgadb5g5ce8961bf317;2;2 | Learned via class level or granted by equipment |
| **hcf772685g3930g428fg9e15g440dcf348ac4;1;2**<br>*Cantrip* | `Shout_WildShape_Combat_Heal_8` | **Cantrip** () | hcbc3105dgeaf4g432bgadb5g5ce8961bf317;2;2 | Learned via class level or granted by equipment |
| **hcf772685g3930g428fg9e15g440dcf348ac4;1;2**<br>*Cantrip* | `Shout_WildShape_Combat_Heal_9` | **Cantrip** () | hcbc3105dgeaf4g432bgadb5g5ce8961bf317;2;2 | Learned via class level or granted by equipment |
| **Shout_Aid_7**<br>*Cantrip* | `Shout_Aid_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_Aid_8**<br>*Cantrip* | `Shout_Aid_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_Aid_9**<br>*Cantrip* | `Shout_Aid_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_ArmsOfHadar_7**<br>*Cantrip* | `Shout_ArmsOfHadar_7` | **Cantrip** () | Mechanics: `DealDamage(8d6,Necrotic,Magical); ApplyStatus(ARMS_OF_HADAR,100,1)` | Learned via class level or granted by equipment |
| **Shout_ArmsOfHadar_8**<br>*Cantrip* | `Shout_ArmsOfHadar_8` | **Cantrip** () | Mechanics: `DealDamage(9d6,Necrotic,Magical); ApplyStatus(ARMS_OF_HADAR,100,1)` | Learned via class level or granted by equipment |
| **Shout_ArmsOfHadar_9**<br>*Cantrip* | `Shout_ArmsOfHadar_9` | **Cantrip** () | Mechanics: `DealDamage(10d6,Necrotic,Magical); ApplyStatus(ARMS_OF_HADAR,100,1)` | Learned via class level or granted by equipment |
| **Shout_PrayerOfHealing_7**<br>*Cantrip* | `Shout_PrayerOfHealing_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_PrayerOfHealing_8**<br>*Cantrip* | `Shout_PrayerOfHealing_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_PrayerOfHealing_9**<br>*Cantrip* | `Shout_PrayerOfHealing_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_ExpeditiousRetreat_7**<br>*Cantrip* | `Shout_ExpeditiousRetreat_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_ExpeditiousRetreat_8**<br>*Cantrip* | `Shout_ExpeditiousRetreat_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_ExpeditiousRetreat_9**<br>*Cantrip* | `Shout_ExpeditiousRetreat_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FlameBlade_7**<br>*Cantrip* | `Shout_FlameBlade_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FlameBlade_8**<br>*Cantrip* | `Shout_FlameBlade_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FlameBlade_9**<br>*Cantrip* | `Shout_FlameBlade_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_Blur_7**<br>*Cantrip* | `Shout_Blur_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_Blur_8**<br>*Cantrip* | `Shout_Blur_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_Blur_9**<br>*Cantrip* | `Shout_Blur_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_MirrorImage_7**<br>*Cantrip* | `Shout_MirrorImage_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_MirrorImage_8**<br>*Cantrip* | `Shout_MirrorImage_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_MirrorImage_9**<br>*Cantrip* | `Shout_MirrorImage_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_DetectThoughts_7**<br>*Cantrip* | `Shout_DetectThoughts_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_DetectThoughts_8**<br>*Cantrip* | `Shout_DetectThoughts_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_DetectThoughts_9**<br>*Cantrip* | `Shout_DetectThoughts_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FeatherFall_7**<br>*Cantrip* | `Shout_FeatherFall_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FeatherFall_8**<br>*Cantrip* | `Shout_FeatherFall_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FeatherFall_9**<br>*Cantrip* | `Shout_FeatherFall_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SpeakWithAnimals_7**<br>*Cantrip* | `Shout_SpeakWithAnimals_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SpeakWithAnimals_8**<br>*Cantrip* | `Shout_SpeakWithAnimals_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SpeakWithAnimals_9**<br>*Cantrip* | `Shout_SpeakWithAnimals_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_PassWithoutTrace_7**<br>*Cantrip* | `Shout_PassWithoutTrace_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_PassWithoutTrace_8**<br>*Cantrip* | `Shout_PassWithoutTrace_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_PassWithoutTrace_9**<br>*Cantrip* | `Shout_PassWithoutTrace_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_Blink_7**<br>*Cantrip* | `Shout_Blink_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_Blink_8**<br>*Cantrip* | `Shout_Blink_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_Blink_9**<br>*Cantrip* | `Shout_Blink_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SeeInvisibility_5**<br>*Cantrip* | `Shout_SeeInvisibility_5` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SeeInvisibility_6**<br>*Cantrip* | `Shout_SeeInvisibility_6` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SeeInvisibility_7**<br>*Cantrip* | `Shout_SeeInvisibility_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SeeInvisibility_8**<br>*Cantrip* | `Shout_SeeInvisibility_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SeeInvisibility_9**<br>*Cantrip* | `Shout_SeeInvisibility_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FireShield_7**<br>*Cantrip* | `Shout_FireShield_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FireShield_8**<br>*Cantrip* | `Shout_FireShield_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FireShield_9**<br>*Cantrip* | `Shout_FireShield_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FireShield_Chill_7**<br>*Cantrip* | `Shout_FireShield_Chill_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FireShield_Chill_8**<br>*Cantrip* | `Shout_FireShield_Chill_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FireShield_Chill_9**<br>*Cantrip* | `Shout_FireShield_Chill_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FireShield_Warm_7**<br>*Cantrip* | `Shout_FireShield_Warm_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FireShield_Warm_8**<br>*Cantrip* | `Shout_FireShield_Warm_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_FireShield_Warm_9**<br>*Cantrip* | `Shout_FireShield_Warm_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **h38a31ba8g9b43g4da2gba82ga3edc87e7fcf;1;2**<br>*Cantrip* | `Shout_CreateSorceryPoints_5` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **h38a31ba8g9b43g4da2gba82ga3edc87e7fcf;1;2**<br>*Cantrip* | `Shout_CreateSorceryPoints_6` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **h38a31ba8g9b43g4da2gba82ga3edc87e7fcf;1;2**<br>*Cantrip* | `Shout_CreateSorceryPoints_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **h38a31ba8g9b43g4da2gba82ga3edc87e7fcf;1;2**<br>*Cantrip* | `Shout_CreateSorceryPoints_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **h38a31ba8g9b43g4da2gba82ga3edc87e7fcf;1;2**<br>*Cantrip* | `Shout_CreateSorceryPoints_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_HeroesFeast_7**<br>*Cantrip* | `Shout_HeroesFeast_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_HeroesFeast_8**<br>*Cantrip* | `Shout_HeroesFeast_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_HeroesFeast_9**<br>*Cantrip* | `Shout_HeroesFeast_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WindWalk_7**<br>*Cantrip* | `Shout_WindWalk_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WindWalk_8**<br>*Cantrip* | `Shout_WindWalk_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WindWalk_9**<br>*Cantrip* | `Shout_WindWalk_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_BeaconOfHope_7**<br>*Cantrip* | `Shout_BeaconOfHope_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_BeaconOfHope_8**<br>*Cantrip* | `Shout_BeaconOfHope_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_BeaconOfHope_9**<br>*Cantrip* | `Shout_BeaconOfHope_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_DispelEvilAndGood_7**<br>*Cantrip* | `Shout_DispelEvilAndGood_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_DispelEvilAndGood_8**<br>*Cantrip* | `Shout_DispelEvilAndGood_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_DispelEvilAndGood_9**<br>*Cantrip* | `Shout_DispelEvilAndGood_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_HealingWord_Mass_7**<br>*Cantrip* | `Shout_HealingWord_Mass_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_HealingWord_Mass_8**<br>*Cantrip* | `Shout_HealingWord_Mass_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_HealingWord_Mass_9**<br>*Cantrip* | `Shout_HealingWord_Mass_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SpiritGuardians_Necrotic_7**<br>*Cantrip* | `Shout_SpiritGuardians_Necrotic_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SpiritGuardians_Necrotic_8**<br>*Cantrip* | `Shout_SpiritGuardians_Necrotic_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SpiritGuardians_Necrotic_9**<br>*Cantrip* | `Shout_SpiritGuardians_Necrotic_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SpiritGuardians_Radiant_7**<br>*Cantrip* | `Shout_SpiritGuardians_Radiant_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SpiritGuardians_Radiant_8**<br>*Cantrip* | `Shout_SpiritGuardians_Radiant_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_SpiritGuardians_Radiant_9**<br>*Cantrip* | `Shout_SpiritGuardians_Radiant_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Badger**<br>*Cantrip* | `Shout_WildShape_Badger` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Bear_Polar**<br>*Cantrip* | `Shout_WildShape_Bear_Polar` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Cat**<br>*Cantrip* | `Shout_WildShape_Cat` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_DeepRothe**<br>*Cantrip* | `Shout_WildShape_DeepRothe` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Raven**<br>*Cantrip* | `Shout_WildShape_Raven` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Spider**<br>*Cantrip* | `Shout_WildShape_Spider` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Wolf_Dire**<br>*Cantrip* | `Shout_WildShape_Wolf_Dire` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_Wildshape_SaberTooth_Tiger**<br>*Cantrip* | `Shout_Wildshape_SaberTooth_Tiger` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_Wildshape_Panther**<br>*Cantrip* | `Shout_Wildshape_Panther` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Dilophosaurus**<br>*Cantrip* | `Shout_WildShape_Dilophosaurus` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Owlbear**<br>*Cantrip* | `Shout_WildShape_Owlbear` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Myrmidon_Air**<br>*Cantrip* | `Shout_WildShape_Myrmidon_Air` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Myrmidon_Earth**<br>*Cantrip* | `Shout_WildShape_Myrmidon_Earth` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Myrmidon_Fire**<br>*Cantrip* | `Shout_WildShape_Myrmidon_Fire` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_WildShape_Myrmidon_Water**<br>*Cantrip* | `Shout_WildShape_Myrmidon_Water` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Corona of Light**<br>*Cantrip* | `Shout_CoronaOfLight` | **Cantrip** (Evocation) | You can use your action to activate an aura of sunlight that lasts for 1 minute or until you dismiss it using another action. You emit bright light in a [15]60 foot radius. | Learned via class level or granted by equipment |
| **Dismiss Corona of Light**<br>*Cantrip* | `Shout_CoronaOfLight_Dismiss` | **Cantrip** () | Remove your aura of sunlight. | Learned via class level or granted by equipment |
| **Eldritch Master**<br>*Cantrip* | `Shout_EldritchMaster` | **Cantrip** ()<br>Recharge: OncePerRest | While not in combat, you can draw on your inner reserve of mystical power while entreating your patron to regain all your expended spell slots. Once you regain spell slots with this feature, you must finish a long rest before you can do so again. | Learned via class level or granted by equipment |
| **Shout_Blink_Signature**<br>*Cantrip* | `Shout_Blink_Signature` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_MAG_SpellSlotRestoration**<br>*Cantrip* | `Shout_MAG_SpellSlotRestoration` | **Cantrip** ()<br>Recharge: OncePerRestPerItem | Spell effect | Learned via class level or granted by equipment |
| **Shout_MAG_SpellSlotRestoration_7**<br>*Cantrip* | `Shout_MAG_SpellSlotRestoration_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_MAG_SpellSlotRestoration_8**<br>*Cantrip* | `Shout_MAG_SpellSlotRestoration_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_MAG_SpellSlotRestoration_9**<br>*Cantrip* | `Shout_MAG_SpellSlotRestoration_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Aura of Courage (10m)**<br>*Cantrip* | `Shout_AuraOf_Courage_2` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Aura of Devotion (10m)**<br>*Cantrip* | `Shout_AuraOf_Devotion_2` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Aura of Hate (10m)**<br>*Cantrip* | `Shout_AuraOf_Hate_2` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Aura of Protection (10m)**<br>*Cantrip* | `Shout_AuraOf_Protection_2` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Aura of Warding (10m)**<br>*Cantrip* | `Shout_AuraOf_Warding_2` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_ShadowBlade_Class_7**<br>*Cantrip* | `Shout_ShadowBlade_Class_7` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_ShadowBlade_Class_8**<br>*Cantrip* | `Shout_ShadowBlade_Class_8` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
| **Shout_ShadowBlade_Class_9**<br>*Cantrip* | `Shout_ShadowBlade_Class_9` | **Cantrip** () | Spell effect | Learned via class level or granted by equipment |
