# mod.io Integration & Community Library Guide

This guide outlines how the **Baldur's Gate 3 Mod Studio** integrates with [mod.io](https://mod.io/g/baldursgate3). The workspace is designed with a **Chat-First** philosophy: rather than memorizing complex CLI commands or manually navigating REST endpoints, you interact conversationally with autonomous agent skills that orchestrate the deterministic Python toolchain in the background.

---

## 1. Chat-First mod.io Ecosystem

Autonomous skills in [`.agents/skills/`](../.agents/skills/) allow developers and players to discover, inspect, catalog, and curate community mods through conversational instructions and slash commands.

| Category | Intent / Slash Command | Description | Canonical CLI Command & Module |
| :--- | :--- | :--- | :--- |
| Discovery | [`/bg3-search-mods`](../.agents/skills/bg3-search-mods/SKILL.md) | Discovers community mods on mod.io with natural language and platform filters, pre-filtering tracked mods. | `bg3 modio search`<br>(`bg3_core.modio_search`) |
| Documentation | [`/bg3-document-mods`](../.agents/skills/bg3-document-mods/SKILL.md) | Concurrently extracts, validates, and generates markdown specifications for community mods. | `bg3 modio extract`<br>(`bg3_core.modio_extract`) |
| Maintenance | [`/bg3-update-mod-documentation`](../.agents/skills/bg3-update-mod-documentation/SKILL.md) | Checks tracked mods for upstream mod.io releases and updates local specs and catalogs. | `bg3 modio update`<br>(`bg3_core.modio_update`) |
| Compatibility | [`/bg3-check-mod-conflicts`](../.agents/skills/bg3-check-mod-conflicts/SKILL.md) | Analyzes mod overrides and stat collisions against cataloged library mods. | `bg3 mod conflict`<br>(`bg3_authoring.diagnostics.check_mod_conflicts`) |
| Collections | [`/bg3-create-modio-collection`](../.agents/skills/bg3-create-modio-collection/SKILL.md) | Curates and syncs public mod.io collections directly from library catalog. | `bg3 modio create-collection`<br>(`bg3_core.modio_create_collection`) |

> [!NOTE]
> For complete CLI parameters, technical flag descriptions, and binary architecture details, see the [Features & Functionality Guide](FEATURES.md).

### Authentication Prerequisites

To enable mod.io discovery and download capabilities, configure your credentials once:

1. **Obtain API Keys**:
   - Visit [mod.io/me/access](https://mod.io/me/access).
   - Generate an **API Key** (for public search and downloads).
   - Generate a **Personal Access Token (PAT)** with Read/Write permissions (for profile subscriptions and collection management).
2. **Configure Credentials (XDG Standard)**:
   - Run the interactive setup launcher:
     ```bash
     ./setup.sh
     ```
     *(or run `bg3 env setup`)*
   - The setup wizard stores credentials securely in `$XDG_CONFIG_HOME/bg3/env` (default: `~/.config/bg3/env`) with strict POSIX mode `0600` permissions. Repository-level `.env` files are eliminated to prevent leaking secrets.
   - Verify path and environment configuration anytime:
     ```bash
     bg3 env paths
     bg3 env check
     ```

---

## 1.5 Official Larian Mod Publishing Requirements

> [!IMPORTANT]
> **Official Larian Mod.io Publishing Protocol**:
> Baldur's Gate 3 mod packages (`.pak`) **cannot** be uploaded via generic mod.io REST APIs or third-party automated HTTP scripts. Larian Studios explicitly mandates that all community mods must be validated, packaged, and published to mod.io directly through the official **Baldur's Gate 3 Toolkit (`Glasses.exe`)**.
> 
> The BG3 Mod Studio manages local staging, metadata synchronization (`bg3 modio update-metadata`), tagging, and collection curation, while binary packaging and store release are completed via the official Toolkit publisher interface. Automated headless binary upload endpoints are not supported by Larian's backend and must not be proposed.

---

## 2. Discovering Community Mods (`/bg3-search-mods`)

Finding mods on mod.io can be handled directly through natural language. The `/bg3-search-mods` skill translates your search queries, applies console or platform constraints, and automatically cross-checks results against already tracked mods in your library catalog (`Mods/subscribed/library.md`).

### Conversational Examples

- *"Search mod.io for Warlock subclasses compatible with PS5."*
- *"Find popular gear mods with custom armor sets."*
- `"/bg3-search-mods level curve mods for xboxseries"`

### Under the Hood: Tool Execution

When invoked, the skill translates conversational parameters into a structured search call:

```bash
# Primary CLI command
bg3 modio search "<query>" --platform <platform> --json

# Direct module execution
uv run -m bg3_core.modio_search "<query>" --platform <platform> --json
```

- **Candidate Pre-Filtering**: The skill inspects the JSON payload, filters out mods already tracked in `Mods/subscribed/library.md`, and presents concise descriptions and download stats in chat.
- **Conflict Assessment**: Optionally coordinates with subagents to assess potential conflicts before you download.
- *Detailed reference*: See [FEATURES.md § 3.6](FEATURES.md#36-library--modio-search-tools-packagesbg3-core).

---

## 3. Extracting & Cataloging Mod Specifications (`/bg3-document-mods`)

Once candidate mods are selected, the studio automatically downloads, decompresses, and deconstructs community `.pak` files into structured markdown specifications within `$XDG_DOCUMENTS_DIR/BG3_Mod_Studio/Mods/subscribed/`.

### Conversational Examples

- *"Document the mod at https://mod.io/g/baldursgate3/m/unlocklevelcurve."*
- `"/bg3-document-single-mod 4166963"`
- `"/bg3-document-mods 5e-spells unlocklevelcurve extra-gear"`

### Under the Hood: Tool Execution

The orchestrator skill coordinates background subagents running pure-Python extraction:

```bash
# Primary CLI command
bg3 modio extract --mod-id <id-or-slug> --output-dir Mods/subscribed/<slug>

# Direct module execution
uv run -m bg3_core.modio_extract --mod-id <id-or-slug> --output-dir Mods/subscribed/<slug>
```

- **Deconstruction**: Downloads the archive and unpackages Larian XML/LSX and TXT data without external tools (`bg3_core.lspk`).
- **Cataloging**: Extracts spells, statuses, progression nodes, and passives into a standardized `README.md` and appends an entry to `Mods/subscribed/library.md`.
- *Detailed reference*: See [FEATURES.md § 3.6](FEATURES.md#36-library--modio-search-tools-packagesbg3-core).

---

## 4. Tracking Upstream Updates & Account Synchronization

Keep local documentation and subscribed mods synchronized with upstream authors on mod.io.

### Conversational Examples

- `"/bg3-update-mod-documentation"` *(checks all cataloged mods for upstream updates)*
- *"Check if 5e-spells or unlocklevelcurve have new versions on mod.io."*
- *"Synchronize all mods subscribed on my mod.io profile."*

### Under the Hood: Tool Execution

The update skills and synchronization workflows leverage two core tools:

1. **Tracking Upstream Mod Updates**:
   ```bash
   # Check tracked mods against upstream releases
   bg3 modio update --check-only --json
   
   # Or run specific mod update
   bg3 modio update --mod <slug>
   ```
   The skill checks tracked mods against mod.io release timestamps. When an update is detected, it delegates to subagents to download the newest `.pak` and update the local specification.

2. **Syncing Profile Subscriptions**:
   ```bash
   # Synchronize subscriptions and refresh catalog
   bg3 modio sync --download-all --sync-library
   
   # Sync with safe pruning guard
   bg3 modio sync --prune
   ```
   Uses your `MODIO_PAT` to fetch your account subscriptions and ensure your local library reflects your subscribed community content. Includes confirmation guards to prevent unintentional local folder deletions.
- *Detailed reference*: See [FEATURES.md § 3.6](FEATURES.md#36-library--modio-search-tools-packagesbg3-core).

---

## 5. Verifying Compatibility & Mod Conflicts (`/bg3-check-mod-conflicts`)

Before deploying new community mods or when authoring custom creations, the `/bg3-check-mod-conflicts` skill verifies whether two or more mods overwrite identical game assets or require missing prerequisite frameworks.

### Conversational Examples

- `"/bg3-check-mod-conflicts unlocklevelcurve custom-subclass"`
- *"Will this new mod conflict with any mods already in my library?"*
- *"Check if my load order has any conflicting RootTemplates or duplicate stat IDs."*

### Under the Hood: Tool Execution

The skill runs static conflict analysis against cataloged definitions:

```bash
# Primary CLI command
bg3 mod conflict <ModSlug> --against-library --json

# Direct module execution
uv run -m bg3_authoring.diagnostics.check_mod_conflicts --candidate <ModSlug> --against-library --json
```

- **Collision Detection**: Compares unpacked stat records, RootTemplate overrides, and prerequisite frameworks (such as `CompatibilityFramework` or `CommunityLibrary`).
- **Console Validation**: Flags non-compliant assets like native DLL dependencies or Script Extender requirements for console targets.
- *Detailed reference*: See [FEATURES.md § 3.3](FEATURES.md#33-diagnostics--auditing-tools-packagesbg3-authoring).

---

## 6. Curating mod.io Collections (`/bg3-create-modio-collection`)

Easily publish and manage curated collections of community mods on mod.io, derived directly from your documented library.

### Conversational Examples

- `"/bg3-create-modio-collection"`
- *"Create a mod.io collection titled 'Tactician Essentials' with the mods in my library."*
- *"Preview which mods will be added to my mod.io collection."*

### Under the Hood: Tool Execution

The collection curation skill automates collection updates through mod.io REST endpoints:

```bash
# Preview proposed collection additions
bg3 modio create-collection --dry-run

# Commit additions to the active collection
bg3 modio create-collection --title "My Curated BG3 Collection"
```

- **Library Reflection**: Pulls verified mod IDs and slugs directly from `Mods/subscribed/library.md`.
- **Safe Staging**: Supports `--dry-run` to preview remote modifications before mutating live collection data.
- *Detailed reference*: See [FEATURES.md § 3.6](FEATURES.md#36-library--modio-search-tools-packagesbg3-core).
