"""Rate-limited HTTP client with exponential backoff retry."""

from __future__ import annotations

import time
import logging
import urllib.request
import urllib.error
import urllib.parse
import json
from typing import Any

from bbb_database_stc.config import HTTP_DELAY, HTTP_MAX_RETRIES

log = logging.getLogger(__name__)

BACKOFF_BASE = 1.5


def get_json(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    delay: float = HTTP_DELAY,
    max_retries: int = HTTP_MAX_RETRIES,
    timeout: int = 30,
) -> Any:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    hdrs = {"Accept": "application/json", "User-Agent": "BBB-MagnoliaDB/2.0"}
    if headers:
        hdrs.update(headers)

    req = urllib.request.Request(url, headers=hdrs)
    last_err: Exception | None = None

    for attempt in range(max_retries + 1):
        if attempt > 0:
            wait = BACKOFF_BASE ** attempt
            log.debug("Retry %d/%d after %.1fs", attempt, max_retries, wait)
            time.sleep(wait)
        try:
            time.sleep(delay)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code == 429:
                log.warning("Rate limited (429) on %s", url)
                continue
            if e.code >= 500:
                log.warning("Server error %d on %s", e.code, url)
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            log.warning("Network error on %s: %s", url, e)
            continue

    raise RuntimeError(f"Failed after {max_retries} retries: {url}") from last_err


def get_text(
    url: str,
    *,
    params: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    delay: float = HTTP_DELAY,
    max_retries: int = HTTP_MAX_RETRIES,
    timeout: int = 30,
) -> str:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    hdrs = {"User-Agent": "BBB-MagnoliaDB/2.0"}
    if headers:
        hdrs.update(headers)

    req = urllib.request.Request(url, headers=hdrs)
    last_err: Exception | None = None

    for attempt in range(max_retries + 1):
        if attempt > 0:
            wait = BACKOFF_BASE ** attempt
            time.sleep(wait)
        try:
            time.sleep(delay)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504):
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            continue

    raise RuntimeError(f"Failed after {max_retries} retries: {url}") from last_err


def post_json(
    url: str,
    data: dict | str,
    *,
    headers: dict[str, str] | None = None,
    delay: float = HTTP_DELAY,
    max_retries: int = HTTP_MAX_RETRIES,
    timeout: int = 30,
) -> Any:
    hdrs = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "BBB-MagnoliaDB/2.0",
    }
    if headers:
        hdrs.update(headers)

    body = json.dumps(data).encode() if isinstance(data, dict) else data.encode()
    req = urllib.request.Request(url, data=body, headers=hdrs)
    last_err: Exception | None = None

    for attempt in range(max_retries + 1):
        if attempt > 0:
            time.sleep(BACKOFF_BASE ** attempt)
        try:
            time.sleep(delay)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504):
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            continue

    raise RuntimeError(f"Failed after {max_retries} retries: {url}") from last_err
