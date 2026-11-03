"""sorter.py

Topological sorting and dependency constraint resolution for Baldur's Gate 3 mod load orders.
"""

from __future__ import annotations

import heapq
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from bg3_core.profile.modsettings_io import (
    CORE_SYSTEM_UUIDS,
    get_mod_metadata_from_workspace,
    parse_modsettings,
    save_modsettings,
)


def topological_sort_mods(
    active_mods: dict[str, dict[str, Any]],
    dependency_graph: dict[str, list[str]],
) -> list[str]:
    """Kahn's algorithm for topological sorting of active mods by dependency constraints.

    Returns ordered list of UUIDs, with core system modules pinned first.
    """
    core_uuids: list[str] = []
    custom_uuids: list[str] = []

    for u in active_mods:
        u_norm = u.lower()
        if u_norm in CORE_SYSTEM_UUIDS:
            core_uuids.append(u)
        else:
            custom_uuids.append(u)

    in_degree: dict[str, int] = {u: 0 for u in custom_uuids}
    adj: dict[str, list[str]] = {u: [] for u in custom_uuids}
    uuid_map = {u.lower(): u for u in custom_uuids}

    for u in custom_uuids:
        deps = dependency_graph.get(u, []) or dependency_graph.get(u.lower(), [])
        for dep in deps:
            dep_norm = dep.lower()
            if dep_norm in uuid_map:
                dep_actual = uuid_map[dep_norm]
                adj[dep_actual].append(u)
                in_degree[u] += 1

    def priority_key(u: str) -> tuple[int, str]:
        name = (active_mods.get(u, {}).get("Name") or "").lower()
        if "communitylibrary" in name:
            return (0, name)
        if "compatibilityframework" in name:
            return (1, name)
        return (2, name)

    heap = [(priority_key(u), u) for u, deg in in_degree.items() if deg == 0]
    heapq.heapify(heap)

    sorted_custom: list[str] = []
    while heap:
        _, curr = heapq.heappop(heap)
        sorted_custom.append(curr)
        for neighbor in adj[curr]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                heapq.heappush(heap, (priority_key(neighbor), neighbor))

    if len(sorted_custom) < len(custom_uuids):
        remaining = [u for u in custom_uuids if u not in sorted_custom]
        sorted_custom.extend(remaining)

    return core_uuids + sorted_custom


def auto_sort_load_order(
    path: Path, dry_run: bool = False
) -> tuple[bool, list[str], dict[str, Any]]:
    """Sorts active mods in modsettings.lsx according to dependencies using topological sort."""
    if not path.is_file():
        return False, [], {"error": "modsettings.lsx not found"}

    parsed = parse_modsettings(path)
    active_mods = parsed.get("mods", {})
    if not active_mods:
        return False, [], {"error": "No active mods in modsettings.lsx"}

    dep_graph: dict[str, list[str]] = {}
    for u, m in active_mods.items():
        dep_graph[u] = []
        meta = (
            get_mod_metadata_from_workspace(u)
            or get_mod_metadata_from_workspace(m.get("Name", ""))
            or get_mod_metadata_from_workspace(m.get("Folder", ""))
            or {}
        )
        if not m.get("Name") and meta.get("Name"):
            m["Name"] = meta["Name"]
        raw_deps = meta.get("Dependencies") or m.get("Dependencies") or []
        for d in raw_deps:
            if isinstance(d, dict) and "UUID" in d:
                dep_uuid = str(d["UUID"]).strip()
                if dep_uuid and dep_uuid.lower() != u.lower():
                    dep_graph[u].append(dep_uuid)

    sorted_order = topological_sort_mods(active_mods, dep_graph)

    if not dry_run:
        tree = ET.parse(path)
        root = tree.getroot()
        mods_children = root.find(".//node[@id='Mods']/children")
        if mods_children is not None:
            descs_by_uuid: dict[str, ET.Element] = {}
            for d in list(mods_children.findall("node[@id='ModuleShortDesc']")):
                u_attr = d.find("attribute[@id='UUID']")
                if u_attr is not None:
                    descs_by_uuid[u_attr.get("value", "").lower()] = d
                    mods_children.remove(d)

            for u in sorted_order:
                node = descs_by_uuid.get(u.lower())
                if node is not None:
                    mods_children.append(node)

        mod_order_children = root.find(".//node[@id='ModOrder']/children")
        if mod_order_children is not None:
            modules_by_uuid: dict[str, ET.Element] = {}
            for m_node in list(mod_order_children.findall("node[@id='Module']")):
                u_attr = m_node.find("attribute[@id='UUID']")
                if u_attr is not None:
                    modules_by_uuid[u_attr.get("value", "").lower()] = m_node
                    mod_order_children.remove(m_node)

            for u in sorted_order:
                matched_node = modules_by_uuid.get(u.lower())
                if matched_node is not None:
                    mod_order_children.append(matched_node)

        save_modsettings(path, tree)

    return True, sorted_order, {"total_sorted": len(sorted_order), "dry_run": dry_run}
