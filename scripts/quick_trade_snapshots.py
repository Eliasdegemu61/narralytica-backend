from __future__ import annotations

import json
from urllib.error import HTTPError

import _bootstrap
from narralytica.clients import BinanceMarketClient, SoDEXMarketClient
from narralytica.config import load_dotenv
from narralytica.quick_trade_engine import BTC_ETH_QUICK_TRADE_CONFIG, build_quick_trade_input_payload
from narralytica.supabase import SupabasePublisher, describe_http_error


def _safe_perps_klines(
    sodex: SoDEXMarketClient,
    *,
    asset: str,
    symbol: str,
    interval: str,
    limit: int,
) -> list[dict[str, object]]:
    try:
        rows = sodex.get_perps_klines(symbol=symbol, interval=interval, limit=limit)
        return rows or []
    except Exception as exc:
        print(f"[warn] SoDEX {interval} klines unavailable for {asset}: {exc}")
        return []


def _safe_long_short_ratio(
    binance: BinanceMarketClient,
    *,
    asset: str,
    symbol: str,
    period: str = "1h",
    limit: int = 24,
) -> list[dict[str, object]]:
    try:
        rows = binance.get_global_long_short_ratio(symbol=symbol, period=period, limit=limit)
        return rows or []
    except Exception as exc:
        print(f"[warn] Binance long/short ratio unavailable for {asset}: {exc}")
        return []


def _safe_funding_rates(
    binance: BinanceMarketClient,
    *,
    asset: str,
    symbol: str,
    limit: int = 24,
) -> list[dict[str, object]]:
    try:
        rows = binance.get_funding_rates(symbol=symbol, limit=limit)
        return rows or []
    except Exception as exc:
        print(f"[warn] Binance funding unavailable for {asset}: {exc}")
        return []


def _safe_open_interest(
    binance: BinanceMarketClient,
    *,
    asset: str,
    symbol: str,
    period: str = "5m",
    limit: int = 48,
) -> list[dict[str, object]]:
    try:
        rows = binance.get_open_interest_hist(symbol=symbol, period=period, limit=limit)
        return rows or []
    except Exception as exc:
        print(f"[warn] Binance open interest unavailable for {asset}: {exc}")
        return []


def main() -> None:
    env = load_dotenv()
    binance = BinanceMarketClient()
    sodex = SoDEXMarketClient()

    payloads: dict[str, dict[str, object]] = {}
    for asset, config in BTC_ETH_QUICK_TRADE_CONFIG.items():
        payloads[asset.lower()] = build_quick_trade_input_payload(
            asset=asset,
            symbol=str(config["symbol"]),
            sodex_symbol=str(config["sodex_symbol"]),
            klines_5m=_safe_perps_klines(sodex, asset=asset, symbol=str(config["sodex_symbol"]), interval="5m", limit=288),
            klines_15m=_safe_perps_klines(sodex, asset=asset, symbol=str(config["sodex_symbol"]), interval="15m", limit=192),
            klines_1h=_safe_perps_klines(sodex, asset=asset, symbol=str(config["sodex_symbol"]), interval="1h", limit=168),
            funding_rows=_safe_funding_rates(binance, asset=asset, symbol=str(config["symbol"]), limit=24),
            long_short_rows=_safe_long_short_ratio(binance, asset=asset, symbol=str(config["symbol"]), period="1h", limit=24),
            open_interest_rows=_safe_open_interest(binance, asset=asset, symbol=str(config["symbol"]), period="5m", limit=48),
        )

    published_to_supabase = False
    supabase_errors: list[dict[str, str]] = []
    supabase_url = env.get("SUPABASE_URL", "")
    supabase_service_role_key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if supabase_url and supabase_service_role_key:
        publisher = SupabasePublisher(supabase_url, supabase_service_role_key)
        for asset, payload in payloads.items():
            try:
                publisher.upsert_site_cache(
                    cache_key=f"quick_trade_inputs_{asset}",
                    payload=payload,
                    source="quick_trade_engine",
                    refresh_interval_minutes=15,
                )
            except HTTPError as exc:
                message = describe_http_error(exc)
                print(f"[warn] Supabase quick trade cache upsert failed for {asset}: {message}")
                supabase_errors.append({"asset": asset, "step": "quick_trade_site_cache", "error": message})
            except Exception as exc:
                message = str(exc)
                print(f"[warn] Supabase quick trade cache upsert failed for {asset}: {message}")
                supabase_errors.append({"asset": asset, "step": "quick_trade_site_cache", "error": message})
        published_to_supabase = True

    print(
        json.dumps(
            {
                "quick_trade_inputs": payloads,
                "supabase_errors": supabase_errors,
                "published_to_supabase": published_to_supabase,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
