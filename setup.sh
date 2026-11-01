#!/usr/bin/env bash
# ==============================================================================
# Baldur's Gate 3 Mod Studio & Mod.io Toolkit - Setup Launcher
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${HOME}/.local/bin"

# 1. Verify Python 3 is installed
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but was not found in your PATH." >&2
    echo "Please install Python 3.10+ and re-run this setup script." >&2
    exit 1
fi

# 2. Verify or Install uv
export PATH="${BIN_DIR}:${PATH}"
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${BIN_DIR}:${PATH}"
fi

# 3. Synchronize in-repo workspace dependencies (for development/skills)
echo "Synchronizing workspace packages..."
(cd "${SCRIPT_DIR}" && uv sync)

# 4. Install standalone tools outside repo into ~/.local/bin via uv tool
echo "Installing standalone tools into ${BIN_DIR}..."
uv tool install --editable "${SCRIPT_DIR}/packages/bg3-core" --force

# 5. Deploy bundled agent skills into studio workspace
echo "Installing agent skills into studio workspace..."
uv run --directory "${SCRIPT_DIR}" python3 -m bg3_core.skills_installer || true

# 6. Launch interactive setup wizard
exec uv run --directory "${SCRIPT_DIR}" python3 -m bg3_core.setup_environment "$@"
