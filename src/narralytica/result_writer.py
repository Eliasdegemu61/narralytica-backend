from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    """Return a simple UTC timestamp string for result files."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _local_snapshot_stamp() -> str:
    """Return a filesystem-friendly local timestamp for snapshot folders."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def _component_map(signal: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index components by name for easier story building."""
    return {component["name"]: component for component in signal["components"]}


def _snapshot_metadata(signal: dict[str, Any]) -> dict[str, Any]:
    """Return top-level snapshot fields needed for later performance tracking."""
    price_component = _component_map(signal)["price_confirmation"]
    details = price_component["details"]
    return {
        "snapshot_time_utc": _utc_now_iso(),
        "asset": signal["asset"],
        "reference_price": details.get("latest_close"),
        "reference_price_date": details.get("latest_date"),
        "price_source": details.get("source", "unknown"),
    }


def _visual_score(component: dict[str, Any]) -> int:
    """Convert component score/label into a UI-friendly 0-100 meter."""
    label = component["label"]
    score = component["score"]

    if label == "bullish":
        return min(95, 55 + score * 15)
    if label == "bearish":
        return max(5, 45 + score * 15)
    if label == "unavailable":
        return 50
    return 50


def _component_story(component: dict[str, Any]) -> dict[str, Any]:
    """Build a presentation-friendly component card."""
    name = component["name"]
    details = component["details"]
    is_unavailable = component["label"] == "unavailable"

    if name == "etf_trend":
        summary = (
            "ETF data is unavailable for this asset."
            if is_unavailable
            else "ETF flows remain supportive."
            if component["label"] == "bullish"
            else "ETF flow momentum is fading."
        )
        calc_hint = "Latest ETF flow and the recent 5-period aggregate are used to frame institutional demand."
        evidence = {
            "latest_date": details.get("latest_date"),
            "latest_net_inflow_usd": details.get("latest_net_inflow_usd"),
            "five_day_net_inflow_usd": details.get("five_day_net_inflow_usd"),
            "positive_days_last_5": details.get("positive_days_last_5"),
            "reason": details.get("reason"),
        }
        title = "ETF Trend"
    elif name == "positioning":
        summary = (
            "Positioning data is unavailable for this asset."
            if is_unavailable
            else "Positioning supports the long side."
            if component["label"] == "bullish"
            else "Short-side positioning still dominates."
            if component["label"] == "bearish"
            else "Positioning is balanced rather than directional."
        )
        calc_hint = "The latest long-short ratio is compared with both 1.0 and its recent average."
        evidence = {
            "latest_date": details.get("latest_date"),
            "latest_long_short_ratio": details.get("latest_long_short_ratio"),
            "latest_long_account_share": details.get("latest_long_account_share"),
            "latest_short_account_share": details.get("latest_short_account_share"),
            "average_ratio_sample": details.get("average_ratio_sample"),
            "reason": details.get("reason"),
        }
        title = "Positioning"
    elif name == "price_confirmation":
        summary = (
            "Price data is unavailable for this asset."
            if is_unavailable
            else "Price is confirming momentum."
            if component["label"] == "bullish"
            else "Price action is weakening."
            if component["label"] == "bearish"
            else "Price is holding without full confirmation."
        )
        calc_hint = "Recent close, daily return, and short moving averages are compared for confirmation."
        evidence = {
            "latest_date": details.get("latest_date"),
            "latest_close": details.get("latest_close"),
            "daily_return_pct": details.get("daily_return_pct"),
            "sample_return_pct": details.get("sample_return_pct"),
            "sma_3": details.get("sma_3"),
            "sma_5": details.get("sma_5"),
            "source": details.get("source"),
            "reason": details.get("reason"),
        }
        title = "Price Confirmation"
    elif name == "funding_rates":
        summary = (
            "Funding data is unavailable for this asset."
            if is_unavailable
            else "Funding is easing crowding pressure."
            if component["label"] == "bullish"
            else "Funding argues against aggressive leverage."
            if component["label"] == "bearish"
            else "Funding is not showing a strong edge."
        )
        calc_hint = "Latest funding is compared with both an extreme threshold and the recent average."
        evidence = {
            "latest_time": details.get("latest_time"),
            "latest_funding_rate": details.get("latest_funding_rate"),
            "average_funding_rate_sample": details.get("average_funding_rate_sample"),
            "extreme_threshold": details.get("extreme_threshold"),
            "sample_size": details.get("sample_size"),
            "mark_price": details.get("mark_price"),
            "reason": details.get("reason"),
        }
        title = "Funding"
    elif name == "futures_open_interest":
        summary = (
            "Open-interest data is unavailable for this asset."
            if is_unavailable
            else "Open interest is confirming price participation."
            if component["label"] == "bullish"
            else "Open interest is building against weak price."
            if component["label"] == "bearish"
            else "Open interest is not giving a strong edge."
        )
        calc_hint = "Recent total open interest is compared with price direction to detect leverage support or crowding."
        evidence = {
            "latest_date": details.get("latest_date"),
            "latest_open_interest": details.get("latest_open_interest"),
            "previous_open_interest": details.get("previous_open_interest"),
            "open_interest_change_pct": details.get("open_interest_change_pct"),
            "latest_reference_price": details.get("latest_reference_price"),
            "reference_price_change_pct": details.get("reference_price_change_pct"),
            "binance_open_interest": details.get("binance_open_interest"),
            "cme_open_interest": details.get("cme_open_interest"),
            "reason": details.get("reason"),
        }
        title = "Futures Open Interest"
    elif name == "depth_asymmetry":
        summary = (
            "Pair-depth data is unavailable for this asset."
            if is_unavailable
            else "Spot depth is more resilient on the downside."
            if component["label"] == "bullish"
            else "Spot depth looks fragile on the downside."
            if component["label"] == "bearish"
            else "Spot depth is balanced rather than directional."
        )
        calc_hint = "Turnover-weighted pair depth compares the cost to move price down versus up by 2%."
        evidence = {
            "depth_ratio": details.get("depth_ratio"),
            "weighted_cost_to_move_up_usd": details.get("weighted_cost_to_move_up_usd"),
            "weighted_cost_to_move_down_usd": details.get("weighted_cost_to_move_down_usd"),
            "markets_used": details.get("markets_used"),
            "reason": details.get("reason"),
        }
        title = "Depth Asymmetry"
    elif name == "breadth_regime":
        summary = (
            "Breadth data is unavailable for this asset."
            if is_unavailable
            else "Breadth is supporting the asset move."
            if component["label"] == "bullish"
            else "Breadth is diverging against the asset move."
            if component["label"] == "bearish"
            else "Breadth is mixed across sectors and indices."
        )
        calc_hint = "Relevant sector performance and index snapshots are used to judge whether the move is broad or narrow."
        evidence = {
            "sector_name": details.get("sector_name"),
            "sector_change_pct_24h": details.get("sector_change_pct_24h"),
            "sector_marketcap_dom": details.get("sector_marketcap_dom"),
            "index_snapshots": details.get("index_snapshots"),
            "reason": details.get("reason"),
        }
        title = "Breadth Regime"
    elif name == "fear_greed":
        summary = (
            "Fear & greed data is unavailable."
            if is_unavailable
            else "Fear is elevated but stabilizing."
            if component["label"] == "bullish"
            else "Greed is stretched."
            if component["label"] == "bearish"
            else "Sentiment is not at an extreme."
        )
        calc_hint = "Fear & greed is used as a light regime filter rather than a primary trigger."
        evidence = {
            "latest_date": details.get("latest_date"),
            "latest_index_value": details.get("latest_index_value"),
            "previous_index_value": details.get("previous_index_value"),
            "reason": details.get("reason"),
        }
        title = "Fear & Greed"
    else:
        summary = "Component state unavailable."
        calc_hint = "Derived from the current signal engine."
        evidence = details
        title = name

    return {
        "name": title,
        "state": component["label"],
        "score": component["score"],
        "score_display": "Unavailable" if is_unavailable else component["score"],
        "visual_score": _visual_score(component),
        "summary": summary,
        "calc_hint": calc_hint,
        "evidence": evidence,
    }


def build_signal_story(signal: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Build a presentation-friendly explanation file for the website layer."""
    components = _component_map(signal)
    bullish = [component["name"] for component in signal["components"] if component["label"] == "bullish"]
    bearish = [component["name"] for component in signal["components"] if component["label"] == "bearish"]
    title_map = {
        "etf_trend": "ETF Trend",
        "positioning": "Positioning",
        "price_confirmation": "Price Confirmation",
        "funding_rates": "Funding",
        "futures_open_interest": "Futures Open Interest",
        "depth_asymmetry": "Depth Asymmetry",
        "breadth_regime": "Breadth Regime",
        "fear_greed": "Fear & Greed",
    }

    action = decision["action"]
    if action == "spot_long":
        headline_title = f'{signal["asset"]} favors spot accumulation'
        headline_summary = "Institutional flow is supportive, but the setup is cleaner for spot than for leverage."
    elif action == "perps_long":
        headline_title = f'{signal["asset"]} favors leveraged upside'
        headline_summary = "Directional components are aligned enough to support a trend-following perps long."
    elif action == "perps_short":
        headline_title = f'{signal["asset"]} favors downside continuation'
        headline_summary = "Bearish components are aligned enough to justify a trend-following perps short."
    else:
        headline_title = f'{signal["asset"]} remains in wait mode'
        headline_summary = "The engine sees useful information, but not enough clean alignment for action."

    return {
        "asset": signal["asset"],
        "updated_at": _utc_now_iso(),
        "headline": {
            "title": headline_title,
            "summary": headline_summary,
        },
        "component_cards": [_component_story(component) for component in signal["components"]],
        "decision_summary": {
            "action": decision["action"],
            "market_bias": decision["market_bias"],
            "conviction": decision["conviction"],
            "setup": decision["setup"],
            "position_size_bucket": decision["position_size_bucket"],
            "summary": " | ".join(decision["why"]),
        },
        "evidence": {
            "total_score": signal["total_score"],
            "overall_signal": signal["overall_signal"],
            "supporting_components": [title_map.get(name, name) for name in bullish],
            "opposing_components": [title_map.get(name, name) for name in bearish],
            "raw_data_used": {
                "etf": components["etf_trend"]["details"],
                "positioning": components["positioning"]["details"],
                "price": components["price_confirmation"]["details"],
                "funding": components["funding_rates"]["details"],
                "open_interest": components["futures_open_interest"]["details"],
                "depth": components["depth_asymmetry"]["details"],
                "breadth": components["breadth_regime"]["details"],
                "fear_greed": components["fear_greed"]["details"],
            },
            "calculation_notes": {
                "etf": "ETF trend uses the latest flow and the recent 5-period aggregate.",
                "positioning": "Positioning compares the latest long-short ratio with 1.0 and its recent sample average.",
                "price": "Price confirmation uses the latest close, daily return, and short moving averages from recent daily candles.",
                "funding": "Funding compares the latest print with an extreme threshold and with the recent funding average.",
                "open_interest": "Open interest compares recent aggregate futures interest with price direction for leverage confirmation.",
                "depth": "Depth asymmetry uses turnover-weighted pair depth to compare downside support against upside resistance.",
                "breadth": "Breadth compares the asset sector and relevant SoSoValue indices to determine whether the move is broad or narrow.",
                "fear_greed": "Fear & greed is used as a light sentiment filter at emotional extremes.",
            },
        },
        "why": decision["why"],
        "invalidations": decision["invalidations"],
    }


def build_enriched_output(output: dict[str, Any]) -> dict[str, Any]:
    """Attach snapshot metadata before writing or publishing outputs."""
    return {
        "snapshot": _snapshot_metadata(output["signal"]),
        **output,
    }


def write_result_files(asset: str, output: dict[str, Any], *, root: str | Path = "results") -> dict[str, str]:
    """Write machine output and presentation story files for an asset."""
    asset_dir = Path(root) / asset.lower()
    asset_dir.mkdir(parents=True, exist_ok=True)

    signal_output_path = asset_dir / "signal_output.json"
    signal_story_path = asset_dir / "signal_story.json"

    enriched_output = build_enriched_output(output)

    signal_output_path.write_text(json.dumps(enriched_output, indent=2), encoding="utf-8")
    signal_story_path.write_text(
        json.dumps(build_signal_story(output["signal"], output["decision"]), indent=2),
        encoding="utf-8",
    )

    return {
        "signal_output": str(signal_output_path),
        "signal_story": str(signal_story_path),
    }
