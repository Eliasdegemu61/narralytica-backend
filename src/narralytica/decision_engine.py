from __future__ import annotations

import json
from math import ceil
from typing import Any


CONVICTION_LEVELS = ("low", "medium", "high")


def _components_by_name(signal: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index signal components by name for simpler decision rules."""
    return {component["name"]: component for component in signal["components"]}


def _base_bias_and_conviction(total_score: int) -> tuple[str, str]:
    """Map total score into the base market bias and conviction bucket."""
    if total_score >= 8:
        return "long", "high"
    if 4 <= total_score <= 7:
        return "long", "medium"
    if -3 <= total_score <= 3:
        return "neutral", "low"
    if -7 <= total_score <= -4:
        return "short", "medium"
    return "short", "high"


def _agreement_state(components: dict[str, dict[str, Any]]) -> tuple[str, str | None]:
    """Classify component agreement as strong or mixed."""
    bullish_count = sum(1 for component in components.values() if component["label"] == "bullish")
    bearish_count = sum(1 for component in components.values() if component["label"] == "bearish")
    threshold = max(3, ceil(len(components) * 0.625))

    if bullish_count >= threshold:
        return "strong", "bullish"
    if bearish_count >= threshold:
        return "strong", "bearish"
    return "mixed", None


def _downgrade_conviction(conviction: str) -> str:
    """Downgrade conviction by one step when agreement is mixed."""
    index = CONVICTION_LEVELS.index(conviction)
    return CONVICTION_LEVELS[max(0, index - 1)]


def _position_size_bucket(action: str, conviction: str) -> str:
    """Convert conviction into a size bucket with wait capped at small."""
    if action == "wait":
        return "small"
    if conviction == "high":
        return "large"
    if conviction == "medium":
        return "medium"
    return "small"


def _funding_is_strongly_bearish(funding_component: dict[str, Any]) -> bool:
    """Return True when funding meaningfully argues against longs."""
    return funding_component["score"] <= -2


def _funding_is_extremely_negative(funding_component: dict[str, Any]) -> bool:
    """Return True when funding is already deeply negative for shorts."""
    details = funding_component["details"]
    return details["latest_funding_rate"] <= -details["extreme_threshold"]


def _build_why(
    action: str,
    market_bias: str,
    agreement: str,
    components: dict[str, dict[str, Any]],
) -> list[str]:
    """Generate short human-readable reasons for the selected decision."""
    reasons: list[str] = []
    reason_map = {
        "etf_trend": {
            "bullish": "ETF trend is bullish",
            "bearish": "ETF trend is bearish",
        },
        "price_confirmation": {
            "bullish": "price confirmation is supportive",
            "bearish": "price confirmation is weakening",
        },
        "positioning": {
            "bullish": "positioning is supporting the long side",
            "bearish": "positioning is favoring the short side",
        },
        "funding_rates": {
            "bullish": "funding is not overcrowded against longs",
            "bearish": "funding is less supportive for aggressive leverage",
        },
        "futures_open_interest": {
            "bullish": "open interest is confirming the move",
            "bearish": "open interest is building against weak price",
        },
        "depth_asymmetry": {
            "bullish": "spot depth is more resilient on the downside",
            "bearish": "spot depth looks fragile on the downside",
        },
        "breadth_regime": {
            "bullish": "breadth is supporting the asset move",
            "bearish": "breadth is diverging against the asset move",
        },
        "fear_greed": {
            "bullish": "fear is elevated but stabilizing",
            "bearish": "greed is stretched",
        },
    }

    priority = (
        "etf_trend",
        "price_confirmation",
        "futures_open_interest",
        "depth_asymmetry",
        "positioning",
        "funding_rates",
        "breadth_regime",
        "fear_greed",
    )
    for component_name in priority:
        component = components[component_name]
        message = reason_map[component_name].get(component["label"])
        if message:
            reasons.append(message)

    if agreement == "mixed":
        reasons.append("signals are mixed across components")

    if action == "wait" and market_bias == "neutral":
        reasons.append("overall score does not show a strong directional edge")

    return reasons[:4]


def _build_invalidations(action: str, market_bias: str, components: dict[str, dict[str, Any]]) -> list[str]:
    """Generate simple rule-based invalidation conditions."""
    invalidations: list[str] = []

    if action in {"spot_long", "perps_long"}:
        invalidations.append("price component flips bearish")
        invalidations.append("ETF 5-day flow turns negative")
        invalidations.append("depth asymmetry turns bearish")
        invalidations.append("open interest starts building against price")
    elif action == "perps_short":
        invalidations.append("price component flips bullish")
        invalidations.append("positioning stops supporting the short")
        invalidations.append("depth asymmetry turns bullish")
        invalidations.append("funding becomes too negative for fresh shorts")
    else:
        if market_bias == "long":
            invalidations.append("price confirmation turns clearly bullish with stronger agreement")
            invalidations.append("depth asymmetry improves materially")
        elif market_bias == "short":
            invalidations.append("price confirmation turns clearly bearish with stronger agreement")
            invalidations.append("breadth deteriorates further against the asset")
        else:
            invalidations.append("at least 5 components align in one direction")
            invalidations.append("total score moves out of the neutral band")

    return invalidations[:4]


def decide_from_signal(signal: dict[str, Any]) -> dict[str, Any]:
    """Turn a signal snapshot into one of four explicit trading actions."""
    total_score = signal["total_score"]
    components = _components_by_name(signal)
    market_bias, conviction = _base_bias_and_conviction(total_score)
    agreement, agreement_direction = _agreement_state(components)

    if agreement == "mixed":
        conviction = _downgrade_conviction(conviction)

    etf = components["etf_trend"]
    price = components["price_confirmation"]
    positioning = components["positioning"]
    funding = components["funding_rates"]
    open_interest = components["futures_open_interest"]
    depth = components["depth_asymmetry"]

    action = "wait"
    if (
        total_score >= 8
        and price["label"] == "bullish"
        and depth["label"] != "bearish"
        and open_interest["label"] in {"bullish", "neutral"}
        and funding["label"] in {"bullish", "neutral"}
        and agreement == "strong"
        and agreement_direction == "bullish"
        and market_bias == "long"
        and conviction != "low"
    ):
        action = "perps_long"
    elif (
        total_score >= 4
        and etf["label"] == "bullish"
        and price["label"] != "bearish"
        and depth["label"] != "bearish"
        and not _funding_is_strongly_bearish(funding)
        and market_bias == "long"
        and conviction != "low"
    ):
        action = "spot_long"
    elif (
        total_score <= -8
        and price["label"] == "bearish"
        and positioning["label"] == "bearish"
        and depth["label"] == "bearish"
        and not _funding_is_extremely_negative(funding)
        and agreement == "strong"
        and agreement_direction == "bearish"
        and market_bias == "short"
        and conviction != "low"
    ):
        action = "perps_short"

    setup = "trend_follow" if action != "wait" else "wait"
    decision = {
        "asset": signal["asset"],
        "market_bias": market_bias,
        "conviction": conviction,
        "action": action,
        "setup": setup,
        "position_size_bucket": _position_size_bucket(action, conviction),
        "why": _build_why(action, market_bias, agreement, components),
        "invalidations": _build_invalidations(action, market_bias, components),
    }
    return decision


if __name__ == "__main__":
    example_signal = {
        "asset": "BTC",
        "total_score": 8,
        "components": [
            {"name": "etf_trend", "label": "bullish", "score": 3, "details": {}},
            {"name": "positioning", "label": "bullish", "score": 1, "details": {}},
            {"name": "price_confirmation", "label": "bullish", "score": 2, "details": {}},
            {"name": "funding_rates", "label": "neutral", "score": 0, "details": {"latest_funding_rate": 0.0, "extreme_threshold": 0.0001}},
            {"name": "futures_open_interest", "label": "bullish", "score": 2, "details": {}},
            {"name": "depth_asymmetry", "label": "bullish", "score": 1, "details": {}},
            {"name": "breadth_regime", "label": "neutral", "score": 0, "details": {}},
            {"name": "fear_greed", "label": "neutral", "score": 0, "details": {}},
        ],
    }
    print(json.dumps(decide_from_signal(example_signal), indent=2))
