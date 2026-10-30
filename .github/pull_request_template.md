## Description

Provide a brief description of the changes introduced by this pull request.

## Type of Change

- [ ] New feature / automation tool
- [ ] Bug fix
- [ ] Mod library catalog update (`Mods/subscribed/` and `Mods/subscribed/library.md`)
- [ ] Custom mod development (`Mods/authored/`)
- [ ] Documentation improvement
- [ ] Tooling or configuration maintenance

## Verification

Please check the verification steps performed:

- [ ] Unit tests passed: `uv run python -m unittest discover tests`
- [ ] Tool registry verified: `uv run bg3 tools verify --audit-skills`
- [ ] Linting & static analysis passed: `uv run ruff check packages/ tests/`
- [ ] Secrets verified as untracked in `$XDG_CONFIG_HOME/bg3/env` via `git status`

## Related Issues

Closes #
