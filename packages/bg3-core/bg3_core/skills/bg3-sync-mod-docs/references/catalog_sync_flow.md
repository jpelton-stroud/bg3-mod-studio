# Subscription Synchronization & Status Reference

## 1. Syncing Subscriptions
Synchronize community library directly against authenticated mod.io subscriptions:
```bash
# Preview subscription sync without modifications
bg3 modio sync --dry-run --json

# Synchronize and safely prune unsubscribed rows and orphaned folders
bg3 modio sync --prune --json
```

---

## 2. Status Indicators
- `🟢 Up-to-date`: Mod has no pending updates on mod.io.
- `🔄 Updated`: Mod was refreshed to a newer release version.
- `✨ Created`: New mod extracted, validated, and added to library.
- `❌ Failed`: Network, unpack, or API error occurred.
