"""Shared HTTP helper: fetch JSON from a rate-limited API, retrying on
429/5xx/connection errors with exponential backoff.

Before this module existed, three different scripts independently
hand-rolled their own retry loop for the exact same concern ("fetch JSON
from a rate-limited API, retry on 429/5xx") - resolve.py talked to
Scryfall via raw urllib with a manual certifi/ssl workaround,
archidekt.py talked to Archidekt via requests with a different retry
loop, and oldest-printing.py reimplemented a third, simpler client
instead of reusing either. This is the one place that logic lives now
(see REFACTOR.md §8.1).

Named `net.py` rather than the more obvious `http.py` to avoid shadowing
the standard library's `http` package on sys.path - every script here
inserts its own directory at the front of sys.path, and `requests`
itself depends on `http.client`, so a local `http.py` would silently
break every HTTP call in the project.
"""

from __future__ import annotations

import sys
import time
from typing import Any

import requests

USER_AGENT = "mtg-decks/1.0 (+https://github.com/)"
MAX_ATTEMPTS = 5
RETRY_DELAY = 1.0  # seconds, multiplied by BACKOFF_FACTOR after each retry
BACKOFF_FACTOR = 2.0
TIMEOUT = 30
MIN_REQUEST_INTERVAL = 0.25  # seconds; matches Scryfall's documented fair-use guidance

_last_request_at = 0.0


def _pace() -> None:
    """Sleep just long enough to keep requests at least
    MIN_REQUEST_INTERVAL apart. Without this, a tight loop of many
    individual requests (e.g. fuzzy-resolving several not-found card
    names in a row) can trigger 429s on otherwise-healthy requests, which
    then makes the exponential backoff retry loop (meant for genuine
    transient failures) kick in constantly instead.
    """
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    if elapsed < MIN_REQUEST_INTERVAL:
        time.sleep(MIN_REQUEST_INTERVAL - elapsed)
    _last_request_at = time.monotonic()


def _request(method: str, url: str, **kwargs: Any) -> requests.Response | None:
    """Perform one HTTP request, retrying on 429/5xx/connection errors
    with exponential backoff. Returns None for a 404 (a legitimate "not
    found", not a failure). Raises requests.RequestException if every
    attempt is exhausted.
    """
    headers = kwargs.pop("headers", {}) or {}
    headers.setdefault("User-Agent", USER_AGENT)
    headers.setdefault("Accept", "application/json")

    delay = RETRY_DELAY
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        _pace()
        try:
            resp = requests.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < MAX_ATTEMPTS:
                print(
                    f"  {method} {url} -> {e}; retrying in {delay:.0f}s "
                    f"(attempt {attempt}/{MAX_ATTEMPTS})...",
                    file=sys.stderr,
                )
                time.sleep(delay)
                delay *= BACKOFF_FACTOR
                continue
            raise
        if resp.status_code == 404:
            return None
        if resp.status_code == 429 or resp.status_code >= 500:
            last_error = requests.HTTPError(f"HTTP {resp.status_code} from {method} {url}")
            if attempt < MAX_ATTEMPTS:
                print(
                    f"  {method} {url} -> HTTP {resp.status_code}; retrying in {delay:.0f}s "
                    f"(attempt {attempt}/{MAX_ATTEMPTS})...",
                    file=sys.stderr,
                )
                time.sleep(delay)
                delay *= BACKOFF_FACTOR
                continue
            raise last_error
        resp.raise_for_status()
        return resp

    assert last_error is not None
    raise last_error


def get_json(url: str, params: dict[str, str] | None = None) -> dict[str, Any] | None:
    """GET `url` as JSON, retrying transient failures. None on a 404."""
    resp = _request("GET", url, params=params)
    return resp.json() if resp is not None else None


def post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST a JSON `payload` to `url`, retrying transient failures."""
    resp = _request("POST", url, json=payload)
    assert resp is not None  # the POST endpoints used in this project never 404
    return resp.json()
