# Search Criteria, Platform Rules & Formatting Rubric

## 1. Platform Values & Requirements
- `PC` / `Windows`
- `Xbox` / `XboxSeriesX`
- `PlayStation` / `PS5`
- `Console` (Requires dual Xbox and PS5 compatibility)

If target platform is omitted in query, prompt user before searching.

---

## 2. Candidate Presentation Schema

```markdown
| # | Mod Name | Slug | Platforms | Tags | Description |
| :-: | :--- | :--- | :--- | :--- | :--- |
| **1** | **[Mod Name](https://mod.io/g/baldursgate3/m/mod-slug)** | `mod-slug` | `windows`, `xboxseriesx`, `ps5` | Warlock, Classes | Full description of features and mechanics. |
```

---

## 3. Conflict Status Rules
- Clean: `✅ No conflicts found with existing mods`
- Tracked Conflict: `⚠️ Possible conflict found: <Tracked Mod Name> - <Issue>`
- Candidate Conflict: `⚠️ Possible conflict found: <Mod A> vs <Mod B> - <Issue>`
- Console Load Order Lock: Append `[Console Load Order: cannot reorder on console to resolve]`
