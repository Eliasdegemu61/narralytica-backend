from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


BTC_ETH_QUICK_TRADE_CONFIG: dict[str, dict[str, Any]] = {
    "BTC": {
        "symbol": "BTCUSDT",
        "sodex_symbol": "BTC-USD",
    },
    "ETH": {
        "symbol": "ETHUSDT",
        "sodex_symbol": "ETH-USD",
    },
}

REFRESH_INTERVAL_MINUTES = 15
CLIENT_MAX_DATA_AGE_MINUTES = 10
CLIENT_REFRESH_BUFFER_MINUTES = 1


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_kline_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "open_time_ms": _safe_int(row.get("t")),
        "open": _safe_float(row.get("o")),
        "high": _safe_float(row.get("h")),
        "low": _safe_float(row.get("l")),
        "close": _safe_float(row.get("c")),
        "base_volume": _safe_float(row.get("v")),
        "quote_volume": _safe_float(row.get("a")),
        "symbol": row.get("s"),
    }


def _normalize_funding_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "funding_time_ms": _safe_int(row.get("fundingTime")),
        "funding_rate": _safe_float(row.get("fundingRate")),
        "mark_price": _safe_float(row.get("markPrice")),
        "symbol": row.get("symbol"),
    }


def _normalize_long_short_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_ms": _safe_int(row.get("timestamp")),
        "long_short_ratio": _safe_float(row.get("longShortRatio")),
        "long_account_share": _safe_float(row.get("longAccount")),
        "short_account_share": _safe_float(row.get("shortAccount")),
        "symbol": row.get("symbol"),
    }


def _normalize_open_interest_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "timestamp_ms": _safe_int(row.get("timestamp")),
        "sum_open_interest": _safe_float(row.get("sumOpenInterest")),
        "sum_open_interest_value": _safe_float(row.get("sumOpenInterestValue")),
        "symbol": row.get("symbol"),
    }


def _strategy_playbook() -> dict[str, Any]:
    return {
        "breakout_continuation": {
            "label": "Breakout Continuation",
            "purpose": "Catch fresh range breaks with follow-through.",
            "primary_timeframe": "5m",
            "confirmation_timeframe": "15m",
            "client_rules": {
                "range_lookback_candles_5m": 12,
                "close_buffer_pct": 0.0004,
                "follow_through_candles": 2,
                "volume_sma_candles": 20,
            },
        },
        "trend_pullback": {
            "label": "Trend Pullback",
            "purpose": "Join an existing trend after a controlled pullback.",
            "primary_timeframe": "15m",
            "confirmation_timeframe": "1h",
            "client_rules": {
                "trend_sma_fast": 20,
                "trend_sma_slow": 50,
                "reclaim_sma": 20,
                "max_pullback_pct_from_fast_sma": 0.006,
            },
        },
        "failed_break_reclaim": {
            "label": "Failed Break / Reclaim",
            "purpose": "Trade fast reversals after a liquidity sweep.",
            "primary_timeframe": "5m",
            "confirmation_timeframe": "15m",
            "client_rules": {
                "sweep_lookback_candles_5m": 20,
                "reclaim_close_buffer_pct": 0.0003,
                "reversal_follow_through_candles": 2,
            },
        },
        "funding_oi_confirmation": {
            "label": "Funding + OI Confirmation",
            "purpose": "Confirm price moves with derivatives positioning context.",
            "primary_timeframe": "5m",
            "confirmation_timeframe": "5m",
            "client_rules": {
                "open_interest_change_window": 6,
                "open_interest_expansion_pct": 0.8,
                "funding_overheat_threshold": 0.0001,
                "long_short_ratio_ceiling": 1.35,
                "long_short_ratio_floor": 0.75,
            },
        },
    }


def build_quick_trade_input_payload(
    *,
    asset: str,
    symbol: str,
    sodex_symbol: str,
    klines_5m: list[dict[str, Any]],
    klines_15m: list[dict[str, Any]],
    klines_1h: list[dict[str, Any]],
    funding_rows: list[dict[str, Any]],
    long_short_rows: list[dict[str, Any]],
    open_interest_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    snapshot_at = _utc_now()
    fresh_until = snapshot_at + timedelta(minutes=CLIENT_MAX_DATA_AGE_MINUTES)
    next_expected_update_at = snapshot_at + timedelta(minutes=REFRESH_INTERVAL_MINUTES)
    wait_until = next_expected_update_at + timedelta(minutes=CLIENT_REFRESH_BUFFER_MINUTES)

    latest_close = None
    if klines_5m:
        latest_close = _safe_float(klines_5m[-1].get("c"))

    return {
        "engine": "quick_trade_inputs_v1",
        "updated_at": _iso(snapshot_at),
        "asset": asset,
        "symbol": symbol,
        "market": "perps",
        "sodex_symbol": sodex_symbol,
        "server_schedule": {
            "refresh_interval_minutes": REFRESH_INTERVAL_MINUTES,
            "client_max_data_age_minutes": CLIENT_MAX_DATA_AGE_MINUTES,
            "client_refresh_buffer_minutes": CLIENT_REFRESH_BUFFER_MINUTES,
            "fresh_until": _iso(fresh_until),
            "next_expected_update_at": _iso(next_expected_update_at),
            "wait_for_next_refresh_until": _iso(wait_until),
            "client_rule": "If snapshot age is greater than 10 minutes, do not open a new quick trade. Wait until wait_for_next_refresh_until before trusting a new setup.",
        },
        "latest_context": {
            "reference_price": latest_close,
            "reference_price_source": "sodex_perps_5m",
        },
        "datasets": {
            "klines": {
                "5m": [_normalize_kline_row(row) for row in klines_5m],
                "15m": [_normalize_kline_row(row) for row in klines_15m],
                "1h": [_normalize_kline_row(row) for row in klines_1h],
            },
            "funding_rates": [_normalize_funding_row(row) for row in funding_rows],
            "long_short_ratio_1h": [_normalize_long_short_row(row) for row in long_short_rows],
            "open_interest_5m": [_normalize_open_interest_row(row) for row in open_interest_rows],
        },
        "strategy_playbook": _strategy_playbook(),
    }
