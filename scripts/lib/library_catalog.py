"""Shared parsing and rendering for the community mod library tables."""

import re


LIBRARY_COLUMNS = (
    "Mod Id",
    "Mod Name",
    "Mod Slug",
    "Description",
    "Features Documented",
    "Spec Link",
)


def split_table_row(line):
    """Split a Markdown table row without treating escaped pipes as separators."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    fields = re.split(r"(?<!\\)\|", stripped[1:-1])
    return [field.replace(r"\|", "|").strip() for field in fields]


def parse_library_rows(content):
    """Return categorized rows from the six-column library schema."""
    rows = []
    category = ""
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("## "):
            category = line[3:].strip()
            continue
        if not line.startswith("|"):
            continue
        fields = split_table_row(line)
        if fields is None or len(fields) != len(LIBRARY_COLUMNS):
            continue
        if tuple(field.casefold() for field in fields) == tuple(
            column.casefold() for column in LIBRARY_COLUMNS
        ):
            continue
        if fields[0].startswith(":") or (
            fields[0] and set(fields[0]) <= {":", "-"}
        ):
            continue

        slug = fields[2].strip("`")
        spec_match = re.fullmatch(r"\[[^\]]*\]\(([^)]+)\)", fields[5])
        rows.append(
            {
                "mod_id": fields[0],
                "name": fields[1],
                "slug": slug,
                "description": fields[3],
                "features_documented": fields[4],
                "spec_link": spec_match.group(1) if spec_match else fields[5],
                "category": category,
            }
        )
    return rows


def render_library_row(mod):
    """Render one row using the canonical six-column schema."""
    values = (
        str(mod.get("mod_id") or ""),
        mod["title"],
        f"`{mod['slug']}`",
        mod["description"],
        f"{mod['feature_count']} implemented",
        f"[View Spec]({mod['slug']}/README.md)",
    )
    escaped = [value.replace("|", r"\|").replace("\n", " ").strip() for value in values]
    return "| " + " | ".join(escaped) + " |"
