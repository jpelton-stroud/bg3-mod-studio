#!/usr/bin/env python3
"""tests/test_theorycraft_simulation.py.

Comprehensive mathematical and behavioral unit tests for bg3_theorycraft:
- Proficiency bonus scaling (1-20)
- Ability score modifier calculation
- Multiclass spell slot allocations and Pact Magic slots
- Action economy resource pools (Ki, Sorcery Points, Superiority Dice, Channel Oath, Rage)
- Action economy budgets (Action Surge, Extra Attack, Fast Hands)
- Exact mathematical hit and crit probability distributions (Normal, Advantage, Disadvantage)
- Savage Attacker exact analytical expectation
- Monotonicity of AC 10-25 damage curves
- Direct integration with bg3_core.query_mod_database
- CLI argument parsing and structured JSON emissions
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from bg3_theorycraft import (
    calculate_ac_curve,
    calculate_action_economy,
    calculate_hit_probability,
    calculate_pact_slots,
    calculate_proficiency,
    calculate_resource_pools,
    calculate_savage_attacker_average,
    calculate_spell_slots,
    load_gear_boosts,
    main,
    parse_ability_modifier,
    parse_boost_effects,
    simulate_build,
    simulate_turn_1_dpr,
)


class TestProficiencyAndAbilityModifiers(unittest.TestCase):
    """Verifies proficiency bonus scaling and ability modifier mathematics."""

    def test_proficiency_bonus_progression(self) -> None:
        self.assertEqual(calculate_proficiency(1), 2)
        self.assertEqual(calculate_proficiency(4), 2)
        self.assertEqual(calculate_proficiency(5), 3)
        self.assertEqual(calculate_proficiency(8), 3)
        self.assertEqual(calculate_proficiency(9), 4)
        self.assertEqual(calculate_proficiency(12), 4)
        self.assertEqual(calculate_proficiency(13), 5)
        self.assertEqual(calculate_proficiency(16), 5)
        self.assertEqual(calculate_proficiency(17), 6)
        self.assertEqual(calculate_proficiency(20), 6)

    def test_ability_modifiers(self) -> None:
        self.assertEqual(parse_ability_modifier(8), -1)
        self.assertEqual(parse_ability_modifier(9), -1)
        self.assertEqual(parse_ability_modifier(10), 0)
        self.assertEqual(parse_ability_modifier(11), 0)
        self.assertEqual(parse_ability_modifier(12), 1)
        self.assertEqual(parse_ability_modifier(14), 2)
        self.assertEqual(parse_ability_modifier(16), 3)
        self.assertEqual(parse_ability_modifier(18), 4)
        self.assertEqual(parse_ability_modifier(20), 5)
        self.assertEqual(parse_ability_modifier(23), 6)


class TestSpellSlotMatrices(unittest.TestCase):
    """Verifies 5e multiclass spell slots and Pact Magic slot matrices."""

    def test_pure_caster_spell_slots(self) -> None:
        lvl, slots = calculate_spell_slots({"wizard": 20})
        self.assertEqual(lvl, 20)
        # Level 20 caster slots: 4/3/3/3/3/2/2/1/1
        self.assertEqual(slots, [4, 3, 3, 3, 3, 2, 2, 1, 1])

    def test_half_caster_spell_slots(self) -> None:
        lvl, slots = calculate_spell_slots({"paladin": 6})
        self.assertEqual(lvl, 3)
        # Level 3 caster: 4 1st, 2 2nd
        self.assertEqual(slots, [4, 2, 0, 0, 0, 0, 0, 0, 0])

    def test_multiclass_spell_slots(self) -> None:
        # Paladin 6 (3) + Sorcerer 14 (14) = 17 caster level
        lvl, slots = calculate_spell_slots({"paladin": 6, "sorcerer": 14})
        self.assertEqual(lvl, 17)
        self.assertEqual(slots, [4, 3, 3, 3, 2, 1, 1, 1, 1])

    def test_non_caster_slots(self) -> None:
        lvl, slots = calculate_spell_slots({"fighter": 12, "rogue": 8})
        self.assertEqual(lvl, 0)
        self.assertEqual(slots, [0] * 9)

    def test_pact_magic_slots(self) -> None:
        self.assertEqual(calculate_pact_slots(0), (0, 0))
        self.assertEqual(calculate_pact_slots(1), (1, 1))
        self.assertEqual(calculate_pact_slots(2), (2, 1))
        self.assertEqual(calculate_pact_slots(3), (2, 2))
        self.assertEqual(calculate_pact_slots(5), (2, 3))
        self.assertEqual(calculate_pact_slots(7), (2, 4))
        self.assertEqual(calculate_pact_slots(9), (2, 5))
        self.assertEqual(calculate_pact_slots(11), (3, 5))
        self.assertEqual(calculate_pact_slots(17), (4, 5))
        self.assertEqual(calculate_pact_slots(20), (4, 5))


class TestActionEconomyAndResourceBudgets(unittest.TestCase):
    """Verifies resource pools and action economy calculations."""

    def test_action_economy_budgets(self) -> None:
        # Baseline
        base = calculate_action_economy({"wizard": 4})
        self.assertEqual(base["base_actions"], 1)
        self.assertEqual(base["turn_1_actions"], 1)
        self.assertFalse(base["has_action_surge"])
        self.assertEqual(base["bonus_actions"], 1)
        self.assertEqual(base["reactions"], 1)
        self.assertEqual(base["attacks_per_action"], 1)
        self.assertEqual(base["turn_1_weapon_attacks"], 1)

        # Fighter Action Surge and Extra Attack
        f2 = calculate_action_economy({"fighter": 2})
        self.assertTrue(f2["has_action_surge"])
        self.assertEqual(f2["turn_1_actions"], 2)

        f5 = calculate_action_economy({"fighter": 5})
        self.assertEqual(f5["attacks_per_action"], 2)
        self.assertEqual(f5["turn_1_weapon_attacks"], 4)

        f11 = calculate_action_economy({"fighter": 11})
        self.assertEqual(f11["attacks_per_action"], 3)
        self.assertEqual(f11["turn_1_weapon_attacks"], 6)

        f20 = calculate_action_economy({"fighter": 20})
        self.assertEqual(f20["attacks_per_action"], 4)
        self.assertEqual(f20["turn_1_weapon_attacks"], 8)

        # Rogue Fast Hands extra Bonus Action
        rogue3 = calculate_action_economy({"rogue": 3})
        self.assertEqual(rogue3["bonus_actions"], 2)

    def test_resource_pools(self) -> None:
        # Monk Ki
        self.assertEqual(calculate_resource_pools({"monk": 1})["ki_points"], 0)
        self.assertEqual(calculate_resource_pools({"monk": 2})["ki_points"], 2)
        self.assertEqual(calculate_resource_pools({"monk": 12})["ki_points"], 12)

        # Sorcerer Sorcery Points
        self.assertEqual(calculate_resource_pools({"sorcerer": 1})["sorcery_points"], 0)
        self.assertEqual(calculate_resource_pools({"sorcerer": 2})["sorcery_points"], 2)
        self.assertEqual(calculate_resource_pools({"sorcerer": 14})["sorcery_points"], 14)

        # Fighter Superiority Dice
        f2 = calculate_resource_pools({"fighter": 2})
        self.assertEqual(f2["superiority_dice"]["count"], 0)
        self.assertEqual(f2["superiority_dice"]["die"], "None")

        f3 = calculate_resource_pools({"fighter": 3})
        self.assertEqual(f3["superiority_dice"]["count"], 4)
        self.assertEqual(f3["superiority_dice"]["die"], "d8")

        f7 = calculate_resource_pools({"fighter": 7})
        self.assertEqual(f7["superiority_dice"]["count"], 5)
        self.assertEqual(f7["superiority_dice"]["die"], "d8")

        f15 = calculate_resource_pools({"fighter": 15})
        self.assertEqual(f15["superiority_dice"]["count"], 6)
        self.assertEqual(f15["superiority_dice"]["die"], "d10")

        # Paladin Channel Oath
        self.assertEqual(calculate_resource_pools({"paladin": 1})["channel_oath_charges"], 1)
        self.assertEqual(calculate_resource_pools({"wizard": 20})["channel_oath_charges"], 0)

        # Barbarian Rage
        self.assertEqual(calculate_resource_pools({"barbarian": 1})["rage_charges"], 2)
        self.assertEqual(calculate_resource_pools({"barbarian": 3})["rage_charges"], 3)
        self.assertEqual(calculate_resource_pools({"barbarian": 6})["rage_charges"], 4)
        self.assertEqual(calculate_resource_pools({"barbarian": 12})["rage_charges"], 5)
        self.assertEqual(calculate_resource_pools({"barbarian": 17})["rage_charges"], 6)
        self.assertEqual(calculate_resource_pools({"barbarian": 20})["rage_charges"], "Unlimited")


class TestHitProbabilityMath(unittest.TestCase):
    """Verifies mathematical correctness of hit and crit probabilities."""

    def test_normal_hit_probability(self) -> None:
        # Target AC 18, attack bonus +8 -> needed_roll = 10 -> (21 - 10) / 20 = 11/20 = 0.55
        p = calculate_hit_probability(target_ac=18, attack_bonus=8, crit_threshold=20)
        self.assertEqual(p["hit_chance"], 0.55)
        self.assertEqual(p["crit_chance"], 0.05)
        self.assertEqual(p["regular_hit_chance"], 0.50)

    def test_boundary_clamping(self) -> None:
        # Extreme high AC: nat 20 always hits (5% min)
        p_high = calculate_hit_probability(target_ac=40, attack_bonus=0)
        self.assertEqual(p_high["hit_chance"], 0.05)

        # Extreme low AC: nat 1 always misses (95% max)
        p_low = calculate_hit_probability(target_ac=5, attack_bonus=20)
        self.assertEqual(p_low["hit_chance"], 0.95)

    def test_advantage_hit_probability(self) -> None:
        # P(hit) = 0.60 -> Advantage = 1 - (1 - 0.60)^2 = 1 - 0.16 = 0.84
        p_norm = calculate_hit_probability(
            target_ac=18, attack_bonus=9, crit_threshold=20, roll_mode="normal"
        )
        self.assertEqual(p_norm["hit_chance"], 0.60)

        p_adv = calculate_hit_probability(
            target_ac=18, attack_bonus=9, crit_threshold=20, roll_mode="advantage"
        )
        self.assertEqual(p_adv["hit_chance"], 0.84)
        # Crit chance with advantage: 1 - (1 - 0.05)^2 = 1 - 0.9025 = 0.0975
        self.assertEqual(p_adv["crit_chance"], 0.0975)

    def test_disadvantage_hit_probability(self) -> None:
        # P(hit) = 0.60 -> Disadvantage = 0.60^2 = 0.36
        p_dis = calculate_hit_probability(
            target_ac=18, attack_bonus=9, crit_threshold=20, roll_mode="disadvantage"
        )
        self.assertEqual(p_dis["hit_chance"], 0.36)
        # Crit chance with disadvantage: 0.05^2 = 0.0025
        self.assertEqual(p_dis["crit_chance"], 0.0025)

    def test_critical_threshold_reductions(self) -> None:
        # Champion / Gear crit on 19-20 (threshold 19): 2/20 = 0.10
        p = calculate_hit_probability(
            target_ac=18, attack_bonus=9, crit_threshold=19, roll_mode="normal"
        )
        self.assertEqual(p["crit_chance"], 0.10)

        # Crit on 18-20 (threshold 18): 3/20 = 0.15
        p18 = calculate_hit_probability(
            target_ac=18, attack_bonus=9, crit_threshold=18, roll_mode="normal"
        )
        self.assertEqual(p18["crit_chance"], 0.15)


class TestSavageAttackerMath(unittest.TestCase):
    """Verifies analytical Savage Attacker dice mathematics."""

    def test_savage_attacker_analytical_averages(self) -> None:
        # 1d6: normal avg 3.5 -> analytical savage attacker: 161 / 36 = 4.4722
        ev_1d6 = calculate_savage_attacker_average(1, 6)
        self.assertAlmostEqual(ev_1d6, 4.4722, places=3)

        # 1d8: normal avg 4.5 -> analytical savage attacker: 5.8125
        ev_1d8 = calculate_savage_attacker_average(1, 8)
        self.assertAlmostEqual(ev_1d8, 5.8125, places=3)

        # 1d10: normal avg 5.5 -> analytical savage attacker: 7.15
        ev_1d10 = calculate_savage_attacker_average(1, 10)
        self.assertAlmostEqual(ev_1d10, 7.15, places=3)

        # 1d12: normal avg 6.5 -> analytical savage attacker: 8.4861
        ev_1d12 = calculate_savage_attacker_average(1, 12)
        self.assertAlmostEqual(ev_1d12, 8.4861, places=3)

        # 2d6 Greatsword: normal avg 7.0 -> analytical savage attacker: 8.37
        ev_2d6 = calculate_savage_attacker_average(2, 6)
        self.assertAlmostEqual(ev_2d6, 8.37, places=2)
        self.assertGreater(ev_2d6, 7.0)


class TestACCurveCalculation(unittest.TestCase):
    """Verifies AC 10-25 curve generation and monotonicity."""

    def test_ac_curve_monotonicity(self) -> None:
        classes = {"paladin": 6, "sorcerer": 14}
        stats = {"Str": 16, "Dex": 10, "Con": 14, "Int": 10, "Wis": 10, "Cha": 20}
        gear_effects: dict[str, int] = {}
        prof = 6

        curve = calculate_ac_curve(
            sequence_type="melee_burst",
            classes=classes,
            stats=stats,
            gear_effects=gear_effects,
            prof=prof,
            roll_mode="normal",
            min_ac=10,
            max_ac=25,
        )

        self.assertEqual(len(curve), 16)
        # Assert DPR and hit chance are monotonically non-increasing as AC increases
        for i in range(len(curve) - 1):
            self.assertGreaterEqual(
                curve[i]["hit_chance_pct"],
                curve[i + 1]["hit_chance_pct"],
                f"Hit chance not monotonic at AC {curve[i]['target_ac']}",
            )
            self.assertGreaterEqual(
                curve[i]["expected_dpr"],
                curve[i + 1]["expected_dpr"],
                f"Expected DPR not monotonic at AC {curve[i]['target_ac']}",
            )


class TestGeneralizedMulticlassDPR(unittest.TestCase):
    """Verifies Turn 1 DPR burst calculations across class combinations."""

    def test_fighter_action_surge_scaling(self) -> None:
        stats = {"Str": 20, "Dex": 10, "Con": 14, "Int": 10, "Wis": 10, "Cha": 10}
        gear: dict[str, int] = {}

        # Fighter 5 (2 attacks, Action Surge -> 4 attacks)
        f5 = simulate_turn_1_dpr(
            "melee_burst", {"fighter": 5}, stats, gear, prof=3, target_ac=15
        )
        self.assertEqual(f5["beams_or_attacks"], 4)

        # Fighter 11 (3 attacks, Action Surge -> 6 attacks)
        f11 = simulate_turn_1_dpr(
            "melee_burst", {"fighter": 11}, stats, gear, prof=4, target_ac=15
        )
        self.assertEqual(f11["beams_or_attacks"], 6)
        self.assertGreater(f11["expected_dpr"], f5["expected_dpr"])

    def test_advantage_and_savage_attacker_increases_dpr(self) -> None:
        classes = {"paladin": 6, "fighter": 2}
        stats = {"Str": 18, "Dex": 10, "Con": 14, "Int": 10, "Wis": 10, "Cha": 16}
        gear: dict[str, int] = {}
        prof = 3

        normal_dpr = simulate_turn_1_dpr(
            "melee_burst",
            classes,
            stats,
            gear,
            prof,
            target_ac=18,
            roll_mode="normal",
            savage_attacker=False,
        )
        adv_dpr = simulate_turn_1_dpr(
            "melee_burst",
            classes,
            stats,
            gear,
            prof,
            target_ac=18,
            roll_mode="advantage",
            savage_attacker=False,
        )
        savage_dpr = simulate_turn_1_dpr(
            "melee_burst",
            classes,
            stats,
            gear,
            prof,
            target_ac=18,
            roll_mode="normal",
            savage_attacker=True,
        )

        self.assertGreater(adv_dpr["expected_dpr"], normal_dpr["expected_dpr"])
        self.assertGreater(savage_dpr["expected_dpr"], normal_dpr["expected_dpr"])

    def test_sorlock_eldritch_blast_scaling(self) -> None:
        # Sorcerer 16 / Warlock 2 / Fighter 2 (Level 20)
        # Base beams: 4 (lvl 20)
        # Action Surge: +4 beams
        # Quicken Metamagic (Sorcerer >= 3 with >= 3 SP): +4 beams
        # Total: 12 beams!
        classes = {"sorcerer": 16, "warlock": 2, "fighter": 2}
        stats = {"Str": 10, "Dex": 14, "Con": 14, "Int": 10, "Wis": 10, "Cha": 20}
        gear: dict[str, int] = {}
        prof = 6

        eb = simulate_turn_1_dpr("eldritch_blast", classes, stats, gear, prof, target_ac=18)
        self.assertEqual(eb["beams_or_attacks"], 12)
        self.assertIn("Quickened", eb["actions_used"])
        self.assertIn("Action Surge", eb["actions_used"])


class TestQueryModDatabaseIntegration(unittest.TestCase):
    """Verifies direct programmatic integration with bg3_core.query_mod_database."""

    def test_parse_boost_effects(self) -> None:
        boosts = (
            "SpellSaveDC(2); AC(1); RollBonus(Attack, 3); DamageBonus(4); "
            "ReduceCriticalThreshold(1); AbilityOverrideMinimum(Constitution, 23)"
        )
        eff = parse_boost_effects(boosts)
        self.assertEqual(eff["dc"], 2)
        self.assertEqual(eff["ac"], 1)
        self.assertEqual(eff["attack_bonus"], 3)
        self.assertEqual(eff["damage_bonus"], 4)
        self.assertEqual(eff["crit_threshold"], 1)
        self.assertEqual(eff["stats"]["Con"], 23)

    @patch("bg3_theorycraft.simulate_build_synergy.build_or_load_index")
    def test_load_gear_boosts_with_database(self, mock_index: unittest.mock.MagicMock) -> None:
        mock_index.return_value = [
            {
                "id": "MAG_SpellSaveDC_Amulet",
                "display_name": "Amulet of the Devout",
                "slot": "Amulet",
                "boosts": "SpellSaveDC(2)",
                "mod": "CommunityFixes",
            },
            {
                "id": "MAG_Legendary_Greatsword",
                "display_name": "Balduran Greatsword",
                "slot": "Weapon",
                "boosts": "DamageBonus(3); ReduceCriticalThreshold(1)",
                "damage": "2d6",
                "mod": "BalduranWeapons",
            },
        ]

        effects, loaded = load_gear_boosts(["Amulet of the Devout", "Balduran Greatsword"])
        self.assertEqual(len(loaded), 2)
        self.assertEqual(effects["dc"], 2)
        self.assertEqual(effects["damage_bonus"], 3)
        self.assertEqual(effects["crit_threshold"], 1)
        self.assertEqual(effects["weapon_damage"], "2d6")


class TestTheorycraftCLI(unittest.TestCase):
    """Verifies CLI argument parsing and output execution."""

    @patch("sys.stdout.write")
    def test_cli_execution_json(self, _mock_stdout: unittest.mock.MagicMock) -> None:
        with patch(
            "sys.argv",
            [
                "simulate_build_synergy.py",
                "--classes",
                "Paladin=6,Sorcerer=14",
                "--target-ac",
                "18",
                "--advantage",
                "--savage-attacker",
                "--ac-curve",
                "--json",
            ],
        ):
            code = main()
            self.assertEqual(code, 0)

    def test_simulate_build_high_level_api(self) -> None:
        result = simulate_build(
            classes={"paladin": 6, "sorcerer": 14},
            stats={"Str": 16, "Dex": 10, "Con": 14, "Int": 10, "Wis": 10, "Cha": 20},
            dpr_sequence="melee_burst",
            roll_mode="advantage",
            savage_attacker=True,
            include_ac_curve=True,
        )
        self.assertEqual(result["total_level"], 20)
        self.assertEqual(result["proficiency_bonus"], 6)
        self.assertIn("action_economy", result)
        self.assertIn("resource_pools", result)
        self.assertIn("ac_curve", result)
        self.assertEqual(len(result["ac_curve"]), 16)

    def test_typed_domain_models(self) -> None:
        from bg3_theorycraft.models import (
            ActionBudget,
            CombatSequence,
            ResourcePools,
            SimulationResult,
        )

        result = simulate_build(
            classes={"fighter": 11, "paladin": 2, "sorcerer": 7},
            stats={"Str": 20, "Dex": 10, "Con": 14, "Int": 10, "Wis": 10, "Cha": 16},
            dpr_sequence="melee_burst",
            roll_mode="normal",
            savage_attacker=True,
            include_ac_curve=False,
        )
        self.assertIsInstance(result, SimulationResult)
        self.assertEqual(result.total_level, 20)
        self.assertIsInstance(result.action_economy, ActionBudget)
        self.assertIsInstance(result.resource_pools, ResourcePools)
        self.assertIsInstance(result.turn_1_dpr, CombatSequence)
        self.assertEqual(result.action_economy.attacks_per_action, 3)
        self.assertEqual(result.action_economy.turn_1_weapon_attacks, 6)
        self.assertTrue(result.action_economy.has_action_surge)
        self.assertGreater(result.turn_1_dpr.expected_dpr, 50.0)
        self.assertIsNotNone(result.turn_1_dpr.damage_breakdown)
        d = result.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["total_level"], 20)

    def test_ranged_burst_sequence_and_weapon_damage_override(self) -> None:
        from bg3_theorycraft.models import CombatSequence

        stats = {"Str": 10, "Dex": 20, "Con": 14, "Int": 10, "Wis": 10, "Cha": 10}
        gear: dict[str, int] = {}

        # 1. Ranged Burst sequence with Heavy Crossbow (1d10 default)
        ranged_res = simulate_turn_1_dpr(
            "ranged_burst",
            classes={"fighter": 11, "rogue": 9},
            stats=stats,
            gear_effects=gear,
            prof=6,
            target_ac=18,
        )
        self.assertIsInstance(ranged_res, CombatSequence)
        self.assertEqual(ranged_res.sequence_type, "ranged_burst")
        self.assertEqual(ranged_res.beams_or_attacks, 6)
        self.assertIn("Action Surge", ranged_res.actions_used)
        self.assertIn("Sneak Attack", ranged_res.actions_used)
        self.assertEqual(ranged_res.damage_breakdown.weapon_base_avg, 5.5)  # 1d10 avg = 5.5
        self.assertEqual(ranged_res.damage_breakdown.sneak_attack_avg, 5 * 3.5)  # ceil(9/2) = 5d6

        # 2. Parameterized weapon damage override (1d12 Greataxe for melee)
        melee_res = simulate_turn_1_dpr(
            "melee_burst",
            classes={"fighter": 5},
            stats={"Str": 18, "Dex": 10, "Con": 14, "Int": 10, "Wis": 10, "Cha": 10},
            gear_effects=gear,
            prof=3,
            target_ac=15,
            weapon_damage="1d12",
        )
        self.assertEqual(melee_res.damage_breakdown.weapon_base_avg, 6.5)


if __name__ == "__main__":
    unittest.main()
