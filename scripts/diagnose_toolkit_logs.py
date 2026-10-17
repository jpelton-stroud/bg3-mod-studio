#!/usr/bin/env python3
"""diagnose_toolkit_logs.py
-------------------------
Automated diagnostic tool to inspect, classify, and triage runtime message logs
from the official Baldur's Gate 3 Toolkit (Glasses.exe).

Features:
- Auto-detects the Toolkit directory from Steam installation or .env (BG3_TOOLKIT_DIR).
- Discovers newest session logs or filters by subsystem (--type engine|osiris|thoth|personal|network).
- Classifies log entries by severity (!ASSERT!Code, !ASSERT!Design, Error, Warning).
- Categorizes messages by subsystem (Boosts, Stats, Thoth, Osiris, RootTemplates, Localization, Assets).
- Correlates errors, missing handles, or boost parse failures directly back to mod files in my_mods/.
- Supports live streaming/tailing (--follow / -f).
- Structured output (--json) and ANSI formatted CLI reports.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.lib.cli_common import ConsoleColor, ExitCode
from scripts.lib.env_paths import MODS_DIR, MY_MODS_DIR, REPO_ROOT as WORKSPACE_ROOT, detect_data_dir, get_env_var, normalize_mod_key

DEFAULT_TOOLKIT_DIR = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/Baldurs Gate 3 Toolkit")

# Zero-dependency ANSI Terminal Colors honoring NO_COLOR
_color = ConsoleColor(stream=sys.stdout)
GREEN = "\033[32m" if _color.enabled else ""
YELLOW = "\033[33m" if _color.enabled else ""
RED = "\033[31m" if _color.enabled else ""
CYAN = "\033[36m" if _color.enabled else ""
MAGENTA = "\033[35m" if _color.enabled else ""
BOLD = "\033[1m" if _color.enabled else ""
DIM = "\033[2m" if _color.enabled else ""
RESET = "\033[0m" if _color.enabled else ""

# Regex for Larian Toolkit log line format:
# [13-10-2026 22:14:17:229][D:\Jenkins\...\BoostTypes.cpp 254 eoc::FixedStringToBoostType]: !ASSERT!Design: Unknown boost type 'AI_IGNORE:Tag'
LOG_LINE_REGEX = re.compile(
    r"^\[(?P<timestamp>\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}:\d{2}:\d{3})\]"
    r"\[(?P<source>[^\]]+)\]:\s*"
    r"(?P<message>.*)$"
)


def load_env_toolkit_dir() -> Optional[Path]:
    """Inspect environment or XDG configuration for BG3_TOOLKIT_DIR."""
    val = get_env_var("BG3_TOOLKIT_DIR")
    if val:
        p = Path(val)
        if p.exists():
            return p
    return None


def resolve_toolkit_dir(cli_dir: Optional[str] = None) -> Optional[Path]:
    """Resolve the Baldur's Gate 3 Toolkit directory."""
    if cli_dir:
        p = Path(cli_dir)
        if p.is_dir():
            return p
        return None

    env_dir = load_env_toolkit_dir()
    if env_dir and env_dir.is_dir():
        return env_dir

    if DEFAULT_TOOLKIT_DIR.is_dir():
        return DEFAULT_TOOLKIT_DIR

    return None


def get_available_log_files(toolkit_dir: Path, log_type: Optional[str] = None) -> List[Path]:
    """Find all log files in the toolkit directory matching specified log type."""
    type_prefixes = {
        "engine": ["log."],
        "osiris": ["osirislog."],
        "thoth": ["thothlog."],
        "personal": ["personallog."],
        "network": ["network."],
        "all": ["log.", "osirislog.", "thothlog.", "personallog.", "network."],
    }

    prefixes = type_prefixes.get(log_type.lower() if log_type else "all", type_prefixes["all"])
    found: List[Path] = []
    try:
        for f in toolkit_dir.iterdir():
            if not f.is_file():
                continue
            for prefix in prefixes:
                if f.name.startswith(prefix) and (f.suffix in [".txt", ".log"]):
                    found.append(f)
                    break
    except Exception:
        pass

    # Sort descending by modification time
    found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return found


def classify_entry(message: str, source: str) -> Tuple[str, str]:
    """Classify severity and subsystem from a log line."""
    # Severity
    upper_msg = message.upper()
    if "!ASSERT!CODE:" in upper_msg or "CRITICAL" in upper_msg:
        severity = "CRITICAL"
    elif "!ASSERT!DESIGN:" in upper_msg or "ERROR:" in upper_msg or "!ASSERT!" in upper_msg:
        severity = "ERROR"
    elif "WARNING:" in upper_msg or "DEPRECATED" in upper_msg or "DUPLICATE" in upper_msg or "DISCARD" in upper_msg:
        severity = "WARNING"
    elif "INFO:" in upper_msg:
        severity = "INFO"
    else:
        severity = "DEBUG"

    # Subsystem
    subsystem = "General"
    src_lower = source.lower()
    msg_lower = message.lower()

    if "boost" in src_lower or "boost" in msg_lower:
        subsystem = "Boosts"
    elif "stats" in src_lower or "functor" in msg_lower or "status" in msg_lower:
        subsystem = "Stats/Status"
    elif "spell" in src_lower or "spell" in msg_lower:
        subsystem = "Spells"
    elif "thoth" in src_lower or "thoth" in msg_lower:
        subsystem = "Thoth"
    elif "osiris" in src_lower or "osiris" in msg_lower or "story" in msg_lower:
        subsystem = "Osiris"
    elif "roottemplate" in src_lower or "roottemplate" in msg_lower or "template" in msg_lower:
        subsystem = "RootTemplates"
    elif "localization" in src_lower or "handle" in msg_lower or "contentuid" in msg_lower:
        subsystem = "Localization"
    elif "modhelper" in src_lower or "dependency" in msg_lower:
        subsystem = "Dependencies"
    elif "charactercreation" in src_lower or "accessory" in msg_lower:
        subsystem = "CharacterCreation"
    elif "asset" in src_lower or "texture" in msg_lower or "visual" in msg_lower:
        subsystem = "Assets"

    return severity, subsystem


def normalize_name(s: str) -> str:
    """Normalize identifier or name for flexible matching (removes hyphens, spaces, quotes, etc.)."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


COMMON_EXCLUDES = {
    "save", "version", "region", "node", "children", "attribute", "root", "config",
    "lsstring", "fixedstring", "uint8", "uint16", "uint32", "uint64", "int64", "int32",
    "bool", "guid", "float", "true", "false", "module", "gameproject", "addon",
    "gustav", "gustavx", "shared", "shareddev", "none", "null", "type", "name", "uuid",
    "author", "description", "folder", "md5", "filesize", "publishhandle", "tableuuid",
    "progressiontype", "ismulticlass", "level", "comment", "handle", "contentuid", "content", "value"
}


def index_mod_content(mod_name: Optional[str] = None) -> Dict[str, List[Tuple[str, int, str]]]:
    """Index names, handles, and identifiers from my_mods/ to correlate with log errors.

    Returns mapping: token -> [(mod_name, line_num, relative_file_path)]
    """
    index: Dict[str, List[Tuple[str, int, str]]] = {}

    target_dirs: List[Tuple[str, Path]] = []
    if mod_name:
        mod_path = MY_MODS_DIR / mod_name
        if mod_path.is_dir():
            target_dirs.append((mod_name, mod_path))
        elif MY_MODS_DIR.is_dir():
            norm_target = normalize_name(mod_name)
            for d in MY_MODS_DIR.iterdir():
                if d.is_dir() and normalize_name(d.name) == norm_target:
                    target_dirs.append((d.name, d))
                    break

        # Also discover and index declared dependency folders (scoped to mods/<slug> and Data/Mods/<dep_folder>)
        for _, m_dir in list(target_dirs):
            for meta_path in m_dir.glob("Mods/*/meta.lsx"):
                try:
                    tree = ET.parse(meta_path)
                    for dep in tree.findall(".//node[@id='Dependencies']//node[@id='ModuleShortDesc']"):
                        d_name_attr = dep.find("attribute[@id='Name']")
                        d_folder_attr = dep.find("attribute[@id='Folder']")
                        d_name = d_name_attr.get("value", "") if d_name_attr is not None else ""
                        d_folder = d_folder_attr.get("value", "") if d_folder_attr is not None else d_name
                        if not d_name or d_name.lower() in COMMON_EXCLUDES:
                            continue
                        # Check local mods/<slug>
                        if MODS_DIR.is_dir():
                            for m_slug in (d_name, d_folder):
                                cand_dir = MODS_DIR / m_slug
                                if cand_dir.is_dir() and (d_name, cand_dir) not in target_dirs:
                                    target_dirs.append((d_name, cand_dir))
                        # Check Data/Mods/<dep_folder> (strictly scoped to this specific unpacked mod folder)
                        game_data = detect_data_dir()
                        if game_data and d_folder:
                            dep_data_dir = game_data / "Mods" / d_folder
                            if dep_data_dir.is_dir() and (d_name, dep_data_dir) not in target_dirs:
                                target_dirs.append((d_name, dep_data_dir))
                except Exception:
                    pass
    else:
        if MY_MODS_DIR.is_dir():
            for d in MY_MODS_DIR.iterdir():
                if d.is_dir():
                    target_dirs.append((d.name, d))

    guid_regex = re.compile(r"^[0-9a-fA-F-]{36}$")
    token_regex = re.compile(r"([A-Za-z0-9_-]{3,64})")
    val_regex = re.compile(r'value="([^"]+)"')
    handle_regex = re.compile(r'(?:contentuid|handle)="([^"]+)"', re.IGNORECASE)

    for m_name, m_path in target_dirs:
        for ext in [".txt", ".lsx", ".xml"]:
            for fpath in m_path.rglob(f"*{ext}"):
                if not fpath.is_file():
                    continue
                try:
                    rel_path = str(fpath.relative_to(m_path))
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for l_idx, line in enumerate(f, 1):
                            line_lower = line.lower()
                            # Index stat keys, boost names, handles
                            if "new entry" in line_lower or "using " in line_lower or "type " in line_lower:
                                parts = line.split('"')
                                if len(parts) >= 2:
                                    token = parts[1].strip()
                                    if token and token.lower() not in COMMON_EXCLUDES:
                                        index.setdefault(token, []).append((m_name, l_idx, rel_path))
                            # Index attribute values (split by semicolon/comma/parens)
                            for m in val_regex.finditer(line):
                                val = m.group(1).strip()
                                for item in re.split(r"[;,()]", val):
                                    item = item.strip()
                                    if len(item) >= 4 and not guid_regex.match(item) and item.lower() not in COMMON_EXCLUDES:
                                        index.setdefault(item, []).append((m_name, l_idx, rel_path))
                            # Index explicit localization handles
                            for m in handle_regex.finditer(line):
                                h_val = m.group(1).strip()
                                if h_val and h_val.lower() not in COMMON_EXCLUDES:
                                    index.setdefault(h_val, []).append((m_name, l_idx, rel_path))
                            # Index tokens with underscores, hyphens, handles, or PascalCase
                            for m in token_regex.finditer(line):
                                t = m.group(1)
                                if len(t) >= 4 and t.lower() not in COMMON_EXCLUDES:
                                    if "_" in t or "-" in t or t.startswith("h") or any(c.isupper() for c in t[1:]):
                                        index.setdefault(t, []).append((m_name, l_idx, rel_path))
                except Exception:
                    pass
    return index


def correlate_message(message: str, mod_index: Dict[str, List[Tuple[str, int, str]]]) -> List[Dict[str, Any]]:
    """Check if message mentions any known tokens from local workspace mods."""
    correlations: List[Dict[str, Any]] = []
    seen = set()

    # Look for tokens in quotes, brackets, or common separators
    candidates = re.findall(r"['\"`\s\(\)\[\]]([A-Za-z0-9_\-]{3,64})['\"`\s\(\)\[\]:]", message)
    # Also include the raw words and handles
    candidates.extend(re.findall(r"\b([A-Za-z0-9_\-]{3,64})\b", message))
    candidates.extend(re.findall(r"\b(h[0-9a-fA-F]{8}g[0-9a-fA-F0-9_]+)\b", message))

    for cand in candidates:
        if cand in mod_index and cand not in seen:
            seen.add(cand)
            for mod_name, line_no, file_path in mod_index[cand][:3]:  # Limit top 3 matches per token
                correlations.append({
                    "token": cand,
                    "mod": mod_name,
                    "file": file_path,
                    "line": line_no,
                })
    return correlations


def parse_log_file(
    file_path: Path,
    mod_index: Optional[Dict[str, List[Tuple[str, int, str]]]] = None,
    severity_filter: Optional[str] = None,
    subsystem_filter: Optional[str] = None,
    mod_filter: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Parse and triage entries from a given log file."""
    entries: List[Dict[str, Any]] = []
    severity_counts = {"CRITICAL": 0, "ERROR": 0, "WARNING": 0, "INFO": 0, "DEBUG": 0}
    subsystem_counts: Dict[str, int] = {}

    sev_order = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3, "DEBUG": 4}
    max_sev_rank = sev_order.get(severity_filter.upper(), 4) if severity_filter else 4

    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                m = LOG_LINE_REGEX.match(line)
                if m:
                    timestamp = m.group("timestamp")
                    source = m.group("source")
                    message = m.group("message")
                else:
                    timestamp = ""
                    source = ""
                    message = line

                sev, sub = classify_entry(message, source)
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
                subsystem_counts[sub] = subsystem_counts.get(sub, 0) + 1

                # Check severity filter
                if sev_order.get(sev, 4) > max_sev_rank:
                    continue

                # Check subsystem filter
                if subsystem_filter and subsystem_filter.lower() not in sub.lower():
                    continue

                # Correlate with workspace mods
                correlations = correlate_message(message, mod_index) if mod_index else []

                # Filter by mod if requested
                if mod_filter:
                    filter_norm = normalize_name(mod_filter)
                    mod_match = any(normalize_name(c["mod"]) == filter_norm for c in correlations)
                    if not mod_match and filter_norm not in normalize_name(message):
                        continue

                entries.append({
                    "line_number": line_no,
                    "timestamp": timestamp,
                    "source": source,
                    "severity": sev,
                    "subsystem": sub,
                    "message": message,
                    "correlations": correlations,
                })

                if limit and len(entries) >= limit:
                    break

    except Exception as e:
        return {"error": f"Failed to read {file_path}: {e}"}

    return {
        "file": str(file_path),
        "file_name": file_path.name,
        "total_lines_read": line_no if 'line_no' in locals() else 0,
        "matched_entries_count": len(entries),
        "severity_summary": severity_counts,
        "subsystem_summary": subsystem_counts,
        "entries": entries,
    }


def stream_log_file(file_path: Path, min_severity: str = "WARNING") -> Generator[Dict[str, Any], None, None]:
    """Tail and stream log lines from an active file."""
    sev_order = {"CRITICAL": 0, "ERROR": 1, "WARNING": 2, "INFO": 3, "DEBUG": 4}
    max_sev = sev_order.get(min_severity.upper(), 2)

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        # Go to the end of the file
        f.seek(0, os.SEEK_END)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue

            line = line.strip()
            if not line:
                continue

            m = LOG_LINE_REGEX.match(line)
            if m:
                timestamp = m.group("timestamp")
                source = m.group("source")
                message = m.group("message")
            else:
                timestamp = ""
                source = ""
                message = line

            sev, sub = classify_entry(message, source)
            if sev_order.get(sev, 4) <= max_sev:
                yield {
                    "timestamp": timestamp,
                    "source": source,
                    "severity": sev,
                    "subsystem": sub,
                    "message": message,
                }


def print_human_report(report: Dict[str, Any], show_correlations: bool = True):
    """Format and print an ANSI styled terminal report."""
    if "error" in report:
        print(f"{RED}Error: {report['error']}{RESET}")
        return

    fname = report.get("file_name", "Log File")
    sev = report.get("severity_summary", {})
    sub = report.get("subsystem_summary", {})
    entries = report.get("entries", [])

    print(f"\n{BOLD}{CYAN}=== BG3 Toolkit Log Diagnosis: {fname} ==={RESET}")
    print(f"Total Entries: {report.get('matched_entries_count', 0)}")
    
    # Severity Bar
    crit_str = f"{RED}{BOLD}Critical: {sev.get('CRITICAL', 0)}{RESET}" if sev.get("CRITICAL") else f"Critical: 0"
    err_str = f"{RED}Errors: {sev.get('ERROR', 0)}{RESET}" if sev.get("ERROR") else f"Errors: 0"
    warn_str = f"{YELLOW}Warnings: {sev.get('WARNING', 0)}{RESET}" if sev.get("WARNING") else f"Warnings: 0"
    print(f"Severity Breakdown:  {crit_str} | {err_str} | {warn_str} | Info: {sev.get('INFO', 0)}")

    # Top Subsystems
    top_sub = sorted(sub.items(), key=lambda x: x[1], reverse=True)[:5]
    if top_sub:
        sub_str = " | ".join([f"{k}: {v}" for k, v in top_sub if v > 0])
        print(f"Active Subsystems:   {sub_str}")
    print("-" * 75)

    if not entries:
        print(f"{GREEN}✓ No matching error or warning events discovered in this log session.{RESET}\n")
        return

    # Print Entries
    for e in entries:
        s = e["severity"]
        if s == "CRITICAL":
            badge = f"{RED}{BOLD}[CRITICAL]{RESET}"
        elif s == "ERROR":
            badge = f"{RED}[ERROR]{RESET}"
        elif s == "WARNING":
            badge = f"{YELLOW}[WARN]{RESET}"
        else:
            badge = f"{DIM}[{s}]{RESET}"

        subsys_tag = f"{MAGENTA}[{e['subsystem']}]{RESET}"
        time_tag = f"{DIM}{e['timestamp']}{RESET}" if e['timestamp'] else ""
        print(f"{badge} {subsys_tag} {time_tag} Line {e['line_number']}")
        print(f"   {e['message']}")

        if show_correlations and e.get("correlations"):
            for c in e["correlations"]:
                print(f"   ↳ {CYAN}Workspace Link{RESET}: {BOLD}{c['mod']}{RESET} -> {c['file']}:{c['line']} (Matched: '{c['token']}')")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="BG3 Toolkit Runtime Message Log Diagnostic & Triage Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--toolkit-dir", type=str, help="Path to BG3 Toolkit directory")
    parser.add_argument(
        "--type",
        choices=["engine", "osiris", "thoth", "personal", "network", "all"],
        default="engine",
        help="Subsystem log type to analyze (default: engine)",
    )
    parser.add_argument(
        "--severity",
        choices=["critical", "error", "warning", "info", "debug"],
        default="warning",
        help="Minimum severity threshold to display (default: warning)",
    )
    parser.add_argument("--subsystem", type=str, help="Filter to specific subsystem (e.g. Boosts, Stats, Thoth)")
    parser.add_argument("--mod", type=str, help="Filter and correlate errors to specific mod slug")
    parser.add_argument("--limit", type=int, default=50, help="Maximum number of log entries to display (default: 50)")
    parser.add_argument("--follow", "-f", action="store_true", help="Live stream / tail active log file")
    parser.add_argument("--list-logs", action="store_true", help="List all available session logs and exit")
    parser.add_argument("--info", action="store_true", help="Show resolved toolkit directory and status")
    parser.add_argument("--json", action="store_true", help="Emit output in structured JSON format")

    args = parser.parse_args()

    # 1. Resolve Toolkit Directory
    toolkit_dir = resolve_toolkit_dir(args.toolkit_dir)
    if not toolkit_dir or not toolkit_dir.is_dir():
        err_msg = (
            f"BG3 Toolkit directory not found. Checked default: {DEFAULT_TOOLKIT_DIR}\n"
            "Set BG3_TOOLKIT_DIR in ~/.config/bg3/env or pass --toolkit-dir <path>."
        )
        if args.json:
            print(json.dumps({"error": err_msg, "status": "not_found"}, indent=2))
        else:
            print(f"{RED}{err_msg}{RESET}", file=sys.stderr)
        sys.exit(1)

    # 2. Handle --info
    if args.info:
        logs = get_available_log_files(toolkit_dir, args.type)
        info_data = {
            "toolkit_directory": str(toolkit_dir),
            "status": "connected",
            "available_logs_count": len(logs),
            "latest_log": str(logs[0]) if logs else None,
        }
        if args.json:
            print(json.dumps(info_data, indent=2))
        else:
            print(f"{BOLD}BG3 Toolkit Directory:{RESET} {toolkit_dir}")
            print(f"Status: {GREEN}Found & Accessible{RESET}")
            print(f"Total Available Logs ({args.type}): {len(logs)}")
            if logs:
                print(f"Latest Session Log: {logs[0].name}")
        sys.exit(0)

    # 3. Handle --list-logs
    available_logs = get_available_log_files(toolkit_dir, args.type)
    if args.list_logs:
        log_records = [
            {
                "file_name": p.name,
                "path": str(p),
                "size_bytes": p.stat().st_size,
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(p.stat().st_mtime)),
            }
            for p in available_logs
        ]
        if args.json:
            print(json.dumps(log_records, indent=2))
        else:
            print(f"\n{BOLD}{CYAN}Available BG3 Toolkit Logs ({args.type}):{RESET}")
            for r in log_records[:20]:
                print(f" - {r['file_name']}  ({r['size_bytes']} bytes, Modified: {r['modified']})")
            if len(log_records) > 20:
                print(f" ... and {len(log_records) - 20} more.")
        sys.exit(ExitCode.OK)

    if not available_logs:
        msg = f"No log files found in {toolkit_dir} matching type '{args.type}'."
        if args.json:
            print(json.dumps({"error": msg}, indent=2))
        else:
            print(f"{YELLOW}{msg}{RESET}")
        sys.exit(ExitCode.OK)

    target_log = available_logs[0]

    # 4. Handle --follow (Streaming)
    if args.follow:
        print(f"{BOLD}{CYAN}Streaming live logs from:{RESET} {target_log.name} (Min severity: {args.severity.upper()})")
        print(f"Press Ctrl+C to exit.\n")
        try:
            for item in stream_log_file(target_log, min_severity=args.severity):
                if args.json:
                    print(json.dumps(item))
                else:
                    sev = item["severity"]
                    color = RED if sev in ["CRITICAL", "ERROR"] else YELLOW if sev == "WARNING" else CYAN
                    print(f"{color}[{sev}]{RESET} [{item['subsystem']}] {item['message']}")
        except KeyboardInterrupt:
            print("\nStopped streaming.")
            sys.exit(130)

    # 5. One-shot triage / parse
    mod_index = index_mod_content(args.mod)
    report = parse_log_file(
        target_log,
        mod_index=mod_index,
        severity_filter=args.severity,
        subsystem_filter=args.subsystem,
        mod_filter=args.mod,
        limit=args.limit,
    )

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_human_report(report)
    return ExitCode.OK


if __name__ == "__main__":
    sys.exit(main())
