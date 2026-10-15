#!/usr/bin/env python3
"""
scripts/modio_search.py

Searches Baldur's Gate 3 mods on mod.io using natural language queries,
platform filtering (PC/Windows, XboxSeriesX, PS5, or Console), tag mapping,
and automatic exclusion of already-tracked mods in mods/library.md.
"""

import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request

if __package__:
    from .library_catalog import parse_library_rows
else:
    from library_catalog import parse_library_rows

BG3_GAME_ID = 6715
MODIO_API_HOST = "g-6715.modapi.io"

# Pre-mapped domain terms to mod.io tags
TAG_MAPPINGS = {
    # Classes & Subclasses
    "warlock": "Warlock",
    "wizard": "Wizard",
    "sorcerer": "Sorcerer",
    "paladin": "Paladin",
    "cleric": "Cleric",
    "druid": "Druid",
    "fighter": "Fighter",
    "monk": "Monk",
    "rogue": "Rogue",
    "ranger": "Ranger",
    "bard": "Bard",
    "barbarian": "Barbarian",
    "feat": "Feats",
    "feats": "Feats",
    # Types
    "spell": "Spells",
    "spells": "Spells",
    "cantrip": "Spells",
    "cantrips": "Spells",
    "class": "Classes",
    "classes": "Classes",
    "subclass": "Subclasses",
    "subclasses": "Subclasses",
    "race": "Races",
    "races": "Races",
    "equipment": "Equipment",
    "gear": "Equipment",
    "weapon": "Equipment",
    "weapons": "Equipment",
    "armor": "Equipment",
    "armour": "Equipment",
    "qol": "Quality of Life",
    "quality of life": "Quality of Life",
    "dice": "Dice",
    "cheat": "Cheats",
    "cheats": "Cheats",
    "visual": "Visual Effects",
    "vfx": "Visual Effects",
    "overhaul": "Overhaul",
    "rules": "Rules Changes",
    "rule": "Rules Changes",
    "customisation": "Customisation",
    "customization": "Customisation",
    "hair": "Hairstyles",
    "head": "Heads",
    "tattoo": "Tattoos",
}

STOP_WORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "is", "are", "that", "this", "these", "those", "mod", "mods",
    "buff", "buffs", "nerf", "nerfs", "add", "adds", "more", "better", "best",
    "new", "some", "any", "all", "please", "search", "find", "looking"
}


def get_api_key():
    """Retrieve MODIO_API_KEY from environment or configuration files."""
    key = os.environ.get("MODIO_API_KEY")
    if key:
        return key.strip()

    # Check project .env
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_file = os.path.join(workspace_root, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("MODIO_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

    # Check ~/.config/modio/env
    home_env = os.path.expanduser("~/.config/modio/env")
    if os.path.exists(home_env):
        with open(home_env, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("MODIO_API_KEY="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")

    return None


def get_tracked_mods(workspace_root=None):
    """
    Parse mods/library.md to collect names and slugs of already tracked mods.
    """
    if workspace_root is None:
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    tracked_slugs = set()
    tracked_names = set()

    # Inspect mods/library.md
    library_path = os.path.join(workspace_root, "mods", "library.md")
    if os.path.isfile(library_path):
        with open(library_path, "r", encoding="utf-8") as f:
            rows = parse_library_rows(f.read())
        for row in rows:
            tracked_names.add(row["name"].lower())
            tracked_slugs.add(row["slug"].lower())

    return tracked_slugs, tracked_names


def normalize_platform(platform_str):
    """Normalize user platform input to mod.io platform key or special 'console' mode."""
    if not platform_str:
        return None
    p = platform_str.strip().lower()
    if p in ("pc", "windows", "win"):
        return "windows"
    if p in ("xbox", "xboxseriesx", "xbox-series-x", "xbox series x", "xsx"):
        return "xboxseriesx"
    if p in ("ps5", "playstation", "playstation5", "playstation 5", "ps"):
        return "ps5"
    if p in ("mac", "osx", "macos"):
        return "mac"
    if p in ("console", "consoles"):
        return "console"
    return p


def parse_query_terms(query_str):
    """
    Extract meaningful search terms and infer mod.io tags from natural language.
    """
    tokens = re.findall(r"[a-zA-Z0-9]+", query_str.lower())
    inferred_tags = set()
    cleaned_terms = []

    # Check two-word phrases first
    joined = query_str.lower()
    for phrase, tag in TAG_MAPPINGS.items():
        if " " in phrase and phrase in joined:
            inferred_tags.add(tag)

    # Check individual tokens
    for t in tokens:
        if t in TAG_MAPPINGS:
            inferred_tags.add(TAG_MAPPINGS[t])
        if t not in STOP_WORDS and len(t) > 1:
            cleaned_terms.append(t)

    return cleaned_terms, list(inferred_tags)


def fetch_mods_from_modio(api_key, search_text, platform, tags, limit=30):
    """
    Query the mod.io REST API with search text, platform, and optional tags.
    Also checks exact name_id/slug match if search_text matches slug patterns.
    """
    collected = []
    seen_ids = set()

    # Check exact slug lookup if search_text resembles a slug
    clean_q = search_text.strip().lower() if search_text else ""
    candidate_slugs = [
        s.strip()
        for s in re.split(r"[,\s]+", clean_q)
        if re.match(r"^[a-z0-9-]+$", s.strip()) and len(s.strip()) > 3
    ]
    if re.match(r"^[a-z0-9-]+$", clean_q) and clean_q not in candidate_slugs:
        candidate_slugs.insert(0, clean_q)

    for cand in candidate_slugs:
        slug_params = {"api_key": api_key, "name_id": cand}
        url = f"https://{MODIO_API_HOST}/v1/games/{BG3_GAME_ID}/mods?{urllib.parse.urlencode(slug_params)}"
        req = urllib.request.Request(url, headers={"User-Agent": "BG3ModSearchPipeline/1.0"})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for item in data.get("data", []):
                    if item["id"] not in seen_ids:
                        seen_ids.add(item["id"])
                        collected.append(item)
        except Exception:
            pass

    params = {
        "api_key": api_key,
        "_limit": max(50, limit * 2),  # Always fetch at least 50 candidates to allow thorough client-side filtering and ranking
    }

    if search_text:
        params["_q"] = search_text

    # Platform parameter handling
    if platform and platform != "console":
        params["platforms"] = platform
    elif platform == "console":
        params["platforms"] = "xboxseriesx"

    if tags:
        # mod.io tags filter format: tags-in=tag1,tag2
        params["tags-in"] = ",".join(tags)

    url = f"https://{MODIO_API_HOST}/v1/games/{BG3_GAME_ID}/mods?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "BG3ModSearchPipeline/1.0"})

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for item in data.get("data", []):
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    collected.append(item)
            return collected
    except Exception as e:
        # Fallback without tags-in if tag filtering fails
        if "tags-in" in params:
            params.pop("tags-in")
            url = f"https://{MODIO_API_HOST}/v1/games/{BG3_GAME_ID}/mods?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "BG3ModSearchPipeline/1.0"})
            try:
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for item in data.get("data", []):
                        if item["id"] not in seen_ids:
                            seen_ids.add(item["id"])
                            collected.append(item)
                    return collected
            except Exception:
                pass
        if collected:
            return collected
        raise RuntimeError(f"mod.io API request failed: {e}")


def filter_and_rank_mods(mods, query_str, platform, tracked_slugs, tracked_names, exclude_tracked=True, limit=15):
    """
    Filter results by platform compatibility, tracked status, and rank by relevance.
    """
    tokens, inferred_tags = parse_query_terms(query_str)
    token_set = set(tokens)
    results = []

    for m in mods:
        slug = m.get("name_id", "").lower()
        name = m.get("name", "").lower()

        # Check if tracked
        is_tracked = (slug in tracked_slugs) or (name in tracked_names)
        if exclude_tracked and is_tracked:
            continue

        # Check platform compatibility
        mod_platforms = [p.get("platform") for p in m.get("platforms", []) if isinstance(p, dict)]
        mod_tags = [t.get("name") for t in m.get("tags", []) if isinstance(t, dict)]

        if platform == "console":
            # Must support both Xbox and PS5, or have the Console tag
            has_xbox = "xboxseriesx" in mod_platforms
            has_ps5 = "ps5" in mod_platforms
            has_tag = "Available on Mac and Console" in mod_tags
            if not ((has_xbox and has_ps5) or has_tag):
                continue
        elif platform:
            if platform not in mod_platforms:
                continue

        # Calculate relevance score
        name_words = set(re.findall(r"[a-zA-Z0-9]+", name))
        summary = (m.get("summary") or "").lower()
        summary_words = set(re.findall(r"[a-zA-Z0-9]+", summary))
        tag_set = set(t.lower() for t in mod_tags)

        score = 0
        clean_q = query_str.strip().lower()
        clean_q_slug = re.sub(r"[^a-z0-9]+", "-", clean_q).strip("-")

        # Huge bonus for exact slug or exact name match
        if slug == clean_q_slug or slug == clean_q:
            score += 150
        elif name == clean_q:
            score += 100
        elif clean_q in name:
            score += 40

        # Exact token overlap with name (highest weight)
        score += len(token_set.intersection(name_words)) * 10
        # Token overlap with summary
        score += len(token_set.intersection(summary_words)) * 3
        # Inferred tag match
        for tag in inferred_tags:
            if tag.lower() in tag_set:
                score += 5

        # Subscribed popularity boost
        stats = m.get("stats") or {}
        subscribers = stats.get("subscribers_total", 0)
        score += min(subscribers / 1000.0, 5.0)

        # Build clean candidate dictionary
        description_text = m.get("description_plaintext") or m.get("summary") or ""
        # Truncate extremely long descriptions for cleaner JSON / output
        description_clean = " ".join(description_text.split()[:120])
        if len(description_text.split()) > 120:
            description_clean += "..."

        results.append({
            "id": m.get("id"),
            "name": m.get("name"),
            "name_id": m.get("name_id"),
            "summary": m.get("summary") or "",
            "description": description_clean,
            "profile_url": m.get("profile_url") or f"https://mod.io/g/baldursgate3/m/{m.get('name_id')}",
            "platforms": mod_platforms,
            "tags": mod_tags,
            "is_tracked": is_tracked,
            "score": round(score, 2),
            "subscribers": subscribers,
        })

    # Sort descending by score
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def main():
    parser = argparse.ArgumentParser(description="Search Baldur's Gate 3 mods on mod.io with natural language and platform filters.")
    parser.add_argument("--query", "-q", required=True, help="Natural language search query or keywords")
    parser.add_argument("--platform", "-p", default="windows", help="Target platform (PC/Windows, XboxSeriesX, PS5, or Console)")
    parser.add_argument("--limit", "-l", type=int, default=15, help="Maximum number of candidates to return (default: 15)")
    parser.add_argument("--include-tracked", action="store_true", help="Include mods that are already tracked in mods/library.md (default is to dump/exclude them)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    api_key = get_api_key()
    if not api_key:
        sys.stderr.write("Error: MODIO_API_KEY could not be found in environment, .env, or ~/.config/modio/env\n")
        sys.exit(1)

    norm_platform = normalize_platform(args.platform)
    terms, tags = parse_query_terms(args.query)
    search_text = " ".join(terms) if terms else args.query

    tracked_slugs, tracked_names = get_tracked_mods()

    try:
        raw_mods = fetch_mods_from_modio(
            api_key=api_key,
            search_text=search_text,
            platform=norm_platform,
            tags=tags,
            limit=args.limit
        )
    except Exception as e:
        sys.stderr.write(f"Search error: {e}\n")
        sys.exit(1)

    candidates = filter_and_rank_mods(
        mods=raw_mods,
        query_str=args.query,
        platform=norm_platform,
        tracked_slugs=tracked_slugs,
        tracked_names=tracked_names,
        exclude_tracked=not args.include_tracked,
        limit=args.limit
    )

    if args.json:
        print(json.dumps(candidates, indent=2))
        return

    # Formatted human-readable output
    platform_label = norm_platform.upper() if norm_platform else "ALL PLATFORMS"
    print(f"\n=== Found {len(candidates)} Candidate Mods for '{args.query}' (Platform: {platform_label}) ===")
    if not candidates:
        print("No matching untracked mods found.")
        return

    for idx, c in enumerate(candidates, 1):
        print(f"\n{idx}. {c['name']} (Slug: `{c['name_id']}`)")
        print(f"   Platforms: {', '.join(c['platforms'])} | Tags: {', '.join(c['tags'][:4])}")
        print(f"   URL: {c['profile_url']}")
        print(f"   Description: {c['summary']}")


if __name__ == "__main__":
    main()
