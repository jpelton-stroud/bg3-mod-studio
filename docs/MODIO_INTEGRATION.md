# mod.io Integration & Community Library Guide

This guide outlines how the **Baldur's Gate 3 Mod Studio** integrates with [mod.io](https://mod.io/g/baldursgate3). The workspace is designed with a **Chat-First** philosophy: rather than memorizing complex CLI commands or manually navigating REST endpoints, you interact conversationally with autonomous agent skills that orchestrate the deterministic Python toolchain in the background.

---

## 1. Chat-First mod.io Ecosystem

Autonomous skills in [`.agents/skills/`](../.agents/skills/) allow developers and players to discover, inspect, catalog, and curate community mods through conversational instructions and slash commands.

| Category | Intent / Slash Command | Description | Primary Script Involved |
| :--- | :--- | :--- | :--- |
| Discovery | [`/bg3_search_mods`](../.agents/skills/bg3_search_mods/SKILL.md) | Discovers community mods on mod.io with natural language and platform filters, pre-filtering tracked mods. | `scripts/modio_search.py` |
| Documentation | [`/bg3_document_mods`](../.agents/skills/bg3_document_mods/SKILL.md) | Concurrently extracts, validates, and generates markdown specifications for community mods. | `scripts/modio_extract.py` |
| Maintenance | [`/bg3_update_mod_documentation`](../.agents/skills/bg3_update_mod_documentation/SKILL.md) | Checks tracked mods for upstream mod.io releases and updates local specs and catalogs. | `scripts/modio_update.py` |
| Compatibility | [`/bg3_check_mod_conflicts`](../.agents/skills/bg3_check_mod_conflicts/SKILL.md) | Analyzes mod overrides and stat collisions against cataloged library mods. | `scripts/check_mod_conflicts.py` |
| Collections | [`/bg3_create_modio_collection`](../.agents/skills/bg3_create_modio_collection/SKILL.md) | Curates and syncs public mod.io collections directly from `mods/library.md`. | `scripts/modio_create_collection.py` |

> [!NOTE]
> For complete CLI parameters, technical flag descriptions, and binary architecture details, see the [Features & Functionality Guide](FEATURES.md).

### Authentication Prerequisites

To enable mod.io discovery and download capabilities, configure your credentials once:

1. **Obtain API Keys**:
   - Visit [mod.io/me/access](https://mod.io/me/access).
   - Generate an **API Key** (for public search and downloads).
   - Generate a **Personal Access Token (PAT)** with Read/Write permissions (for profile subscriptions and collection management).
2. **Configure Credentials**:
   - Run the interactive setup launcher:
     ```bash
     ./setup.sh
     ```
   - Or populate `.env`:
     ```bash
     MODIO_API_KEY=your_key_here
     MODIO_PAT=your_pat_here
     ```

---

## 2. Discovering Community Mods (`/bg3_search_mods`)

Finding mods on mod.io can be handled directly through natural language. The `/bg3_search_mods` skill translates your search queries, applies console or platform constraints, and automatically cross-checks results against already tracked mods in your [`mods/library.md`](../mods/library.md).

### Conversational Examples

- *"Search mod.io for Warlock subclasses compatible with PS5."*
- *"Find popular gear mods with custom armor sets."*
- `"/bg3_search_mods level curve mods for xboxseries"`

### Under the Hood: Tool Execution

When invoked, the skill translates conversational parameters into a structured search call:

```bash
python3 scripts/modio_search.py "<query>" --platform <platform> --json
```

- **Candidate Pre-Filtering**: The skill inspects the JSON payload, filters out mods already tracked in [`mods/library.md`](../mods/library.md), and presents concise descriptions and download stats in chat.
- **Conflict Assessment**: Optionally coordinates with subagents to assess potential conflicts before you download.
- *Detailed script reference*: See [scripts/modio_search.py in FEATURES.md](FEATURES.md#2-autonomous-agent-skills-slash-commands).

---

## 3. Extracting & Cataloging Mod Specifications (`/bg3_document_mods`)

Once candidate mods are selected, the studio automatically downloads, decompresses, and deconstructs community `.pak` files into structured markdown specifications within [`mods/`](../mods/).

### Conversational Examples

- *"Document the mod at https://mod.io/g/baldursgate3/m/unlocklevelcurve."*
- `"/bg3_document_single_mod 4166963"`
- `"/bg3_document_mods 5e-spells unlocklevelcurve extra-gear"`

### Under the Hood: Tool Execution

The orchestrator skill coordinates background subagents running pure-Python extraction:

```bash
python3 scripts/modio_extract.py --mod-id <id-or-slug> --output-dir mods/<slug>
```

- **Deconstruction**: Downloads the archive and unpackages Larian XML/LSX and TXT data without external tools.
- **Cataloging**: Extracts spells, statuses, progression nodes, and passives into a standardized `README.md` and appends an entry to [`mods/library.md`](../mods/library.md).
- *Detailed script reference*: See [scripts/modio_extract.py in FEATURES.md](FEATURES.md#2-autonomous-agent-skills-slash-commands).

---

## 4. Tracking Upstream Updates & Account Synchronization

Keep local documentation and subscribed mods synchronized with upstream authors on mod.io.

### Conversational Examples

- `"/bg3_update_mod_documentation"` *(checks all cataloged mods for upstream updates)*
- *"Check if 5e-spells or unlocklevelcurve have new versions on mod.io."*
- *"Synchronize all mods subscribed on my mod.io profile."*

### Under the Hood: Tool Execution

The update skills and synchronization workflows leverage two core scripts:

1. **Tracking Upstream Mod Updates**:
   ```bash
   python3 scripts/modio_update.py --list-tracked --json
   ```
   The skill checks tracked mods against mod.io release timestamps. When an update is detected, it delegates to subagents to download the newest `.pak` and update the local specification.

2. **Syncing Profile Subscriptions**:
   ```bash
   # List subscribed mods or download and update all
   python3 scripts/modio_sync.py --download-all
   ```
   Uses your `MODIO_PAT` to fetch your account subscriptions and ensure your local library reflects your subscribed community content.
- *Detailed script reference*: See [scripts/modio_update.py in FEATURES.md](FEATURES.md#2-autonomous-agent-skills-slash-commands).

---

## 5. Verifying Compatibility & Mod Conflicts (`/bg3_check_mod_conflicts`)

Before deploying new community mods or when authoring custom creations, the `/bg3_check_mod_conflicts` skill verifies whether two or more mods overwrite identical game assets or require missing prerequisite frameworks.

### Conversational Examples

- `"/bg3_check_mod_conflicts unlocklevelcurve custom-subclass"`
- *"Will this new mod conflict with any mods already in my library?"*
- *"Check if my load order has any conflicting RootTemplates or duplicate stat IDs."*

### Under the Hood: Tool Execution

The skill runs static conflict analysis against cataloged definitions:

```bash
python3 scripts/check_mod_conflicts.py --json
```

- **Collision Detection**: Compares unpacked stat records, RootTemplate overrides, and prerequisite frameworks (such as `CompatibilityFramework` or `CommunityLibrary`).
- **Console Validation**: Flags non-compliant assets like native DLL dependencies or Script Extender requirements for console targets.
- *Detailed script reference*: See [scripts/check_mod_conflicts.py in FEATURES.md](FEATURES.md#2-autonomous-agent-skills-slash-commands).

---

## 6. Curating mod.io Collections (`/bg3_create_modio_collection`)

Easily publish and manage curated collections of community mods on mod.io, derived directly from your documented library.

### Conversational Examples

- `"/bg3_create_modio_collection"`
- *"Create a mod.io collection titled 'Tactician Essentials' with the mods in my library."*
- *"Preview which mods will be added to my mod.io collection."*

### Under the Hood: Tool Execution

The collection curation skill automates collection updates through mod.io REST endpoints:

```bash
# Preview proposed collection additions
python3 scripts/modio_create_collection.py --dry-run

# Commit additions to the active collection
python3 scripts/modio_create_collection.py
```

- **Library Reflection**: Pulls verified mod IDs and slugs directly from [`mods/library.md`](../mods/library.md).
- **Safe Staging**: Supports `--dry-run` to preview remote modifications before mutating live collection data.
- *Detailed script reference*: See [scripts/modio_create_collection.py in FEATURES.md](FEATURES.md#2-autonomous-agent-skills-slash-commands).
