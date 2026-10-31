#!/usr/bin/env python3
"""
render_modio_description.py
---------------------------
Exports a custom mod's README.md as a standalone HTML document or mod.io description.
Supports headings, lists, inline markdown, code blocks, and GFM markdown tables.
"""

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

from bg3_core.cli_common import ConsoleColor, ExitCode
from bg3_core.env_paths import MY_MODS_DIR, REPO_ROOT, resolve_mod_dir

WORKSPACE_ROOT = REPO_ROOT


def find_mod_dir(mod_query: str) -> Path:
    """Locate mod directory by path, name, or slug."""
    resolved = resolve_mod_dir(mod_query, prefer_my_mods=True, allow_substring=True)
    if resolved and resolved.is_dir():
        return resolved

    my_mods_dir = Path(os.environ.get("BG3_MODS_DIR", MY_MODS_DIR))
    if not my_mods_dir.exists():
        raise FileNotFoundError(f"my_mods directory does not exist at {my_mods_dir}")

    raise ValueError(f"No mod found in my_mods/ matching query '{mod_query}'.")


def render_inline_markdown(text: str) -> str:
    """Convert inline markdown (*, **, `, links) to safe HTML."""
    escaped = html.escape(text, quote=True)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<a href="\2">\1</a>',
        escaped,
    )
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    return escaped


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|") and len(stripped) > 2


def _is_table_separator(line: str) -> bool:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return False
    cells = [c.strip() for c in stripped[1:-1].split("|")]
    return len(cells) > 0 and all(re.match(r"^:?-+:?$", c) for c in cells if c)


def markdown_to_html(markdown: str, title_fallback: str) -> str:
    """Convert GFM markdown text into an HTML document."""
    lines = markdown.splitlines()
    title_match = next((re.match(r"^#\s+(.+?)\s*#*\s*$", line) for line in lines if line.startswith("# ")), None)
    title = title_match.group(1) if title_match else title_fallback

    body: List[str] = []
    paragraph: List[str] = []
    list_items: List[str] = []
    list_tag = ""
    code_lines: List[str] = []
    in_code_block = False
    table_lines: List[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            rendered_lines = [
                render_inline_markdown(line.rstrip())
                for line in paragraph
            ]
            paragraph_html = ""
            for index, (line, rendered) in enumerate(zip(paragraph, rendered_lines)):
                if index:
                    paragraph_html += "<br>\n" if paragraph[index - 1].endswith("  ") else " "
                paragraph_html += rendered
            body.append(f"<p>{paragraph_html}</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_tag
        if list_items:
            body.append(f"<{list_tag}>")
            body.extend(f"<li>{render_inline_markdown(item)}</li>" for item in list_items)
            body.append(f"</{list_tag}>")
            list_items.clear()
            list_tag = ""

    def flush_table() -> None:
        if not table_lines:
            return
        if len(table_lines) >= 2 and _is_table_separator(table_lines[1]):
            header_cells = [c.strip() for c in table_lines[0].strip().strip("|").split("|")]
            body.append("<table>")
            body.append("<thead><tr>" + "".join(f"<th>{render_inline_markdown(c)}</th>" for c in header_cells) + "</tr></thead>")
            body.append("<tbody>")
            for row in table_lines[2:]:
                cells = [c.strip() for c in row.strip().strip("|").split("|")]
                body.append("<tr>" + "".join(f"<td>{render_inline_markdown(c)}</td>" for c in cells) + "</tr>")
            body.append("</tbody>")
            body.append("</table>")
        else:
            for r in table_lines:
                paragraph.append(r)
            flush_paragraph()
        table_lines.clear()

    for line in lines:
        if line.strip().startswith("```"):
            flush_paragraph()
            flush_list()
            flush_table()
            if in_code_block:
                body.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
            in_code_block = not in_code_block
            continue
        if in_code_block:
            code_lines.append(line)
            continue

        if _is_table_row(line):
            flush_paragraph()
            flush_list()
            table_lines.append(line)
            continue
        elif table_lines:
            flush_table()

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            body.append(f"<h{level}>{render_inline_markdown(heading.group(2))}</h{level}>")
        elif re.match(r"^\s*[-*_]{3,}\s*$", line):
            flush_paragraph()
            flush_list()
            body.append("<hr>")
        elif re.match(r"^\s*[-*+]\s+", line):
            flush_paragraph()
            if list_tag and list_tag != "ul":
                flush_list()
            list_tag = "ul"
            list_items.append(re.sub(r"^\s*[-*+]\s+", "", line))
        elif re.match(r"^\s*\d+[.)]\s+", line):
            flush_paragraph()
            if list_tag and list_tag != "ol":
                flush_list()
            list_tag = "ol"
            list_items.append(re.sub(r"^\s*\d+[.)]\s+", "", line))
        elif not line.strip():
            flush_paragraph()
            flush_list()
        else:
            paragraph.append(line)

    flush_paragraph()
    flush_list()
    flush_table()
    if in_code_block:
        body.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; line-height: 1.6; max-width: 56rem; margin: 2rem auto; padding: 0 1rem; }}
    code, pre {{ background: #f3f4f6; }}
    code {{ padding: 0.1em 0.3em; }}
    pre {{ overflow-x: auto; padding: 1rem; }}
    table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.5rem; text-align: left; }}
    th {{ background-color: #f9fafb; }}
  </style>
</head>
<body>
{chr(10).join(body)}
</body>
</html>
"""


def render_mod_description(mod_query: str, write_file: bool = False, as_json: bool = False) -> Dict[str, Any]:
    """Render a mod's README.md to HTML and optionally write modio_description.html."""
    mod_dir = find_mod_dir(mod_query)
    readme_file = mod_dir / "README.md"
    if not readme_file.is_file():
        raise FileNotFoundError(f"Mod README not found: {readme_file}")

    html_file = mod_dir / "modio_description.html"
    html_content = markdown_to_html(readme_file.read_text(encoding="utf-8"), mod_dir.name)
    result: dict[str, Any] = {
        "mod_name": mod_dir.name,
        "mod_dir": str(mod_dir),
        "readme_file": str(readme_file),
        "html_file": str(html_file),
    }

    if write_file:
        html_file.write_text(html_content, encoding="utf-8")
        result["written_files"] = [str(html_file)]
    if as_json:
        print(json.dumps(result, indent=2))
    elif write_file:
        print(f"Generated {html_file}")
    else:
        print(html_content, end="")
    return result


process_mod_metadata = render_mod_description


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a mod's README.md as a publishing-ready HTML document."
    )
    parser.add_argument("mod_pos", nargs="?", help="Mod name or directory (positional)")
    parser.add_argument("--mod", dest="mod_flag", help="Mod name, directory in my_mods/, or mod directory path")
    parser.add_argument("--write", action="store_true", help="Write modio_description.html beside README.md")
    parser.add_argument("--json", action="store_true", help="Emit structured output information as JSON")
    args = parser.parse_args()

    mod_query = args.mod_flag or args.mod_pos
    if not mod_query:
        err_color = ConsoleColor(stream=sys.stderr)
        print(f"{err_color.red('[ERROR]')} Mod name or slug is required (via positional argument or --mod).", file=sys.stderr)
        sys.exit(ExitCode.USAGE)

    try:
        render_mod_description(mod_query=mod_query, write_file=args.write, as_json=args.json)
        sys.exit(ExitCode.OK)
    except (OSError, ValueError) as error:
        if args.json:
            print(json.dumps({"error": str(error), "success": False}, indent=2))
        else:
            err_color = ConsoleColor(stream=sys.stderr)
            print(f"{err_color.red('[ERROR]')} {error}", file=sys.stderr)
        sys.exit(ExitCode.GENERAL)


if __name__ == "__main__":
    main()
