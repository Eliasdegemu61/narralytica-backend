from __future__ import annotations

from typing import Any

from narralytica.http import fetch_json


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
