# Subscription Synchronization & Status Reference

## 1. Syncing Subscriptions
Synchronize community library directly against authenticated mod.io subscriptions:
```bash
# Preview subscription sync without modifications
python3 scripts/bg3.py modio sync --dry-run --json

# Synchronize and safely prune unsubscribed rows and orphaned folders
python3 scripts/bg3.py modio sync --prune --json
```

---

## 2. Status Indicators
- `🟢 Up-to-date`: Mod has no pending updates on mod.io.
- `🔄 Updated`: Mod was refreshed to a newer release version.
- `⚠️ Not Tracked`: Mod was not found in `mods/library.md`.
- `❌ Failed`: Network, unpack, or API error occurred.
