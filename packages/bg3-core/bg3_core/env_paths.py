"""Shared environment variable, workspace path, and mod directory resolution utilities."""

import glob
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
DIST_DIR = REPO_ROOT / "dist"

DEFAULT_WSL_DATA_DIR = Path("/mnt/c/Program Files (x86)/Steam/steamapps/common/Baldurs Gate 3/Data")
DEFAULT_WIN_DATA_DIR = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Baldurs Gate 3\Data")


def get_xdg_config_home(app: str = "bg3") -> Path:
    """Return configuration directory adhering to XDG Base Directory Specification."""
    val = os.environ.get("XDG_CONFIG_HOME")
    if val and val.strip():
        base = Path(val.strip())
    elif os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata and appdata.strip() else Path.home() / "AppData" / "Roaming"
    else:
        base = Path.home() / ".config"
    return base / app


def get_xdg_cache_home(app: str = "bg3") -> Path:
    """Return cache directory adhering to XDG Base Directory Specification."""
    val = os.environ.get("XDG_CACHE_HOME")
    if val and val.strip():
        base = Path(val.strip())
    elif os.name == "nt":
        localapp = os.environ.get("LOCALAPPDATA")
        base = Path(localapp) if localapp and localapp.strip() else Path.home() / "AppData" / "Local"
        return base / app / "cache"
    else:
        base = Path.home() / ".cache"
    return base / app


def get_xdg_data_home(app: str = "bg3") -> Path:
    """Return application data directory adhering to XDG Base Directory Specification."""
    val = os.environ.get("XDG_DATA_HOME")
    if val and val.strip():
        base = Path(val.strip())
    elif os.name == "nt":
        localapp = os.environ.get("LOCALAPPDATA")
        base = Path(localapp) if localapp and localapp.strip() else Path.home() / "AppData" / "Local"
        return base / app / "data"
    else:
        base = Path.home() / ".local" / "share"
    return base / app


def get_xdg_state_home(app: str = "bg3") -> Path:
    """Return state/session directory adhering to XDG Base Directory Specification."""
    val = os.environ.get("XDG_STATE_HOME")
    if val and val.strip():
        base = Path(val.strip())
    elif os.name == "nt":
        localapp = os.environ.get("LOCALAPPDATA")
        base = Path(localapp) if localapp and localapp.strip() else Path.home() / "AppData" / "Local"
        return base / app / "state"
    else:
        base = Path.home() / ".local" / "state"
    return base / app


def get_xdg_documents_home() -> Path:
    """Return user documents directory adhering to XDG user-dirs or platform defaults."""
    val = os.environ.get("XDG_DOCUMENTS_DIR")
    if val and val.strip():
        expanded = os.path.expandvars(os.path.expanduser(val.strip()))
        return Path(expanded)
    if os.name != "nt":
        user_dirs_file = Path.home() / ".config" / "user-dirs.dirs"
        if user_dirs_file.is_file():
            try:
                for line in user_dirs_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("XDG_DOCUMENTS_DIR="):
                        raw_path = line.split("=", 1)[1].strip().strip('"')
                        raw_path = raw_path.replace("$HOME", str(Path.home()))
                        if raw_path:
                            return Path(os.path.expandvars(os.path.expanduser(raw_path)))
            except OSError:
                pass
    return Path.home() / "Documents"


def get_cache_dir() -> Path:
    """Resolve active cache directory, honoring BG3_CACHE_DIR or XDG_CACHE_HOME."""
    custom = os.environ.get("BG3_CACHE_DIR")
    if custom and custom.strip():
        return Path(custom.strip())
    return get_xdg_cache_home()


CACHE_DIR = get_xdg_cache_home()


def load_env_file(env_path: Optional[Path] = None) -> Dict[str, str]:
    """Load key-value pairs from XDG config or explicit env_path. In-repo .env is strictly ignored."""
    env: Dict[str, str] = {}
    candidates = [env_path] if env_path else [
        get_xdg_config_home() / "env",
        Path.home() / ".config" / "modio" / "env",
    ]
    for path in candidates:
        if path and path.is_file():
            try:
                for raw_line in path.read_text(encoding="utf-8").splitlines():
                    line = raw_line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, val = line.split("=", 1)
                        key = key.strip()
                        val = val.strip().strip("'\"")
                        if key not in env:
                            env[key] = val
            except OSError:
                pass
    return env


def get_env_var(key: str, default: Optional[str] = None, env_path: Optional[Path] = None) -> Optional[str]:
    """Retrieve a configuration value from os.environ or XDG config files."""
    val = os.environ.get(key)
    if val is not None and val.strip():
        return val.strip()
    file_vars = load_env_file(env_path)
    return file_vars.get(key, default)


def get_env_source(key: str, env_path: Optional[Path] = None) -> Tuple[Optional[str], str]:
    """Retrieve key value and the origin source where it was resolved."""
    val = os.environ.get(key)
    if val is not None and val.strip():
        return val.strip(), "environment"
    file_vars = load_env_file(env_path)
    if key in file_vars:
        if env_path and env_path.is_file():
            return file_vars[key], str(env_path)
        primary = get_xdg_config_home() / "env"
        if primary.is_file() and key in load_env_file(primary):
            return file_vars[key], str(primary)
        return file_vars[key], "xdg config"
    return None, "unset"


def get_studio_dir(env_path: Optional[Path] = None) -> Path:
    """Resolve active BG3 Mod Studio root directory."""
    custom = get_env_var("BG3_STUDIO_DIR", env_path=env_path)
    if custom and custom.strip():
        return Path(os.path.expandvars(os.path.expanduser(custom.strip())))
    return get_xdg_documents_home() / "BG3_Mod_Studio"


def get_build_guides_dir(env_path: Optional[Path] = None) -> Path:
    """Resolve build guides directory."""
    custom = get_env_var("BG3_BUILD_GUIDES_DIR", env_path=env_path)
    if custom and custom.strip():
        return Path(os.path.expandvars(os.path.expanduser(custom.strip())))
    studio_dir = get_studio_dir(env_path=env_path)
    return studio_dir / "Build_Guides"


def get_subscribed_mods_dir(env_path: Optional[Path] = None) -> Path:
    """Resolve subscribed/community mods directory."""
    custom = get_env_var("BG3_SUBSCRIBED_MODS_DIR", env_path=env_path) or get_env_var(
        "BG3_LIBRARY_DIR", env_path=env_path
    )
    if custom and custom.strip():
        return Path(os.path.expandvars(os.path.expanduser(custom.strip())))
    studio_dir = get_studio_dir(env_path=env_path)
    studio_subscribed = studio_dir / "Mods" / "subscribed"
    if not studio_subscribed.exists() and (REPO_ROOT / "mods").is_dir():
        return REPO_ROOT / "mods"
    return studio_subscribed


def get_authored_mods_dir(env_path: Optional[Path] = None) -> Path:
    """Resolve authored/custom mods directory."""
    custom = get_env_var("BG3_AUTHORED_MODS_DIR", env_path=env_path) or get_env_var(
        "BG3_MODS_DIR", env_path=env_path
    )
    if custom and custom.strip():
        return Path(os.path.expandvars(os.path.expanduser(custom.strip())))
    studio_dir = get_studio_dir(env_path=env_path)
    studio_authored = studio_dir / "Mods" / "authored"
    if not studio_authored.exists() and (REPO_ROOT / "my_mods").is_dir():
        return REPO_ROOT / "my_mods"
    return studio_authored


STUDIO_DIR = get_studio_dir()
MY_MODS_DIR = get_authored_mods_dir()
MODS_DIR = get_subscribed_mods_dir()
BUILD_GUIDES_DIR = get_build_guides_dir()


def normalize_mod_key(value: str) -> str:
    """Normalize a mod slug, folder name, or UUID-suffixed folder name for matching."""
    cleaned = value.strip()
    # Strip trailing _<UUID> if passed a Larian folder name like PaladinsCall_7f92e4b1-82d3-4a16-9cf8-61d5302e1a90
    cleaned = re.sub(
        r"_[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        "",
        cleaned,
    )
    return re.sub(r"[^a-z0-9]", "", cleaned.casefold())


def resolve_mod_dir(
    identifier: str,
    roots: Optional[Sequence[Path]] = None,
    allow_substring: bool = True,
    prefer_my_mods: Optional[bool] = None,
) -> Optional[Path]:
    """Resolve a mod directory across my_mods/ and mods/ by path, slug, Name, or <ModName>_<UUID>."""
    if roots is None:
        my_mods = get_authored_mods_dir()
        mods = get_subscribed_mods_dir()
        roots = (my_mods, mods)

    if prefer_my_mods is not None:
        roots = (roots[0], roots[1]) if prefer_my_mods else (roots[1], roots[0])

    if not identifier or not identifier.strip():
        if prefer_my_mods is not None:
            raise FileNotFoundError(f"Mod directory not found: '{identifier}'")
        return None

    direct = Path(identifier)
    if direct.is_dir():
        return direct.resolve()

    query_raw = identifier.strip()
    query_norm = normalize_mod_key(query_raw)

    # 1. Exact directory name or normalized name match
    for root in roots:
        if not root.is_dir():
            continue
        exact = root / query_raw
        if exact.is_dir():
            return exact.resolve()

        for child in sorted(root.iterdir()):
            if not child.is_dir():
                continue
            if normalize_mod_key(child.name) == query_norm:
                return child.resolve()
            # Also check internal Mods/<ModName>_<UUID> or Projects/<ModName>_<UUID> folder names
            for sub in ("Mods", "Projects", "Public"):
                sub_dir = child / sub
                if sub_dir.is_dir():
                    for mod_folder in sub_dir.iterdir():
                        if mod_folder.is_dir() and (
                            mod_folder.name.casefold() == query_raw.casefold()
                            or normalize_mod_key(mod_folder.name) == query_norm
                        ):
                            return child.resolve()

    # 2. Substring match fallback if allowed
    if allow_substring and query_norm:
        for root in roots:
            if not root.is_dir():
                continue
            for child in sorted(root.iterdir()):
                if child.is_dir() and query_norm in normalize_mod_key(child.name):
                    return child.resolve()

    if prefer_my_mods is not None:
        raise FileNotFoundError(f"Mod directory not found: '{identifier}'")
    return None


def detect_bg3_appdata_dirs() -> List[Path]:
    """Return candidate Baldur's Gate 3 AppData base directories across Linux/WSL/Windows/macOS."""
    candidates: List[Path] = []
    home = Path.home()

    if os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            candidates.append(Path(local_app) / "Larian Studios" / "Baldur's Gate 3")
        candidates.append(home / "AppData" / "Local" / "Larian Studios" / "Baldur's Gate 3")

    # WSL /mnt/c/Users/* detection
    for wsl_match in sorted(glob.glob("/mnt/c/Users/*/AppData/Local/Larian Studios/Baldur's Gate 3")):
        candidates.append(Path(wsl_match))

    # Linux Steam Proton prefix
    candidates.append(
        home
        / ".steam/steam/steamapps/compatdata/1086940/pfx/drive_c/users/steamuser/AppData/Local/Larian Studios/Baldur's Gate 3"
    )
    candidates.append(
        home
        / ".local/share/Steam/steamapps/compatdata/1086940/pfx/drive_c/users/steamuser/AppData/Local/Larian Studios/Baldur's Gate 3"
    )
    # macOS
    candidates.append(home / "Documents" / "Larian Studios" / "Baldur's Gate 3")

    return candidates


def detect_data_dir() -> Path:
    """Detect the Baldur's Gate 3 Data directory from env or platform defaults."""
    configured = get_env_var("BG3_DATA_DIR")
    if configured:
        return Path(configured)
    if os.name == "nt":
        return DEFAULT_WIN_DATA_DIR
    return DEFAULT_WSL_DATA_DIR
