# PowerShell Setup Launcher for Windows
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# 1. Verify Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python 3.10+ is required but was not found in PATH."
    exit 1
}

# 2. Verify or Install uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv package manager..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

# 3. Synchronize in-repo workspace dependencies
Write-Host "Synchronizing workspace packages..."
Push-Location $ScriptDir
try {
    uv sync
    # 4. Install standalone tools outside repo
    Write-Host "Installing standalone tools into user environment..."
    uv tool install --editable .\packages\bg3-core --force
    uv tool install --editable .\packages\bg3-theorycraft --force
    uv tool install --editable .\packages\bg3-authoring --force

    # 5. Launch interactive setup wizard
    uv run python -m bg3_core.setup_environment @args
} finally {
    Pop-Location
}
