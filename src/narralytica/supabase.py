from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError

from narralytica.http import fetch_json


class SupabasePublisher:
    """Publish signal outputs and cache payloads through Supabase PostgREST."""

    def __init__(self, url: str, service_role_key: str) -> None:
        if not url:
            raise ValueError("SUPABASE_URL is required")
        if not service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required")

        self.base_url = url.rstrip("/")
        self.service_role_key = service_role_key
        self.rest_url = f"{self.base_url}/rest/v1"

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal,resolution=merge-duplicates",
        }

    def _request(
        self,
        path: str,
        *,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        final_headers = dict(self._headers)
        final_headers.update(headers or {})
        return fetch_json(
            f"{self.rest_url}/{path.lstrip('/')}",
            method=method,
            params=params,
            headers=final_headers,
            body=body,
        )

    def insert_decision_run(
        self,
        *,
        asset: str,
        output: dict[str, Any],
        story: dict[str, Any],
    ) -> None:
        signal = output["signal"]
        decision = output["decision"]
        snapshot = output["snapshot"]
        payload = {
            "asset": asset.lower(),
            "snapshot_time_utc": snapshot["snapshot_time_utc"],
            "reference_price": snapshot["reference_price"],
            "reference_price_date": snapshot["reference_price_date"],
            "price_source": snapshot["price_source"],
            "overall_signal": signal["overall_signal"],
            "total_score": signal["total_score"],
            "action": decision["action"],
            "market_bias": decision["market_bias"],
            "conviction": decision["conviction"],
            "position_size_bucket": decision["position_size_bucket"],
            "signal_output": output,
            "signal_story": story,
        }
        self._request("decision_runs", method="POST", body=payload)

    def upsert_latest_asset_state(
        self,
        *,
        asset: str,
        output: dict[str, Any],
        story: dict[str, Any],
    ) -> None:
        signal = output["signal"]
        decision = output["decision"]
        snapshot = output["snapshot"]
        payload = {
            "asset": asset.lower(),
            "snapshot_time_utc": snapshot["snapshot_time_utc"],
            "reference_price": snapshot["reference_price"],
            "reference_price_date": snapshot["reference_price_date"],
            "price_source": snapshot["price_source"],
            "overall_signal": signal["overall_signal"],
            "total_score": signal["total_score"],
            "action": decision["action"],
            "market_bias": decision["market_bias"],
            "conviction": decision["conviction"],
            "position_size_bucket": decision["position_size_bucket"],
            "signal_output": output,
            "signal_story": story,
            "updated_at": snapshot["snapshot_time_utc"],
        }
        self._request(
            "latest_asset_state",
            method="POST",
            params={"on_conflict": "asset"},
            body=payload,
        )

    def upsert_site_cache(
        self,
        *,
        cache_key: str,
        payload: dict[str, Any],
        source: str,
        refresh_interval_minutes: int,
    ) -> None:
        body = {
            "cache_key": cache_key,
            "payload": payload,
            "source": source,
            "refresh_interval_minutes": refresh_interval_minutes,
            "updated_at": payload.get("updated_at"),
        }
        self._request(
            "site_cache",
            method="POST",
            params={"on_conflict": "cache_key"},
            body=body,
        )

    def upsert_news_events(
        self,
        *,
        rows: list[dict[str, Any]],
    ) -> None:
        if not rows:
            return
        self._request(
            "news_events",
            method="POST",
            params={"on_conflict": "asset,news_id"},
            body=rows,
        )


def describe_http_error(exc: HTTPError) -> str:
    body_text = ""
    try:
        if exc.fp is not None:
            body_text = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body_text = ""
    if body_text:
        return f"HTTP {exc.code}: {body_text}"
    return f"HTTP {exc.code}: {exc.reason}"


def load_story_file(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)
