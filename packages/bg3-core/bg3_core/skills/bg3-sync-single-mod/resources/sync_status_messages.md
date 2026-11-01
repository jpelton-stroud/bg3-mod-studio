# Synchronized Status Message Schema

Standardized return messages emitted by worker subagents executing `bg3-sync-single-mod`:

## 1. Up-to-Date
When local mod release hash matches the latest upstream release on mod.io:
```text
<mod-slug>: No updates found (current version: v<version>)
```

## 2. Updated
When a new upstream release was downloaded, unpacked, and specifications refreshed:
```text
<mod-slug>: Documentation updated to v<version> — <Brief summary of updated stats, spells, or features>
```

## 3. Created (New Mod Ingestion)
When a new mod was downloaded, unpacked, and documented into `library.md`:
```text
<mod-slug>: Successfully added to library — <Brief description of implemented mod mechanics>
```

## 4. Failed
When mod download, archive unpacking, or parsing fails:
```text
<mod-slug>: Failed: <Specific error description, e.g. Invalid MODIO_API_KEY, Corrupt LSPK archive>
```
