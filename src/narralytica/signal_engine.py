from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean
from typing import Any


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)


def _timestamp_ms_to_iso(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


@dataclass
class SignalComponent:
    name: str
    score: int
    label: str
    details: dict[str, Any]


ASSET_CONFIG = {
    "BTC": {
        "symbol": "BTCUSDT",
        "etf_type": "us-btc-spot",
        "has_etf": True,
        "currency_id": "1673723677362319866",
        "sector_name": "BTC",
        "index_tickers": ("ssiMAG7", "ssiCeFi"),
    },
    "ETH": {
        "symbol": "ETHUSDT",
        "etf_type": "us-eth-spot",
        "has_etf": True,
        "currency_id": "1673723677362319867",
        "sector_name": "ETH",
        "index_tickers": ("ssiLayer1", "ssiDeFi"),
    },
    "SOL": {
        "symbol": "SOLUSDT",
        "etf_type": None,
        "has_etf": False,
        "currency_id": None,
        "sector_name": "Layer1",
        "index_tickers": ("ssiLayer1",),
    },
}

FUNDING_EXTREME_THRESHOLD = 0.0001
ETF_WEIGHTED_STRONG_SCORE = 3
ETF_CONTRADICTION_CAP_SCORE = 2


def _label_from_score(score: int) -> str:
    if score > 0:
        return "bullish"
    if score < 0:
        return "bearish"
    return "neutral"


def summarize_etf_trend(rows: list[dict[str, Any]]) -> SignalComponent:
    if not rows:
        raise ValueError("ETF historical data is empty")

    latest = rows[0]
    recent = rows[:5]
    latest_inflow = _to_float(latest["totalNetInflow"])
    recent_inflows = [_to_float(row["totalNetInflow"]) for row in recent]
    positive_days = sum(1 for value in recent_inflows if value > 0)
    five_day_sum = sum(recent_inflows)

    score = 0
    if latest_inflow > 0:
        score += 1
    elif latest_inflow < 0:
        score -= 1

    if five_day_sum > 0:
        score += 1
    elif five_day_sum < 0:
        score -= 1

    return SignalComponent(
        name="etf_trend",
        score=score,
        label=_label_from_score(score),
        details={
            "latest_date": latest["date"],
            "latest_net_inflow_usd": latest_inflow,
            "five_day_net_inflow_usd": five_day_sum,
            "positive_days_last_5": positive_days,
        },
    )


def summarize_missing_etf(asset: str) -> SignalComponent:
    return SignalComponent(
        name="etf_trend",
        score=0,
        label="unavailable",
        details={
            "asset": asset,
            "reason": "No ETF source configured for this asset",
        },
    )


def summarize_positioning(rows: list[dict[str, Any]]) -> SignalComponent:
    if not rows:
        raise ValueError("Binance positioning data is empty")

    latest = rows[-1]
    ratios = [_to_float(row["longShortRatio"]) for row in rows]
    latest_ratio = _to_float(latest["longShortRatio"])
    avg_ratio = mean(ratios)

    score = 0
    if latest_ratio > 1.0:
        score += 1
    elif latest_ratio < 0.95:
        score -= 1

    if latest_ratio > avg_ratio:
        score += 1
    elif latest_ratio < avg_ratio:
        score -= 1

    return SignalComponent(
        name="positioning",
        score=score,
        label=_label_from_score(score),
        details={
            "latest_date": _timestamp_ms_to_iso(int(latest["timestamp"])),
            "latest_long_short_ratio": latest_ratio,
            "latest_long_account_share": _to_float(latest["longAccount"]),
            "latest_short_account_share": _to_float(latest["shortAccount"]),
            "average_ratio_sample": avg_ratio,
        },
    )


def summarize_sodex_price_confirmation(klines: list[dict[str, Any]]) -> SignalComponent:
    if len(klines) < 5:
        raise ValueError("At least 5 SoDEX klines are required for price confirmation")

    ordered = list(reversed(klines))
    closes = [float(row["c"]) for row in ordered]
    latest = ordered[-1]
    latest_close = float(latest["c"])
    latest_open = float(latest["o"])
    sma_3 = mean(closes[-3:])
    sma_5 = mean(closes)
    daily_return_pct = ((latest_close / latest_open) - 1.0) * 100.0
    sample_return_pct = ((closes[-1] / closes[0]) - 1.0) * 100.0

    score = 0
    if latest_close > sma_3:
        score += 1
    elif latest_close < sma_3:
        score -= 1

    if sma_3 > sma_5:
        score += 1
    elif sma_3 < sma_5:
        score -= 1

    return SignalComponent(
        name="price_confirmation",
        score=score,
        label=_label_from_score(score),
        details={
            "latest_date": _timestamp_ms_to_iso(int(latest["t"])),
            "latest_close": latest_close,
            "daily_return_pct": daily_return_pct,
            "sample_return_pct": sample_return_pct,
            "sma_3": sma_3,
            "sma_5": sma_5,
            "source": "sodex_perps_klines",
        },
    )


def summarize_funding_rates(rows: list[dict[str, Any]]) -> SignalComponent:
    if not rows:
        raise ValueError("Binance funding-rate data is empty")

    latest = rows[-1]
    latest_funding = _to_float(latest["fundingRate"])
    avg_funding = mean(_to_float(row["fundingRate"]) for row in rows)

    score = 0
    if latest_funding > FUNDING_EXTREME_THRESHOLD:
        score -= 1
    elif latest_funding < -FUNDING_EXTREME_THRESHOLD:
        score += 1

    if latest_funding > avg_funding:
        score -= 1
    elif latest_funding < avg_funding:
        score += 1

    return SignalComponent(
        name="funding_rates",
        score=score,
        label=_label_from_score(score),
        details={
            "latest_time": _timestamp_ms_to_iso(int(latest["fundingTime"])),
            "latest_funding_rate": latest_funding,
            "average_funding_rate_sample": avg_funding,
            "extreme_threshold": FUNDING_EXTREME_THRESHOLD,
            "sample_size": len(rows),
            "mark_price": _to_float(latest.get("markPrice")),
        },
    )


def summarize_fear_greed(rows: list[dict[str, Any]]) -> SignalComponent:
    if not rows:
        raise ValueError("Fear & greed data is empty")

    latest = rows[0]
    latest_value = _to_float(latest["crypto_fear_&_greed_index"])
    previous_value = _to_float(rows[1]["crypto_fear_&_greed_index"]) if len(rows) > 1 else latest_value

    score = 0
    if latest_value <= 25 and latest_value >= previous_value:
        score = 1
    elif latest_value >= 75 and latest_value >= previous_value:
        score = -1

    return SignalComponent(
        name="fear_greed",
        score=score,
        label=_label_from_score(score),
        details={
            "latest_date": _timestamp_ms_to_iso(int(latest["timestamp"])),
            "latest_index_value": latest_value,
            "previous_index_value": previous_value,
        },
    )


def summarize_futures_open_interest(rows: list[dict[str, Any]]) -> SignalComponent:
    if len(rows) < 2:
        raise ValueError("At least 2 futures open-interest rows are required")

    latest = rows[0]
    previous = rows[1]
    latest_oi = _to_float(latest["all"])
    previous_oi = _to_float(previous["all"])
    latest_price = _to_float(latest["btc_price"])
    previous_price = _to_float(previous["btc_price"])
    oi_change_pct = ((latest_oi / previous_oi) - 1.0) * 100.0 if previous_oi else 0.0
    price_change_pct = ((latest_price / previous_price) - 1.0) * 100.0 if previous_price else 0.0

    score = 0
    if oi_change_pct > 1.0 and price_change_pct >= 0:
        score = 2
    elif oi_change_pct > 0.5 and price_change_pct >= -0.5:
        score = 1
    elif oi_change_pct > 1.0 and price_change_pct < -0.5:
        score = -2
    elif oi_change_pct > 0.5 and price_change_pct < 0:
        score = -1

    return SignalComponent(
        name="futures_open_interest",
        score=score,
        label=_label_from_score(score),
        details={
            "latest_date": _timestamp_ms_to_iso(int(latest["timestamp"])),
            "latest_open_interest": latest_oi,
            "previous_open_interest": previous_oi,
            "open_interest_change_pct": oi_change_pct,
            "latest_reference_price": latest_price,
            "reference_price_change_pct": price_change_pct,
            "binance_open_interest": _to_float(latest.get("binance")),
            "cme_open_interest": _to_float(latest.get("cme")),
        },
    )


def summarize_depth_asymmetry(asset: str, rows: list[dict[str, Any]]) -> SignalComponent:
    if not rows:
        raise ValueError("Trading pair depth data is empty")

    top_rows = sorted(rows, key=lambda row: _to_float(row["turnover_24h"]), reverse=True)[:5]
    total_turnover = sum(_to_float(row["turnover_24h"]) for row in top_rows) or 1.0

    weighted_up = 0.0
    weighted_down = 0.0
    markets: list[dict[str, Any]] = []
    for row in top_rows:
        turnover = _to_float(row["turnover_24h"])
        weight = turnover / total_turnover
        move_up = _to_float(row["cost_to_move_up_usd"])
        move_down = _to_float(row["cost_to_move_down_usd"])
        weighted_up += move_up * weight
        weighted_down += move_down * weight
        markets.append(
            {
                "market": row["market"],
                "price": _to_float(row["price"]),
                "turnover_24h": turnover,
                "cost_to_move_up_usd": move_up,
                "cost_to_move_down_usd": move_down,
            }
        )

    depth_ratio = weighted_down / weighted_up if weighted_up else 1.0
    if depth_ratio >= 1.20:
        score = 2
    elif depth_ratio >= 1.05:
        score = 1
    elif depth_ratio > 0.94:
        score = 0
    elif depth_ratio >= 0.80:
        score = -1
    else:
        score = -2

    return SignalComponent(
        name="depth_asymmetry",
        score=score,
        label=_label_from_score(score),
        details={
            "asset": asset,
            "depth_ratio": depth_ratio,
            "weighted_cost_to_move_up_usd": weighted_up,
            "weighted_cost_to_move_down_usd": weighted_down,
            "markets_used": markets,
        },
    )


def _get_sector_row(sector_payload: dict[str, Any], sector_name: str) -> dict[str, Any] | None:
    sectors = sector_payload.get("sector", [])
    if not isinstance(sectors, list):
        return None
    for row in sectors:
        if str(row.get("name", "")).strip().upper() == sector_name.upper():
            return row
    return None


def summarize_breadth_regime(
    *,
    asset: str,
    sector_payload: dict[str, Any],
    index_snapshots: dict[str, dict[str, Any]],
) -> SignalComponent:
    config = ASSET_CONFIG[asset]
    sector_row = _get_sector_row(sector_payload, config["sector_name"])
    sector_change = _to_float(sector_row.get("change_pct_24h")) if sector_row else 0.0
    sector_dom = _to_float(sector_row.get("marketcap_dom")) if sector_row else 0.0
    relevant_snapshots = {ticker: snapshot for ticker, snapshot in index_snapshots.items() if snapshot}

    positive_index_count = sum(1 for snapshot in relevant_snapshots.values() if _to_float(snapshot.get("roi_7d")) > 0)
    negative_index_count = sum(1 for snapshot in relevant_snapshots.values() if _to_float(snapshot.get("roi_7d")) < 0)

    score = 0
    if sector_change > 0 and positive_index_count >= 1:
        score = 1
    elif sector_change < 0 and negative_index_count >= 1:
        score = -1

    return SignalComponent(
        name="breadth_regime",
        score=score,
        label=_label_from_score(score),
        details={
            "sector_name": config["sector_name"],
            "sector_change_pct_24h": sector_change,
            "sector_marketcap_dom": sector_dom,
            "index_snapshots": relevant_snapshots,
        },
    )


def _weighted_component_score(component: SignalComponent) -> int:
    """Convert raw component scores into the effective score used in totals."""
    if component.name == "etf_trend":
        if component.score >= 2:
            return ETF_WEIGHTED_STRONG_SCORE
        if component.score <= -2:
            return -ETF_WEIGHTED_STRONG_SCORE
    return component.score


def _apply_etf_price_conflict_rule(
    etf_component: SignalComponent,
    price_component: SignalComponent,
    weighted_scores: dict[str, int],
) -> dict[str, int]:
    """Reduce ETF influence when fast price action strongly disagrees."""
    adjusted = dict(weighted_scores)
    etf_score = adjusted.get(etf_component.name, 0)
    price_score = adjusted.get(price_component.name, 0)

    if etf_score >= ETF_CONTRADICTION_CAP_SCORE and price_score == -2:
        adjusted[etf_component.name] = ETF_CONTRADICTION_CAP_SCORE
    elif etf_score <= -ETF_CONTRADICTION_CAP_SCORE and price_score == 2:
        adjusted[etf_component.name] = -ETF_CONTRADICTION_CAP_SCORE

    return adjusted


def _finalize_signal_snapshot(asset: str, components: list[SignalComponent]) -> dict[str, Any]:
    """Build a signal payload from raw components and effective scoring rules."""
    weighted_scores = {component.name: _weighted_component_score(component) for component in components}
    component_map = {component.name: component for component in components}
    adjusted_scores = _apply_etf_price_conflict_rule(
        component_map["etf_trend"],
        component_map["price_confirmation"],
        weighted_scores,
    )

    total_score = sum(adjusted_scores.values())
    overall = "bullish" if total_score >= 4 else "bearish" if total_score <= -4 else "neutral"

    return {
        "asset": asset,
        "overall_signal": overall,
        "total_score": total_score,
        "components": [
            {
                "name": component.name,
                "label": component.label,
                "score": adjusted_scores[component.name],
                "details": {
                    **component.details,
                    "raw_score": component.score,
                    "effective_score": adjusted_scores[component.name],
                },
            }
            for component in components
        ],
    }


def build_asset_signal_snapshot(
    asset: str,
    *,
    etf_rows: list[dict[str, Any]] | None,
    positioning_rows: list[dict[str, Any]],
    klines: list[dict[str, Any]],
    funding_rows: list[dict[str, Any]],
    fear_greed_rows: list[dict[str, Any]],
    futures_open_interest_rows: list[dict[str, Any]],
    pair_rows: list[dict[str, Any]],
    sector_payload: dict[str, Any],
    index_snapshots: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    normalized_asset = asset.upper()
    etf_component = (
        summarize_etf_trend(etf_rows or [])
        if etf_rows is not None
        else summarize_missing_etf(normalized_asset)
    )
    positioning = summarize_positioning(positioning_rows)
    price = summarize_sodex_price_confirmation(klines)
    funding = summarize_funding_rates(funding_rows)
    fear_greed = summarize_fear_greed(fear_greed_rows)
    futures_open_interest = summarize_futures_open_interest(futures_open_interest_rows)
    depth_asymmetry = summarize_depth_asymmetry(normalized_asset, pair_rows)
    breadth_regime = summarize_breadth_regime(
        asset=normalized_asset,
        sector_payload=sector_payload,
        index_snapshots=index_snapshots,
    )

    return _finalize_signal_snapshot(
        normalized_asset,
        [
            etf_component,
            positioning,
            price,
            funding,
            futures_open_interest,
            depth_asymmetry,
            breadth_regime,
            fear_greed,
        ],
    )
