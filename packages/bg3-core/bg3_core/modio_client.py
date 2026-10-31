#!/usr/bin/env python3
"""
modio_client.py - Reusable client for the mod.io REST API v1.

Provides ModioClient with bearer token auth, pagination, atomic caching,
exponential backoff retry with jitter, and helper functions for CLI scripts.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .env_paths import get_env_var, get_xdg_cache_home

logger = logging.getLogger(__name__)

BG3_GAME_ID = 6715
MODIO_API_HOST = f"g-{BG3_GAME_ID}.modapi.io"
API_ROOT = f"https://{MODIO_API_HOST}/v1"
USER_AGENT = "BG3ModStudio/1.0"


class ModioError(RuntimeError):
    """Raised for an invalid target, preflight failure, or mod.io API error."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ModioClient:
    """Authenticated mod.io v1 REST client supporting GET, form-urlencoded, and multipart POST/PUT."""

    def __init__(
        self,
        token: Optional[str] = None,
        opener: Any = urllib.request.urlopen,
        cache_ttl_seconds: int = 300,
        enable_cache: bool = False,
        cache_path: Optional[Path] = None,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        jitter: bool = True,
    ) -> None:
        self.token = token or ""
        self.opener = opener
        self.cache_ttl_seconds = cache_ttl_seconds
        self.enable_cache = enable_cache
        self._cache_path = cache_path
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def get_cache_path(self) -> Path:
        """Resolve path to local mod.io response cache."""
        if self._cache_path is not None:
            return self._cache_path
        cache_dir = get_xdg_cache_home()
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "modio_cache.json"

    def _read_cache(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            path = self.get_cache_path()
            if path.is_file():
                with open(path, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                entry = cache.get(key)
                if entry and isinstance(entry, dict):
                    ts = entry.get("timestamp", 0)
                    if time.time() - ts < self.cache_ttl_seconds:
                        return entry.get("data")
        except (OSError, ValueError, KeyError) as err:
            logger.debug("Failed to read mod.io cache: %s", err)
        return None

    def _write_cache(self, key: str, data: Dict[str, Any]) -> None:
        try:
            path = self.get_cache_path()
            cache: Dict[str, Any] = {}
            if path.is_file():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                except (OSError, ValueError):
                    cache = {}
            cache[key] = {
                "timestamp": time.time(),
                "data": data,
            }
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=2)
            tmp.replace(path)
        except OSError as err:
            logger.debug("Failed to write mod.io cache: %s", err)

    def clear_cache(self) -> None:
        """Clear local mod.io response cache."""
        try:
            path = self.get_cache_path()
            if path.exists():
                path.unlink()
        except OSError as err:
            logger.debug("Failed to clear mod.io cache: %s", err)

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        fields: Optional[Sequence[Tuple[str, str]]] = None,
        multipart: bool = False,
        bypass_cache: bool = False,
    ) -> Dict[str, Any]:
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{API_ROOT}{path}"
        if params:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{urllib.parse.urlencode(params)}"

        cache_key = url
        if method.upper() == "GET" and self.enable_cache and not bypass_cache and self.cache_ttl_seconds > 0:
            cached = self._read_cache(cache_key)
            if cached is not None:
                return cached

        auth_header = "Authorization"
        headers = {
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }
        if self.token:
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

        retries = 0
        while True:
            try:
                with self.opener(request, timeout=30) as response:
                    response_body = response.read()
                break
            except urllib.error.HTTPError as error:
                try:
                    detail = error.read().decode("utf-8", errors="replace").strip()
                finally:
                    error.close()
                if self.token:
                    detail = detail.replace(self.token, "[REDACTED]")

                if error.code in (429, 500, 502, 503, 504) and retries < self.max_retries:
                    retries += 1
                    retry_after = error.headers.get("Retry-After") if hasattr(error, "headers") and error.headers else None
                    sleep_time = 0.0
                    if retry_after:
                        try:
                            sleep_time = float(retry_after)
                        except (ValueError, TypeError):
                            sleep_time = 0.0
                    if sleep_time <= 0.0:
                        sleep_time = self.backoff_factor * (2 ** (retries - 1))
                        if self.jitter:
                            sleep_time += random.uniform(0.0, 0.25)
                    time.sleep(sleep_time)
                    continue

                raise ModioError(
                    f"mod.io API returned HTTP {error.code} {error.reason}"
                    + (f": {detail}" if detail else "")
                ) from None
            except urllib.error.URLError as error:
                if retries < self.max_retries:
                    retries += 1
                    sleep_time = self.backoff_factor * (2 ** (retries - 1))
                    if self.jitter:
                        sleep_time += random.uniform(0.0, 0.25)
                    time.sleep(sleep_time)
                    continue
                raise ModioError(f"Network error contacting mod.io: {error.reason}") from None

        try:
            payload = json.loads(response_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            raise ModioError("mod.io returned non-JSON content.") from error

        if not isinstance(payload, dict):
            raise ModioError("mod.io returned an unexpected response shape.")

        if method.upper() == "GET" and self.enable_cache and not bypass_cache and self.cache_ttl_seconds > 0:
            self._write_cache(cache_key, payload)
        elif method.upper() in ("POST", "PUT", "DELETE"):
            self.clear_cache()

        return payload

    def download_file(self, url: str, destination: Path | None = None, chunk_size: int = 65536) -> bytes:
        """Download binary content from URL with chunking and retries."""
        headers = {"User-Agent": USER_AGENT}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        req = urllib.request.Request(url, headers=headers)
        retries = 0
        while True:
            try:
                with self.opener(req, timeout=60) as resp:
                    if destination:
                        tmp_dst = destination.with_suffix(f"{destination.suffix}.part")
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with open(tmp_dst, "wb") as f_out:
                            while True:
                                chunk = resp.read(chunk_size)
                                if not chunk:
                                    break
                                f_out.write(chunk)
                        tmp_dst.replace(destination)
                        return b""
                    else:
                        buffer = bytearray()
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            buffer.extend(chunk)
                        return bytes(buffer)
            except urllib.error.HTTPError as error:
                is_transient = error.code in (429, 500, 502, 503, 504)
                if is_transient and retries < self.max_retries:
                    retries += 1
                    sleep_time = self.backoff_factor * (2 ** (retries - 1))
                    time.sleep(sleep_time)
                    continue
                raise ModioError(f"HTTP {error.code} downloading file: {error.reason}") from error
            except urllib.error.URLError as error:
                if retries < self.max_retries:
                    retries += 1
                    sleep_time = self.backoff_factor * (2 ** (retries - 1))
                    time.sleep(sleep_time)
                    continue
                raise ModioError(f"Network error downloading file: {error.reason}") from error

    def get_paged(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        page_size: int = 100,
    ) -> List[Dict[str, Any]]:
        """Fetch all items from a paginated endpoint automatically."""
        offset = 0
        items: List[Dict[str, Any]] = []
        base_params = dict(params or {})
        while True:
            page_params = {**base_params, "_limit": page_size, "_offset": offset}
            payload = self.request("GET", path, params=page_params)
            data = payload.get("data", [])
            if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
                raise ModioError("mod.io returned an unexpected list payload shape.")
            items.extend(data)
            total = payload.get("result_total")
            if total is not None:
                if not isinstance(total, int) or total < 0:
                    raise ModioError("mod.io returned an invalid result_total.")
                if offset + len(data) >= total:
                    break
            elif len(data) < page_size:
                break
            if not data:
                break
            offset += len(data)
        return items


def get_api_key() -> Optional[str]:
    """Retrieve MODIO_API_KEY from environment or config files."""
    return get_env_var("MODIO_API_KEY")


def get_oauth_token(cli_token: Optional[str] = None) -> Optional[str]:
    """Retrieve OAuth2 token / PAT from CLI flag, environment, or config files."""
    if cli_token and cli_token.strip():
        return cli_token.strip()
    for key in ("MODIO_OAUTH_TOKEN", "MODIO_PAT", "MODIO_TOKEN"):
        val = get_env_var(key)
        if val:
            return val
    return None


def query_modio(query_or_slug: str, api_key: str) -> Dict[str, Any]:
    """Search mod.io for a BG3 mod by name, slug, URL, or numeric ID using ModioClient."""
    clean_query = query_or_slug.strip()
    if "mod.io" in clean_query:
        parts = clean_query.rstrip("/").split("/")
        clean_query = parts[-1]

    client = ModioClient()

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
        params: dict[str, Any] = {"api_key": api_key}
        if is_id:
            params["id"] = cand
        else:
            params["name_id"] = cand

        try:
            data = client.request("GET", f"/games/{BG3_GAME_ID}/mods", params=params)
            if data.get("data") and len(data["data"]) > 0:
                return data["data"][0]
        except Exception as err:
            logger.debug("Candidate query failed: %s", err)

    clean_q_alpha = re.sub(r"[^a-z0-9]", "", clean_query.lower())
    search_queries = [clean_query]
    if clean_q_alpha and clean_q_alpha != clean_query.lower():
        search_queries.append(clean_q_alpha)

    results: list[dict[str, Any]] = []
    for q_term in search_queries:
        params = {"api_key": api_key, "_q": q_term}
        try:
            data = client.request("GET", f"/games/{BG3_GAME_ID}/mods", params=params)
            batch = data.get("data", [])
            if batch:
                results.extend(batch)
        except Exception as err:
            logger.debug("Search query term failed: %s", err)

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


def download_mod_file(mod_metadata: Dict[str, Any], api_key: str, destination: Path | None = None) -> bytes:
    """Download mod archive (.zip or .pak) from mod.io using resilient ModioClient."""
    modfile = mod_metadata.get("modfile")
    if not modfile or not modfile.get("download", {}).get("binary_url"):
        raise RuntimeError(
            f"Mod '{mod_metadata.get('name')}' has no active file download available."
        )

    download_url = modfile["download"]["binary_url"]
    sep = "&" if "?" in download_url else "?"
    signed_url = f"{download_url}{sep}api_key={api_key}"

    client = ModioClient()
    return client.download_file(signed_url, destination=destination)
