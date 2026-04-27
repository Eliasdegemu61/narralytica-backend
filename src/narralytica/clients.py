from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from xml.etree import ElementTree

from narralytica.http import fetch_json, fetch_text


class MarketauxClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.marketaux.com/v1",
    ) -> None:
        if not api_key:
            raise ValueError("MARKETAUX_API_KEY is required")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def get_crypto_news(
        self,
        *,
        published_after: str,
        published_before: str,
        language: str = "en",
        limit: int = 3,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.base_url}/news/all",
            params={
                "api_token": self.api_key,
                "language": language,
                "entity_types": "cryptocurrency",
                "must_have_entities": "true",
                "filter_entities": "true",
                "published_after": published_after,
                "published_before": published_before,
                "limit": limit,
                "page": page,
            },
        )
        data = payload.get("data", [])
        return data if isinstance(data, list) else []


class CoinDeskRSSClient:
    def __init__(
        self,
        *,
        feed_url: str = "https://www.coindesk.com/arc/outboundfeeds/rss/",
    ) -> None:
        self.feed_url = feed_url

    def get_news(
        self,
        *,
        lookback_hours: int = 24,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        xml_text = fetch_text(self.feed_url, headers={"Accept": "application/rss+xml, application/xml;q=0.9, text/xml;q=0.8"})
        root = ElementTree.fromstring(xml_text)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
        rows: list[dict[str, Any]] = []
        for item in root.findall(".//item"):
            pub_date = item.findtext("pubDate")
            if not pub_date:
                continue
            try:
                published_at = parsedate_to_datetime(pub_date).astimezone(timezone.utc)
            except (TypeError, ValueError):
                continue
            if published_at < cutoff:
                continue

            categories = [element.text.strip() for element in item.findall("category") if element.text and element.text.strip()]
            link = (item.findtext("link") or "").strip()
            guid = (item.findtext("guid") or link or item.findtext("title") or "").strip()
            title = (item.findtext("title") or "").strip()
            description = (item.findtext("description") or "").strip()
            rows.append(
                {
                    "id": guid or title,
                    "release_time": int(published_at.timestamp() * 1000),
                    "title": title,
                    "content": description,
                    "category": None,
                    "category_label": "crypto_market_news",
                    "tags": categories,
                    "matched_currencies": [],
                    "source_link": link or None,
                    "original_link": link or None,
                    "author": "CoinDesk",
                    "nick_name": "CoinDesk",
                    "feature_image": None,
                    "impression_count": 0,
                    "like_count": 0,
                    "reply_count": 0,
                    "retweet_count": 0,
                    "importance_score": 50.0,
                    "source_type": "coindesk_rss",
                }
            )

        rows.sort(key=lambda row: int(row.get("release_time", 0) or 0), reverse=True)
        return rows[:limit]


class SoSoValueClient:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("SOSO_API_KEY is required")
        self.api_key = api_key
        self.base_url = "https://api.sosovalue.xyz"

    @property
    def _headers(self) -> dict[str, str]:
        return {"x-soso-api-key": self.api_key}

    def get_etf_historical_inflow(self, etf_type: str = "us-btc-spot") -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v2/etf/historicalInflowChart",
            method="POST",
            headers=self._headers,
            body={"type": etf_type},
        )
        data = payload.get("data", [])
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("list", [])
        return []

    def get_current_etf_metrics(self, etf_type: str = "us-btc-spot") -> dict[str, Any]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v2/etf/currentEtfDataMetrics",
            method="POST",
            headers=self._headers,
            body={"type": etf_type},
        )
        data = payload.get("data", {})
        return data if isinstance(data, dict) else {}

    def get_analysis_chart(self, chart_name: str, *, limit: int = 5) -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v1/analyses/{chart_name}",
            headers=self._headers,
            params={"limit": limit},
        )
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def get_currency_list(self) -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v1/currencies",
            headers=self._headers,
        )
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def get_currency_pairs(
        self,
        currency_id: str,
        *,
        page_size: int = 5,
    ) -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v1/currencies/{currency_id}/pairs",
            headers=self._headers,
            params={"page_size": page_size},
        )
        data = payload.get("data", {})
        if isinstance(data, dict):
            pair_list = data.get("list", [])
            return pair_list if isinstance(pair_list, list) else []
        return []

    def get_currency_klines(
        self,
        currency_id: str,
        *,
        interval: str = "1d",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v1/currencies/{currency_id}/klines",
            headers=self._headers,
            params={"interval": interval, "limit": limit},
        )
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def get_currency_market_snapshot(self, currency_id: str) -> dict[str, Any]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v1/currencies/{currency_id}/market-snapshot",
            headers=self._headers,
        )
        data = payload.get("data", {})
        return data if isinstance(data, dict) else {}

    def get_sector_spotlight(self) -> dict[str, Any]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v1/currencies/sector-spotlight",
            headers=self._headers,
        )
        data = payload.get("data", {})
        return data if isinstance(data, dict) else {}

    def get_index_list(self) -> list[str]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v1/indices",
            headers=self._headers,
        )
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    def get_index_market_snapshot(self, ticker: str) -> dict[str, Any]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v1/indices/{ticker}/market-snapshot",
            headers=self._headers,
        )
        data = payload.get("data", {})
        return data if isinstance(data, dict) else {}

    def get_news(
        self,
        *,
        currency_id: str | None = None,
        category: str | None = None,
        language: str = "en",
        page: int = 1,
        page_size: int = 20,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "language": language,
            "page": page,
            "page_size": page_size,
        }
        if currency_id:
            params["currency_id"] = currency_id
        if category:
            params["category"] = category
        if start_time is not None:
            params["start_time"] = start_time
        if end_time is not None:
            params["end_time"] = end_time

        payload = fetch_json(
            f"{self.base_url}/openapi/v1/news",
            headers=self._headers,
            params=params,
        )
        data = payload.get("data", {})
        if isinstance(data, dict):
            rows = data.get("list", [])
            return rows if isinstance(rows, list) else []
        return []

    def get_recent_asset_news(
        self,
        currency_id: str,
        *,
        lookback_days: int = 7,
        page_size: int = 50,
        language: str = "en",
    ) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=lookback_days)
        return self.get_news(
            currency_id=currency_id,
            language=language,
            page=1,
            page_size=page_size,
            start_time=int(start.timestamp() * 1000),
            end_time=int(now.timestamp() * 1000),
        )

    def get_featured_news(
        self,
        *,
        categories: list[int] | None = None,
        language: str = "en",
        page: int = 1,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "language": language,
            "page": page,
            "page_size": page_size,
        }
        if categories:
            params["category"] = ",".join(str(category) for category in categories)

        payload = fetch_json(
            f"{self.base_url}/openapi/v1/news/featured",
            headers=self._headers,
            params=params,
        )
        data = payload.get("data", {})
        if isinstance(data, dict):
            rows = data.get("list", [])
            return rows if isinstance(rows, list) else []
        return []

    def get_macro_events(self) -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.base_url}/openapi/v1/macro/events",
            headers=self._headers,
        )
        data = payload.get("data", [])
        return data if isinstance(data, list) else []


class BinanceMarketClient:
    def __init__(self) -> None:
        self.futures_url = "https://fapi.binance.com"
        self.spot_url = "https://api.binance.com"

    def get_global_long_short_ratio(
        self,
        symbol: str = "BTCUSDT",
        period: str = "1d",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.futures_url}/futures/data/globalLongShortAccountRatio",
            params={"symbol": symbol, "period": period, "limit": limit},
        )
        return payload if isinstance(payload, list) else []

    def get_spot_klines(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1d",
        limit: int = 5,
    ) -> list[list[Any]]:
        payload = fetch_json(
            f"{self.spot_url}/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
        )
        return payload if isinstance(payload, list) else []

    def get_funding_rates(
        self,
        symbol: str = "BTCUSDT",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.futures_url}/fapi/v1/fundingRate",
            params={"symbol": symbol, "limit": limit},
        )
        return payload if isinstance(payload, list) else []

    def get_open_interest_hist(
        self,
        symbol: str = "BTCUSDT",
        period: str = "5m",
        limit: int = 48,
    ) -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.futures_url}/futures/data/openInterestHist",
            params={
                "symbol": symbol,
                "period": period,
                "limit": limit,
                "contractType": "PERPETUAL",
            },
        )
        return payload if isinstance(payload, list) else []


class SoDEXMarketClient:
    def __init__(self) -> None:
        self.perps_url = "https://mainnet-gw.sodex.dev/api/v1/perps"

    def get_perps_klines(
        self,
        symbol: str,
        interval: str = "1d",
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        payload = fetch_json(
            f"{self.perps_url}/markets/{symbol}/klines",
            params={"interval": interval, "limit": limit},
        )
        if isinstance(payload, dict):
            data = payload.get("data", [])
            return data if isinstance(data, list) else []
        return []
