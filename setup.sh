#!/usr/bin/env bash
# ==============================================================================
# Baldur's Gate 3 Mod Studio & Mod.io Toolkit - Setup Launcher
# ==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verify Python 3 is installed
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but was not found in your PATH." >&2
    echo "Please install Python 3.10+ and re-run this setup script." >&2
    exit 1
fi

# Ensure ~/.local/bin exists and symlink bg3 CLI entrypoint
mkdir -p "${HOME}/.local/bin"
ln -srf "${SCRIPT_DIR}/scripts/bg3.py" "${HOME}/.local/bin/bg3"

exec python3 "${SCRIPT_DIR}/scripts/management/setup_environment.py" "$@"
