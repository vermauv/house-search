"""Tiny stdlib HTTP helper, so the skill needs no third-party packages.

The transport is injectable, which keeps every network-touching module
testable without a network.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Mapping

USER_AGENT = "house-search-skill/0.1 (agent skill; contact: see repository)"

# (request, timeout_seconds) -> response body bytes. Raise HttpError on failure.
Transport = Callable[[urllib.request.Request, float], bytes]

_SECRET_PARAM = re.compile(r"(key|token|apikey)=[^&\s]+", re.IGNORECASE)


class HttpError(RuntimeError):
    """Raised for any failed request. Messages never contain API keys."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


def redact(url: str) -> str:
    """Strip API keys from a URL so it is safe to print or log."""
    return _SECRET_PARAM.sub(r"\1=REDACTED", url)


def _urllib_transport(req: urllib.request.Request, timeout: float) -> bytes:
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise HttpError(f"HTTP {exc.code} from {redact(req.full_url)}", exc.code) from None
    except urllib.error.URLError as exc:
        raise HttpError(f"Network error for {redact(req.full_url)}: {exc.reason}") from None


def request_json(
    url: str,
    *,
    params: Mapping[str, Any] | None = None,
    json_body: Any = None,
    form: Mapping[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = 25.0,
    retries: int = 2,
    backoff: float = 1.5,
    transport: Transport | None = None,
) -> Any:
    """GET (or POST when a body is given) and decode a JSON response.

    Retries on HTTP 429 and 5xx with exponential backoff; other errors raise
    immediately because retrying a 4xx never helps.
    """
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    data: bytes | None = None
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode()
        hdrs["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode()
        hdrs["Content-Type"] = "application/x-www-form-urlencoded"
    hdrs.update(headers or {})

    send = transport or _urllib_transport
    last: HttpError | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=hdrs)  # noqa: S310
        try:
            body = send(req, timeout)
        except HttpError as exc:
            last = exc
            retryable = exc.status is None or exc.status == 429 or exc.status >= 500
            if not retryable or attempt == retries:
                raise
            time.sleep(backoff**attempt)
            continue
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise HttpError(f"Non-JSON response from {redact(url)}: {exc}") from None
    raise last or HttpError("request failed")
