"""Regression tests for function length and AST control flow nesting depth."""

import ast
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

REFACTORED_MODULES = [
    Path("packages/bg3-core/bg3_core/binary/lsf.py"),
    Path("packages/bg3-core/bg3_core/modio/query_mod_database.py"),
    Path("packages/bg3-core/bg3_core/modio/modio_extract.py"),
    Path("packages/bg3-core/bg3_core/profile/manage_load_order.py"),
    Path("packages/bg3-core/bg3_core/cli/router.py"),
    Path("packages/bg3-theorycraft/bg3_theorycraft/simulate_build_synergy.py"),
]

TARGET_REFACTORED_FUNCTIONS: Dict[str, List[str]] = {
    "lsf.py": [
        "_parse_attribute_value",
        "_serialize_attribute_value",
    ],
    "query_mod_database.py": [
        "parse_mod_stat_entries",
        "_apply_stat_property",
        "_classify_stat_file",
        "_build_stat_entry",
    ],
    "modio_extract.py": [
        "extract_and_verify_features",
        "_build_weapon_feature",
        "_build_armor_feature",
        "_build_spell_feature",
        "_build_passive_feature",
        "_build_object_feature",
        "_build_progression_features",
        "_determine_armor_slot",
    ],
    "manage_load_order.py": [
        "main",
        "build_load_order_parser",
        "_resolve_subcommand_aliases",
        "_resolve_modsettings_path",
        "_handle_create_default",
        "_dispatch_auto_sort",
        "_dispatch_restore",
        "_dispatch_dedup",
        "_collect_test_dependencies",
        "_dispatch_enable",
        "_dispatch_disable",
        "_dispatch_validate",
        "_dispatch_list",
    ],
    "router.py": [
        "build_parser",
        "_add_direct_subparsers",
        "_add_mod_subparsers",
        "_add_loadorder_subparsers",
        "_add_modio_subparsers",
        "_add_save_subparsers",
        "_add_build_subparsers",
        "_add_tools_subparsers",
        "_add_env_subparsers",
    ],
    "simulate_build_synergy.py": [
        "simulate_turn_1_dpr",
        "_simulate_eldritch_blast_sequence",
        "_simulate_ranged_burst_sequence",
        "_simulate_melee_burst_sequence",
        "_calculate_barbarian_rage_bonus",
        "_calculate_divine_smite_dice_avg",
    ],
}


def _calculate_max_ast_nesting_depth(node: ast.AST, depth: int = 0) -> int:
    """Calculate maximum nesting depth of control flow structures in an AST node."""
    if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.Match)):
        depth += 1
    child_depths = [_calculate_max_ast_nesting_depth(child, depth) for child in ast.iter_child_nodes(node)]
    return max([depth] + child_depths) if child_depths else depth


def _extract_functions(path: Path) -> List[Tuple[str, int, int]]:
    """Extract (func_name, line_count, ast_depth) for all functions in path."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions: List[Tuple[str, int, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", node.lineno)
            line_count = end - node.lineno + 1
            depth = _calculate_max_ast_nesting_depth(node)
            functions.append((node.name, line_count, depth))
    return functions


@pytest.mark.parametrize("module_path", REFACTORED_MODULES, ids=lambda p: p.name)
def test_all_functions_line_count_within_threshold(module_path: Path) -> None:
    """Ensure no function in refactored modules exceeds 200 lines."""
    functions = _extract_functions(module_path)
    for func_name, line_count, _ in functions:
        assert line_count <= 200, (
            f"Function '{func_name}' in {module_path.name} exceeds line limit: "
            f"{line_count} > 200 lines"
        )


@pytest.mark.parametrize("module_path", REFACTORED_MODULES, ids=lambda p: p.name)
def test_target_functions_ast_depth_within_threshold(module_path: Path) -> None:
    """Ensure target refactored functions and extracted helpers have AST nesting depth <= 5."""
    target_names = TARGET_REFACTORED_FUNCTIONS.get(module_path.name, [])
    functions = {name: (lines, depth) for name, lines, depth in _extract_functions(module_path)}

    for target in target_names:
        assert target in functions, f"Target function '{target}' not found in {module_path.name}"
        _, depth = functions[target]
        assert depth <= 5, (
            f"Target function '{target}' in {module_path.name} exceeds AST nesting threshold: "
            f"depth {depth} > 5"
        )
