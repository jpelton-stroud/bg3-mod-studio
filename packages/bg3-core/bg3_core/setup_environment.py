#!/usr/bin/env python3
"""
setup_environment.py
--------------------
Interactive setup wizard and environment configuration manager for the
Baldur's Gate 3 Mod Studio & Mod.io Toolkit.

Features:
- Validates and configures .env (written with 0600 permissions) using pure Python standard library.
- Secrets (API key, PAT) are entered via hidden input and never echoed or displayed.
- Tests mod.io API Key against https://api.mod.io/v1/games/3716.
- Tests mod.io Personal Access Token (PAT) against https://api.mod.io/v1/me.
- Detects OS / WSL environment and validates Baldur's Gate 3 Data directory path.
- Configures default mod author identity.
- Detects GitHub CLI (gh) authentication and offers seamless remote repo creation.
- Supports non-interactive status check (--check) and preview (--dry-run).
"""

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from bg3_core.env_paths import (
    REPO_ROOT,
    get_authored_mods_dir,
    get_build_guides_dir,
    get_env_source,
    get_studio_dir,
    get_subscribed_mods_dir,
    get_xdg_cache_home,
    get_xdg_config_home,
    get_xdg_data_home,
    get_xdg_documents_home,
    get_xdg_state_home,
)
from bg3_core.library_catalog import purge_library_mods
from bg3_core.modio_client import BG3_GAME_ID, MODIO_API_HOST, USER_AGENT

WORKSPACE_ROOT = REPO_ROOT
ENV_PATH = get_xdg_config_home() / "env"

# ANSI Terminal Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RED = "\033[31m"
RESET = "\033[0m"


def print_banner() -> None:
    print(f"\n{BOLD}{CYAN}========================================================================{RESET}")
    print(f"{BOLD}{CYAN}      Baldur's Gate 3 Mod Studio & Mod.io Toolkit Setup Wizard          {RESET}")
    print(f"{BOLD}{CYAN}========================================================================{RESET}\n")


def parse_env_file(path: Path) -> dict:
    """Safely parse key-value pairs from an existing .env file."""
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    env[key] = val
    except Exception as e:
        print(f"{YELLOW}Warning: Could not read {path}: {e}{RESET}")
    return env


def detect_default_data_dir() -> str:
    """Determine the most likely Baldur's Gate 3 Data path based on OS/WSL."""
    if os.name == "nt":
        return r"C:\Program Files (x86)\Steam\steamapps\common\Baldurs Gate 3\Data"

    # Check for WSL environment
    is_wsl = False
    proc_version = Path("/proc/version")
    if proc_version.exists():
        try:
            content = proc_version.read_text(encoding="utf-8").lower()
            if "microsoft" in content or "wsl" in content:
                is_wsl = True
        except Exception:
            pass

    if is_wsl or Path("/mnt/c").exists():
        return "/mnt/c/Program Files (x86)/Steam/steamapps/common/Baldurs Gate 3/Data"

    # Native Linux Steam default
    linux_default = Path.home() / ".local/share/Steam/steamapps/common/Baldurs Gate 3/Data"
    return str(linux_default)


def test_modio_api_key(api_key: str) -> tuple[bool, str]:
    """Validate mod.io API key by querying the Baldur's Gate 3 game metadata (ID: 6715)."""
    if not api_key:
        return False, "API key is empty."

    url = f"https://{MODIO_API_HOST}/v1/games/{BG3_GAME_ID}?api_key={urllib.parse.quote(api_key)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                game_name = data.get("name", "Baldur's Gate 3")
                return True, f"Successfully verified access to '{game_name}' on mod.io!"
            return False, f"Unexpected HTTP status {response.status}"
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            msg = err_body.get("error", {}).get("message", e.reason)
        except Exception:
            msg = e.reason
        return False, f"HTTP Error {e.code}: {msg}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def test_modio_pat(api_key: str, pat: str) -> tuple[bool, str]:
    """Validate mod.io Personal Access Token against the /me endpoint."""
    if not pat:
        return False, "PAT is empty."

    url = f"https://{MODIO_API_HOST}/v1/me"
    if api_key:
        url += f"?api_key={urllib.parse.quote(api_key)}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Authorization": f"Bearer {pat}",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                username = data.get("username", "Unknown User")
                return True, f"Successfully authenticated as mod.io user '{username}'!"
            return False, f"Unexpected HTTP status {response.status}"
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode("utf-8"))
            msg = err_body.get("error", {}).get("message", e.reason)
        except Exception:
            msg = e.reason
        return False, f"HTTP Error {e.code}: {msg}"
    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def prompt_input(prompt_text: str, default_val: str = "", allow_empty: bool = True) -> str:
    """Prompt the user for terminal input with a default fallback."""
    suffix = f" [{default_val}]" if default_val else ""
    while True:
        try:
            res = input(f"{BOLD}{prompt_text}{RESET}{suffix}: ").strip()
        except EOFError:
            return default_val
        if res:
            return res
        if default_val or allow_empty:
            return default_val
        print(f"{YELLOW}A non-empty value is required. Please try again.{RESET}")


def mask_secret(value: str) -> str:
    """Return a non-revealing placeholder for a secret value."""
    return "****" if value else ""


def prompt_secret(prompt_text: str, current_val: str = "") -> str:
    """Prompt for a secret without echoing it or displaying the stored value.

    Pressing Enter keeps the current value (if any).
    """
    suffix = " [configured - press Enter to keep]" if current_val else ""
    try:
        res = getpass.getpass(f"{BOLD}{prompt_text}{RESET}{suffix}: ").strip()
    except EOFError:
        return current_val
    return res or current_val


def write_env_file(path: Path, content: str) -> None:
    """Write the environment configuration file readable/writable by the owner only (0600)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    os.chmod(path, 0o600)  # O_CREAT mode is ignored for pre-existing files


def check_environment_status(as_json: bool = False, config_path: Optional[Path] = None) -> None:
    """Non-interactive check of project environment configuration and XDG paths."""
    target_env = config_path or ENV_PATH
    cfg_home = get_xdg_config_home()
    cache_home = get_xdg_cache_home()
    data_home = get_xdg_data_home()
    state_home = get_xdg_state_home()
    legacy_env = WORKSPACE_ROOT / ".env"

    # Auto-migrate legacy repository .env if target doesn't exist
    if not target_env.is_file() and legacy_env.is_file():
        try:
            write_env_file(target_env, legacy_env.read_text(encoding="utf-8"))
            legacy_env.unlink()
        except OSError:
            pass

    if not target_env.is_file():
        xdg_info = {
            "config_home": str(cfg_home),
            "cache_home": str(cache_home),
            "data_home": str(data_home),
            "state_home": str(state_home),
            "config_file": str(target_env),
            "config_exists": False,
        }
        if as_json:
            print(json.dumps({
                "env_path": str(target_env),
                "configured": False,
                "error": f"No environment configuration found at {target_env}.",
                "xdg": xdg_info,
            }, indent=2))
        else:
            print(f"\n{BOLD}=== Environment Configuration Status ==={RESET}")
            print(f"{YELLOW}[!] No configuration found at {target_env}. Run './setup.sh' to configure.{RESET}")
            print(f"XDG_CONFIG_HOME:  {cfg_home}")
            print(f"XDG_CACHE_HOME:   {cache_home}")
            print(f"XDG_DATA_HOME:    {data_home}")
            print(f"XDG_STATE_HOME:   {state_home}\n")
        return

    env = parse_env_file(target_env)
    api_key = env.get("MODIO_API_KEY", "")
    pat = env.get("MODIO_PAT", env.get("MODIO_OAUTH_TOKEN", ""))
    data_dir = env.get("BG3_DATA_DIR", "")
    author = env.get("BG3_MOD_AUTHOR", "")
    data_dir_exists = Path(data_dir).exists() if data_dir else False

    studio_dir = env.get("BG3_STUDIO_DIR", str(get_studio_dir(target_env)))
    studio_dir_exists = Path(studio_dir).exists() if studio_dir else False
    build_guides_dir = env.get("BG3_BUILD_GUIDES_DIR", str(get_build_guides_dir(target_env)))
    build_guides_dir_exists = Path(build_guides_dir).exists() if build_guides_dir else False
    subscribed_mods_dir = env.get(
        "BG3_SUBSCRIBED_MODS_DIR",
        env.get("BG3_LIBRARY_DIR", str(get_subscribed_mods_dir(target_env))),
    )
    subscribed_mods_dir_exists = Path(subscribed_mods_dir).exists() if subscribed_mods_dir else False
    authored_mods_dir = env.get(
        "BG3_AUTHORED_MODS_DIR",
        env.get("BG3_MODS_DIR", str(get_authored_mods_dir(target_env))),
    )
    authored_mods_dir_exists = Path(authored_mods_dir).exists() if authored_mods_dir else False

    _, key_source = get_env_source("MODIO_API_KEY", target_env)
    _, pat_source = get_env_source("MODIO_PAT", target_env)

    xdg_info = {
        "config_home": str(cfg_home),
        "cache_home": str(cache_home),
        "data_home": str(data_home),
        "state_home": str(state_home),
        "config_file": str(target_env),
        "config_exists": True,
    }

    if as_json:
        result = {
            "env_path": str(target_env),
            "configured": True,
            "modio_api_key_configured": bool(api_key),
            "modio_pat_configured": bool(pat),
            "bg3_data_dir": data_dir,
            "bg3_data_dir_exists": data_dir_exists,
            "bg3_mod_author": author or "default",
            "bg3_studio_dir": studio_dir,
            "bg3_studio_dir_exists": studio_dir_exists,
            "bg3_build_guides_dir": build_guides_dir,
            "bg3_build_guides_dir_exists": build_guides_dir_exists,
            "bg3_subscribed_mods_dir": subscribed_mods_dir,
            "bg3_subscribed_mods_dir_exists": subscribed_mods_dir_exists,
            "bg3_authored_mods_dir": authored_mods_dir,
            "bg3_authored_mods_dir_exists": authored_mods_dir_exists,
            "xdg": xdg_info,
        }
        print(json.dumps(result, indent=2))
        return

    print(f"\n{BOLD}=== Environment Configuration Status ==={RESET}")
    print(f"Config file:      {target_env}")
    print(f"XDG_CONFIG_HOME:  {cfg_home}")
    print(f"XDG_CACHE_HOME:   {cache_home}")
    print(f"XDG_DATA_HOME:    {data_home}")
    print(f"XDG_STATE_HOME:   {state_home}")
    print(f"MODIO_API_KEY:    {'Configured (' + api_key[:4] + '***) [' + key_source + ']' if api_key else RED + 'Missing' + RESET}")
    print(f"MODIO_PAT:        {'Configured (***) [' + pat_source + ']' if pat else YELLOW + 'Not set (Optional)' + RESET}")
    print(f"BG3_DATA_DIR:     {data_dir if data_dir else RED + 'Missing' + RESET}")
    if data_dir:
        status_text = f"{GREEN}Exists{RESET}" if data_dir_exists else f"{YELLOW}Not found on disk{RESET}"
        print(f"  └ Directory:    {status_text}")
    print(f"BG3_MOD_AUTHOR:   {author if author else 'default'}")
    print(f"BG3_STUDIO_DIR:   {studio_dir if studio_dir else YELLOW + 'Default' + RESET}")
    if studio_dir:
        s_status = f"{GREEN}Exists{RESET}" if studio_dir_exists else f"{YELLOW}Not found on disk{RESET}"
        print(f"  └ Studio Root:  {s_status}")
    print("")


def configure_github_remote(non_interactive: bool = False) -> None:
    """Optionally configure a GitHub remote repository using GitHub CLI."""
    if non_interactive:
        return

    # Check if git is initialized
    if not (WORKSPACE_ROOT / ".git").is_dir():
        return

    # Check if a remote origin already exists
    res = subprocess.run(["git", "remote"], cwd=WORKSPACE_ROOT, capture_output=True, text=True)
    if "origin" in res.stdout.splitlines():
        return

    gh_bin = shutil.which("gh")
    if not gh_bin:
        return

    # Check gh auth status
    auth_check = subprocess.run([gh_bin, "auth", "status"], capture_output=True, text=True)
    if auth_check.returncode != 0:
        return

    print(f"\n{BOLD}{CYAN}------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}GitHub Remote Configuration{RESET}")
    print("GitHub CLI (`gh`) is authenticated and no remote repository is configured for this workspace.")
    choice = prompt_input("Would you like to create and link a remote GitHub repository now? (y/n)", "n").lower()
    if choice not in ("y", "yes"):
        return

    repo_name = prompt_input("Repository name", WORKSPACE_ROOT.name)
    visibility_choice = prompt_input("Visibility (private/public)", "private").lower()
    vis_flag = "--public" if visibility_choice in ("public", "pub") else "--private"

    print(f"Creating GitHub repository '{repo_name}' ({vis_flag})...")
    cmd = [gh_bin, "repo", "create", repo_name, "--source=.", "--remote=origin", vis_flag]
    result = subprocess.run(cmd, cwd=WORKSPACE_ROOT, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{GREEN}✓ Successfully created and linked remote 'origin'!{RESET}")
        push_choice = prompt_input("Push current branch 'main' to origin? (y/n)", "y").lower()
        if push_choice in ("y", "yes"):
            push_res = subprocess.run(
                ["git", "push", "-u", "origin", "main"],
                cwd=WORKSPACE_ROOT,
                capture_output=True,
                text=True,
            )
            if push_res.returncode == 0:
                print(f"{GREEN}✓ Branch pushed to remote successfully!{RESET}")
            else:
                print(f"{YELLOW}Notice: Push output:\n{push_res.stderr.strip()}{RESET}")
    else:
        print(f"{YELLOW}Remote creation skipped: {result.stderr.strip()}{RESET}")


def prompt_subscription_sync(non_interactive: bool = False) -> str:
    """Prompt user for modio_sync subscription synchronization action.

    Returns the selected choice: '1', '2', '3', or '4'.
    """
    if non_interactive:
        return "3"

    print(f"\n{BOLD}{CYAN}------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}5. mod.io Subscription Sync & Library Management{RESET}")
    print("Would you like to run `modio_sync` now to sync your existing subscriptions?")
    print("  1) Yes, sync my existing subscriptions and prune mods to which I'm not subscribed [Default]")
    print("  2) Yes, sync my existing subscriptions, but *don't* prune")
    print("  3) No, don't sync my subscriptions now")
    print("  4) No, and purge any mods currently listed in `mods/library.md`")

    while True:
        try:
            choice = input(f"{BOLD}Select an option [1-4, default: 1]{RESET}: ").strip()
        except EOFError:
            return "3" if non_interactive else "1"
        if not choice:
            return "1"
        if choice in ("1", "2", "3", "4"):
            return choice
        print(f"{YELLOW}Please enter 1, 2, 3, or 4 (or press Enter for default 1).{RESET}")


def handle_subscription_sync(choice: str, dry_run: bool = False) -> None:
    """Execute the selected subscription sync or library purge action."""
    if choice == "1":
        print(f"\n{CYAN}Running subscription sync with pruning (--prune)...{RESET}")
        cmd = [sys.executable, "-m", "bg3_core.modio_sync", "--prune"]
        if dry_run:
            print(f"{CYAN}[DRY-RUN] Would run: {' '.join(cmd)}{RESET}")
        else:
            subprocess.run(cmd, cwd=WORKSPACE_ROOT)

    elif choice == "2":
        print(f"\n{CYAN}Running subscription sync without pruning...{RESET}")
        cmd = [sys.executable, "-m", "bg3_core.modio_sync"]
        if dry_run:
            print(f"{CYAN}[DRY-RUN] Would run: {' '.join(cmd)}{RESET}")
        else:
            subprocess.run(cmd, cwd=WORKSPACE_ROOT)

    elif choice == "3":
        print("Continuing setup without subscription sync.")

    elif choice == "4":
        print(f"\n{YELLOW}Purging all mods currently found in mods/ and resetting mods/library.md...{RESET}")
        result = purge_library_mods(dry_run=dry_run)
        mode_prefix = f"{CYAN}[DRY-RUN] {RESET}" if dry_run else ""
        print(f"{mode_prefix}{GREEN}✓ Purged {result['purged_count']} mod folder(s) and reset library.md.{RESET}")


def prompt_custom_mods_purge(non_interactive: bool = False) -> str:
    """Prompt user for purging custom mods currently residing in my_mods/.

    Returns 'y' or 'n'.
    """
    if non_interactive:
        return "n"

    print(f"\n{BOLD}{CYAN}------------------------------------------------------------------------{RESET}")
    print(f"{BOLD}6. Custom Mods Cleanup{RESET}")
    while True:
        try:
            choice = input(
                f"{BOLD}Would you like to purge custom mods currently residing in the `my_mods/` folder? (Y/n){RESET} [Y]: "
            ).strip().lower()
        except EOFError:
            return "n" if non_interactive else "y"
        if not choice or choice in ("y", "yes"):
            return "y"
        if choice in ("n", "no"):
            return "n"
        print(f"{YELLOW}Please enter 'y' or 'n' (or press Enter for default Y).{RESET}")


def handle_custom_mods_purge(choice: str, dry_run: bool = False) -> None:
    """Purge custom mods residing in my_mods/ folder."""
    if choice != "y":
        print("Continuing without purging custom mods.")
        return

    my_mods_dir = WORKSPACE_ROOT / "my_mods"
    if dry_run:
        print(f"{CYAN}[DRY-RUN] Would purge custom mods in {my_mods_dir} (rm -rf my_mods/*){RESET}")
        return

    print(f"Purging custom mods residing in {my_mods_dir}...")
    if my_mods_dir.is_dir():
        for child in sorted(my_mods_dir.iterdir()):
            try:
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            except Exception as e:
                print(f"{YELLOW}Warning: Could not remove {child}: {e}{RESET}")
    print(f"{GREEN}✓ Successfully purged custom mods in my_mods/.{RESET}")


def run_wizard(
    dry_run: bool = False,
    non_interactive: bool = False,
    config_path: Optional[Path] = None,
    studio_dir_override: Optional[str] = None,
) -> None:
    print_banner()

    target_env = config_path or ENV_PATH
    existing_env = parse_env_file(target_env)
    if not existing_env and (WORKSPACE_ROOT / ".env").is_file():
        existing_env = parse_env_file(WORKSPACE_ROOT / ".env")
        print(f"{YELLOW}[!] Detected legacy repository-level .env. Migrating values to {target_env}.{RESET}")

    default_data_dir = detect_default_data_dir()
    default_studio_dir = str(get_xdg_documents_home() / "BG3_Mod_Studio")

    if non_interactive:
        api_key = existing_env.get("MODIO_API_KEY", "")
        pat = existing_env.get("MODIO_PAT", existing_env.get("MODIO_OAUTH_TOKEN", ""))
        data_dir = existing_env.get("BG3_DATA_DIR", default_data_dir)
        author = existing_env.get("BG3_MOD_AUTHOR", "default")
        studio_dir = studio_dir_override or existing_env.get("BG3_STUDIO_DIR", default_studio_dir)
    else:
        # 1. MODIO_API_KEY
        print(f"{BOLD}1. mod.io API Key{RESET}")
        print("Required for searching, downloading, and cataloging BG3 mods from mod.io.")
        print("Get your API key at: https://mod.io/me/access")
        current_key = existing_env.get("MODIO_API_KEY", "")
        api_key = prompt_secret("Enter MODIO_API_KEY (input hidden)", current_key)

        if api_key:
            test_now = prompt_input("Test this API key live against mod.io? (Y/n)", "y").lower()
            if test_now in ("y", "yes", ""):
                print("Connecting to mod.io API...")
                success, msg = test_modio_api_key(api_key)
                if success:
                    print(f"{GREEN}✓ {msg}{RESET}")
                else:
                    print(f"{RED}✗ Verification issue: {msg}{RESET}")
                    keep = prompt_input("Do you want to keep this key anyway? (y/n)", "y").lower()
                    if keep not in ("y", "yes"):
                        api_key = prompt_secret("Re-enter MODIO_API_KEY (input hidden)")

        # 2. MODIO_PAT
        print(f"\n{BOLD}2. mod.io Personal Access Token (PAT) [Optional]{RESET}")
        print("Optional token required for account actions such as subscribing/syncing mods.")
        print("Generate a PAT at: https://mod.io/me/access")
        current_pat = existing_env.get("MODIO_PAT", existing_env.get("MODIO_OAUTH_TOKEN", ""))
        pat = prompt_secret("Enter MODIO_PAT (input hidden, press Enter to skip)", current_pat)

        if pat:
            test_pat_choice = prompt_input("Test this PAT live against mod.io? (Y/n)", "y").lower()
            if test_pat_choice in ("y", "yes", ""):
                print("Verifying PAT credentials...")
                success, msg = test_modio_pat(api_key, pat)
                if success:
                    print(f"{GREEN}✓ {msg}{RESET}")
                else:
                    print(f"{YELLOW}✗ PAT issue: {msg}{RESET}")

        # 3. BG3_DATA_DIR
        print(f"\n{BOLD}3. Baldur's Gate 3 Data Directory{RESET}")
        print("Path to the game's Data directory (used to live-sync your custom mods into BG3).")
        current_data_dir = existing_env.get("BG3_DATA_DIR", default_data_dir)
        data_dir = prompt_input("Enter BG3_DATA_DIR", current_data_dir)

        target_path = Path(data_dir)
        if not target_path.exists():
            print(f"{YELLOW}Notice: Path does not exist currently: {target_path}{RESET}")
            print("This is normal if the game is installed in a custom library or not currently mounted.")
            confirm = prompt_input("Keep this path? (Y/n)", "y").lower()
            if confirm not in ("y", "yes", ""):
                data_dir = prompt_input("Re-enter BG3_DATA_DIR", default_data_dir)
        else:
            print(f"{GREEN}✓ Found directory on disk: {target_path}{RESET}")

        # 4. BG3_MOD_AUTHOR
        print(f"\n{BOLD}4. Default Mod Author Identity{RESET}")
        print("Default author name stamped into meta.lsx when generating new mod scaffolds.")
        current_author = existing_env.get("BG3_MOD_AUTHOR", "default")
        author = prompt_input("Enter default BG3_MOD_AUTHOR (leave blank or 'default')", current_author)
        if not author:
            author = "default"

        # 5. BG3_STUDIO_DIR
        print(f"\n{BOLD}5. BG3 Mod Studio Target Directory{RESET}")
        print("Root directory where all user-generated content (build guides, subscribed mods, authored mods) is stored.")
        current_studio_dir = studio_dir_override or existing_env.get("BG3_STUDIO_DIR", default_studio_dir)
        studio_dir = prompt_input("Enter target directory for BG3_Mod_Studio", current_studio_dir)

    studio_path = Path(os.path.expandvars(os.path.expanduser(studio_dir.strip())))

    # Assemble output
    output_lines = [
        "# ==============================================================================",
        "# Baldur's Gate 3 Mod Studio & Mod.io Toolkit - Environment Variables",
        f"# Generated by setup_environment.py at {target_env}",
        "# ==============================================================================",
        "",
        "# mod.io API Credentials",
        f"MODIO_API_KEY={api_key}",
        f"MODIO_PAT={pat}",
        "",
        "# Baldur's Gate 3 Game Paths",
        f"BG3_DATA_DIR={data_dir}",
        "",
        "# Mod Author Metadata",
        f"BG3_MOD_AUTHOR={author}",
        "",
        "# BG3 Mod Studio User Content Directory",
        f"BG3_STUDIO_DIR={studio_path}",
        "",
    ]
    content = "\n".join(output_lines)

    if dry_run:
        print(f"\n{CYAN}[DRY-RUN] Would write to {target_env} (secrets masked):{RESET}")
        print(content.replace(f"MODIO_API_KEY={api_key}", f"MODIO_API_KEY={mask_secret(api_key)}")
                     .replace(f"MODIO_PAT={pat}", f"MODIO_PAT={mask_secret(pat)}"))
        print(f"{CYAN}[DRY-RUN] Would scaffold directories under {studio_path}:{RESET}")
        print(f"  - {studio_path / 'Build_Guides'}")
        print(f"  - {studio_path / 'Mods' / 'subscribed'}")
        print(f"  - {studio_path / 'Mods' / 'authored'}")
        print(f"  - {studio_path / '.agents' / 'skills'}")
    else:
        write_env_file(target_env, content)
        print(f"\n{GREEN}✓ Environment configuration saved successfully to {target_env} (mode 600)!{RESET}")
        legacy_file = WORKSPACE_ROOT / ".env"
        if legacy_file.is_file():
            try:
                legacy_file.unlink()
                print(f"{GREEN}✓ Removed deprecated repository-level .env file.{RESET}")
            except OSError:
                pass

        (studio_path / "Build_Guides").mkdir(parents=True, exist_ok=True)
        (studio_path / "Mods" / "subscribed").mkdir(parents=True, exist_ok=True)
        (studio_path / "Mods" / "authored").mkdir(parents=True, exist_ok=True)
        (studio_path / ".agents" / "skills").mkdir(parents=True, exist_ok=True)
        print(f"{GREEN}✓ Ensured studio directories exist at {studio_path}.{RESET}")

        # Deploy bundled agent skills into studio workspace
        try:
            from bg3_core.skills_installer import install_agent_skills
            skill_res = install_agent_skills(target_dir=studio_path / ".agents" / "skills")
            count = len(skill_res.get("installed", [])) + len(skill_res.get("updated", []))
            print(f"{GREEN}✓ Deployed {count} agent skills to {studio_path / '.agents' / 'skills'}.{RESET}")
        except Exception as e:
            print(f"{YELLOW}Warning: Could not install agent skills: {e}{RESET}")

    # GitHub Remote Setup
    configure_github_remote()

    # 5. mod.io Subscription Sync & Library Management
    sync_choice = prompt_subscription_sync(non_interactive=non_interactive)
    handle_subscription_sync(sync_choice, dry_run=dry_run)

    # 6. Custom Mods Cleanup
    purge_choice = prompt_custom_mods_purge(non_interactive=non_interactive)
    handle_custom_mods_purge(purge_choice, dry_run=dry_run)

    print(f"\n{BOLD}{GREEN}Setup completed successfully!{RESET}")
    print("You can run `./setup.sh --check` anytime to review your configuration.")
    print("Run `bg3 --help` to get started.\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BG3 Mod Studio & Mod.io Toolkit Environment Setup Wizard"
    )
    parser.add_argument(
        "--check",
        "--check-only",
        dest="check",
        action="store_true",
        help="Check and display current environment configuration without prompting",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Custom configuration file path (defaults to $XDG_CONFIG_HOME/bg3/env)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output check results as JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run setup wizard in preview mode without writing to disk",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run wizard non-interactively with safe default answers (no-sync, no-purge)",
    )
    parser.add_argument(
        "--studio-dir",
        type=str,
        default=None,
        help="Target directory for BG3 Mod Studio user content (defaults to XDG_DOCUMENTS_DIR/BG3_Mod_Studio)",
    )
    args = parser.parse_args()

    if args.check:
        check_environment_status(as_json=args.json, config_path=args.config)
    else:
        run_wizard(
            dry_run=args.dry_run,
            non_interactive=args.non_interactive,
            config_path=args.config,
            studio_dir_override=args.studio_dir,
        )


if __name__ == "__main__":
    main()

