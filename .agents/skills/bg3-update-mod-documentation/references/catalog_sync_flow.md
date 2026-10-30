# Subscription Synchronization & Status Reference

## 1. Syncing Subscriptions
Synchronize community library directly against authenticated mod.io subscriptions:
```bash
# Preview subscription sync without modifications
uv run bg3 modio sync --dry-run --json

# Synchronize and safely prune unsubscribed rows and orphaned folders
uv run bg3 modio sync --prune --json
```

---

## 2. Status Indicators
- `🟢 Up-to-date`: Mod has no pending updates on mod.io.
- `🔄 Updated`: Mod was refreshed to a newer release version.
- `⚠️ Not Tracked`: Mod was not found in `mods/library.md`.
- `❌ Failed`: Network, unpack, or API error occurred.
