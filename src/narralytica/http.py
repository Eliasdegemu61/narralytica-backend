from __future__ import annotations

import json
import time
from typing import Any
from urllib import parse, request
from urllib.error import URLError


DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 1.0
DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "NarralyticaBot/0.1 (+local-test)",
}


def fetch_json(
    url: str,
    *,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRIES,
) -> Any:
    full_url = url
    if params:
        query = parse.urlencode(params, doseq=True)
        separator = "&" if "?" in url else "?"
        full_url = f"{url}{separator}{query}"

    data = None
    final_headers = dict(DEFAULT_HEADERS)
    final_headers.update(headers or {})
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        final_headers.setdefault("Content-Type", "application/json")

    req = request.Request(
        full_url,
        method=method.upper(),
        headers=final_headers,
        data=data,
    )

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            with request.urlopen(req, timeout=timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                text = response.read().decode(charset)
                return json.loads(text)
        except URLError as exc:
            last_error = exc
            if attempt == retries - 1:
                raise
            time.sleep(DEFAULT_RETRY_DELAY_SECONDS * (attempt + 1))

    if last_error is not None:
        raise last_error
    raise RuntimeError("fetch_json failed without raising a specific error")
