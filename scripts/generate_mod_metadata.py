#!/usr/bin/env python3
"""
generate_mod_metadata.py
------------------------
Exports a custom mod's README.md as a standalone HTML document for publishing.
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
MY_MODS_DIR = WORKSPACE_ROOT / "my_mods"


def find_mod_dir(mod_query: str) -> Path:
    query_path = Path(mod_query).expanduser()
    if query_path.is_dir():
        return query_path

    if not MY_MODS_DIR.exists():
        raise FileNotFoundError(f"my_mods directory does not exist at {MY_MODS_DIR}")

    query_norm = mod_query.strip().lower().replace("-", "").replace("_", "")
    for candidate in MY_MODS_DIR.iterdir():
        if candidate.is_dir() and query_norm in candidate.name.lower().replace("-", "").replace("_", ""):
            return candidate
    raise ValueError(f"No mod found in my_mods/ matching query '{mod_query}'.")


def render_inline_markdown(text: str) -> str:
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


def markdown_to_html(markdown: str, title_fallback: str) -> str:
    lines = markdown.splitlines()
    title_match = next((re.match(r"^#\s+(.+?)\s*#*\s*$", line) for line in lines if line.startswith("# ")), None)
    title = title_match.group(1) if title_match else title_fallback

    body = []
    paragraph = []
    list_items = []
    list_tag = ""
    code_lines = []
    in_code_block = False

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

    for line in lines:
        if line.strip().startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code_block:
                body.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines.clear()
            in_code_block = not in_code_block
            continue
        if in_code_block:
            code_lines.append(line)
            continue

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
  </style>
</head>
<body>
{chr(10).join(body)}
</body>
</html>
"""


def process_mod_metadata(mod_query: str, write_file: bool = False, as_json: bool = False) -> dict:
    mod_dir = find_mod_dir(mod_query)
    readme_file = mod_dir / "README.md"
    if not readme_file.is_file():
        raise FileNotFoundError(f"Mod README not found: {readme_file}")

    html_file = mod_dir / "modio_description.html"
    html_content = markdown_to_html(readme_file.read_text(encoding="utf-8"), mod_dir.name)
    result = {
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a mod's README.md as a publishing-ready HTML document."
    )
    parser.add_argument("--mod", required=True, help="Mod name, directory in my_mods/, or mod directory path")
    parser.add_argument("--write", action="store_true", help="Write modio_description.html beside README.md")
    parser.add_argument("--json", action="store_true", help="Emit structured output information as JSON")
    args = parser.parse_args()

    try:
        process_mod_metadata(mod_query=args.mod, write_file=args.write, as_json=args.json)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
