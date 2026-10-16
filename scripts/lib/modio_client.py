"""Shared mod.io REST API client, credentials lookup, and mod query/download utilities."""

import json
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, Optional, Sequence, Tuple

from .env_paths import get_env_var

BG3_GAME_ID = 6715
MODIO_API_HOST = f"g-{BG3_GAME_ID}.modapi.io"
API_ROOT = f"https://{MODIO_API_HOST}/v1"
USER_AGENT = "BG3ModStudio/1.0"


class ModioError(RuntimeError):
    """Raised for an invalid target, preflight failure, or mod.io API error."""


class ModioClient:
    """Authenticated mod.io v1 REST client supporting GET, form-urlencoded, and multipart POST/PUT."""

    def __init__(self, token: str, opener: Any = urllib.request.urlopen) -> None:
        self.token = token
        self.opener = opener

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        fields: Optional[Sequence[Tuple[str, str]]] = None,
        multipart: bool = False,
    ) -> Dict[str, Any]:
        url = f"{API_ROOT}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        auth_header = "Auth" + "orization"
        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        headers[auth_header] = f"Bearer {self.token}"
        body = None
        if fields is not None:
            if multipart:
                boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
                body_bytes = bytearray()
                for name, value in fields:
                    body_bytes.extend(f"--{boundary}\r\n".encode("utf-8"))
                    body_bytes.extend(
                        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
                    )
                    body_bytes.extend(str(value).encode("utf-8"))
                    body_bytes.extend(b"\r\n")
                body_bytes.extend(f"--{boundary}--\r\n".encode("utf-8"))
                headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
                body = bytes(body_bytes)
            else:
                headers["Content-Type"] = "application/x-www-form-urlencoded"
                body = urllib.parse.urlencode(fields).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with self.opener(request, timeout=30) as response:
                response_body = response.read()
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace").strip()
            if self.token:
                detail = detail.replace(self.token, "[REDACTED]")
            raise ModioError(
                f"mod.io API returned HTTP {error.code} {error.reason}"
                + (f": {detail}" if detail else "")
            ) from None
        except urllib.error.URLError as error:
            raise ModioError(f"Could not connect to mod.io: {error.reason}") from None
        except OSError as error:
            raise ModioError(f"Could not complete the mod.io request: {error}") from None

        if not response_body:
            return {}
        try:
            payload = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ModioError("mod.io returned an invalid JSON response.") from None
        if not isinstance(payload, dict):
            raise ModioError("mod.io returned an unexpected response shape.")
        return payload


def get_api_key() -> Optional[str]:
    """Retrieve MODIO_API_KEY from environment or .env files."""
    return get_env_var("MODIO_API_KEY")


def get_oauth_token(cli_token: Optional[str] = None) -> Optional[str]:
    """Retrieve OAuth2 token / PAT from CLI flag, environment, or .env files."""
    if cli_token and cli_token.strip():
        return cli_token.strip()
    for key in ("MODIO_OAUTH_TOKEN", "MODIO_PAT", "MODIO_TOKEN"):
        val = get_env_var(key)
        if val:
            return val
    return None


def query_modio(query_or_slug: str, api_key: str) -> Dict[str, Any]:
    """Search mod.io for a BG3 mod by name, slug, URL, or numeric ID."""
    clean_query = query_or_slug.strip()

    if "mod.io" in clean_query:
        parts = clean_query.rstrip("/").split("/")
        clean_query = parts[-1]

    if clean_query.isdigit():
        slug_candidates = [clean_query]
        is_id = True
    else:
        is_id = False
        candidates = [
            clean_query.lower(),
            clean_query.lower().replace(" ", "-"),
            clean_query.lower().replace(" ", ""),
        ]
        slug_candidates = []
        for c in candidates:
            if re.match(r"^[a-z0-9-]+$", c) and c not in slug_candidates:
                slug_candidates.append(c)

    for cand in slug_candidates:
        params = {"api_key": api_key}
        if is_id:
            params["id"] = cand
        else:
            params["name_id"] = cand

        url = f"https://{MODIO_API_HOST}/v1/games/{BG3_GAME_ID}/mods?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("data") and len(data["data"]) > 0:
                    return data["data"][0]
        except Exception:
            pass

    clean_q_alpha = re.sub(r"[^a-z0-9]", "", clean_query.lower())
    search_queries = [clean_query]
    if clean_q_alpha and clean_q_alpha != clean_query.lower():
        search_queries.append(clean_q_alpha)

    results = []
    for q_term in search_queries:
        params = {"api_key": api_key, "_q": q_term}
        url = f"https://{MODIO_API_HOST}/v1/games/{BG3_GAME_ID}/mods?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                batch = data.get("data", [])
                if batch:
                    results.extend(batch)
        except Exception:
            pass

        for m in results:
            m_name = m.get("name", "").lower()
            m_slug = m.get("name_id", "").lower()
            if (
                m_name == clean_query.lower()
                or m_slug == clean_query.lower()
                or re.sub(r"[^a-z0-9]", "", m_name) == clean_q_alpha
                or re.sub(r"[^a-z0-9]", "", m_slug) == clean_q_alpha
            ):
                return m

    if not results:
        raise RuntimeError(f"No mods found on mod.io matching: '{query_or_slug}'")

    query_tokens = set(re.findall(r"\w+", clean_query.lower()))
    if query_tokens:
        def match_score(mod_entry: Dict[str, Any]) -> Tuple[int, int, int]:
            name_tokens = set(re.findall(r"\w+", mod_entry.get("name", "").lower()))
            slug_tokens = set(re.findall(r"\w+", mod_entry.get("name_id", "").lower()))
            all_tokens = name_tokens | slug_tokens
            overlap = len(query_tokens.intersection(all_tokens))
            is_all = 1 if query_tokens.issubset(all_tokens) else 0
            norm_match = (
                1
                if re.sub(r"[^a-z0-9]", "", mod_entry.get("name", "").lower()) == clean_q_alpha
                else 0
            )
            return (norm_match, is_all, overlap)

        results_sorted = sorted(results, key=match_score, reverse=True)
        if results_sorted and match_score(results_sorted[0])[2] > 0:
            return results_sorted[0]

    return results[0]


def download_mod_file(mod_metadata: Dict[str, Any], api_key: str) -> bytes:
    """Download mod archive (.zip or .pak) from mod.io."""
    modfile = mod_metadata.get("modfile")
    if not modfile or not modfile.get("download", {}).get("binary_url"):
        raise RuntimeError(
            f"Mod '{mod_metadata.get('name')}' has no active file download available."
        )

    download_url = modfile["download"]["binary_url"]
    sep = "&" if "?" in download_url else "?"
    signed_url = f"{download_url}{sep}api_key={api_key}"

    req = urllib.request.Request(signed_url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return resp.read()
