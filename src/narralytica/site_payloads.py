from __future__ import annotations

from datetime import datetime, timezone
import re
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


FOUR_HOUR_MS = 4 * 60 * 60 * 1000
NEWS_CATEGORY_LABELS = {
    1: "news",
    2: "research",
    3: "institution",
    4: "insight",
    7: "announcement",
    13: "crypto_stock_news",
}


def _iso_from_ms(timestamp_ms: int | None) -> str | None:
    if not timestamp_ms:
        return None
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    text = re.sub(r"<[^>]+>", " ", value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _display_title(row: dict[str, Any]) -> str:
    if row.get("source_type") == "macro_event":
        event_name = str(row.get("title", "") or "").strip()
        return event_name or "Macro event"

    title = str(row.get("title", "") or "").strip()
    if title:
        return title

    content_text = _strip_html(str(row.get("content", "") or ""))
    if content_text:
        return content_text[:117] + "..." if len(content_text) > 120 else content_text

    tags = row.get("tags", [])
    if isinstance(tags, list) and tags:
        return f"News update: {', '.join(str(tag) for tag in tags[:3])}"

    return "Untitled market update"


def _bucket_open_ms(timestamp_ms: int | None, *, bucket_ms: int = FOUR_HOUR_MS) -> int | None:
    if not timestamp_ms:
        return None
    return (timestamp_ms // bucket_ms) * bucket_ms


def _news_importance_score(row: dict[str, Any]) -> float:
    explicit_score = row.get("importance_score")
    if explicit_score is not None:
        try:
            return float(explicit_score)
        except (TypeError, ValueError):
            pass

    if row.get("source_type") == "macro_event":
        return float(row.get("importance_score", 60.0) or 60.0)

    category_weight = {
        7: 40.0,
        3: 30.0,
        2: 25.0,
        1: 18.0,
        4: 12.0,
        13: 10.0,
    }
    category = int(row.get("category", 0) or 0)
    impressions = float(row.get("impression_count", 0) or 0)
    likes = float(row.get("like_count", 0) or 0)
    replies = float(row.get("reply_count", 0) or 0)
    retweets = float(row.get("retweet_count", 0) or 0)
    tags = row.get("tags", [])
    matched = row.get("matched_currencies", [])

    return (
        category_weight.get(category, 8.0)
        + min(impressions / 1000.0, 25.0)
        + min((likes + replies + retweets) / 10.0, 15.0)
        + (5.0 if isinstance(tags, list) and tags else 0.0)
        + (5.0 if isinstance(matched, list) and matched else 0.0)
    )


def _normalize_news_row(asset: str, row: dict[str, Any]) -> dict[str, Any]:
    release_time_ms = int(row.get("release_time", 0) or 0)
    bucket_ms = _bucket_open_ms(release_time_ms)
    matched = row.get("matched_currencies", [])
    display_title = _display_title(row)
    content_text = _strip_html(str(row.get("content", "") or ""))
    source_type = str(row.get("source_type", "featured_news") or "featured_news")
    return {
        "id": str(row.get("id", "")),
        "asset": asset,
        "source_type": source_type,
        "title": display_title,
        "original_title": row.get("title", ""),
        "timestamp_ms": release_time_ms,
        "timestamp_iso": _iso_from_ms(release_time_ms),
        "bucket_open_ms_4h": bucket_ms,
        "bucket_open_iso_4h": _iso_from_ms(bucket_ms),
        "source_link": row.get("source_link"),
        "original_link": row.get("original_link"),
        "category": row.get("category"),
        "category_label": row.get("category_label") or NEWS_CATEGORY_LABELS.get(int(row.get("category", 0) or 0), "unknown"),
        "author": row.get("author"),
        "nick_name": row.get("nick_name"),
        "tags": row.get("tags", []),
        "matched_currencies": matched if isinstance(matched, list) else [],
        "feature_image": row.get("feature_image"),
        "content_excerpt": content_text[:237] + "..." if len(content_text) > 240 else content_text,
        "impression_count": row.get("impression_count", 0),
        "like_count": row.get("like_count", 0),
        "reply_count": row.get("reply_count", 0),
        "retweet_count": row.get("retweet_count", 0),
        "importance_score": _news_importance_score(row),
    }


def _annotated_news_sets(
    asset: str,
    news_rows: list[dict[str, Any]],
    *,
    major_limit: int,
    recent_limit: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    normalized = [_normalize_news_row(asset, row) for row in news_rows]
    recent_items = sorted(normalized, key=lambda item: item["timestamp_ms"], reverse=True)[:recent_limit]
    major_items = sorted(normalized, key=lambda item: item["importance_score"], reverse=True)[:major_limit]

    major_ids = {item["id"] for item in major_items}
    annotated_recent = [
        {
            **item,
            "is_major": item["id"] in major_ids,
        }
        for item in recent_items
    ]
    annotated_major = [
        {
            **item,
            "is_major": True,
        }
        for item in major_items
    ]
    annotated_all = [
        {
            **item,
            "is_major": item["id"] in major_ids,
        }
        for item in normalized
    ]
    return annotated_all, annotated_recent, annotated_major


def _group_news_markers(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for item in items:
        bucket_ms = item.get("bucket_open_ms_4h")
        if not bucket_ms:
            continue
        grouped.setdefault(int(bucket_ms), []).append(item)

    markers: list[dict[str, Any]] = []
    for bucket_ms, bucket_items in sorted(grouped.items()):
        sorted_items = sorted(bucket_items, key=lambda item: item["importance_score"], reverse=True)
        markers.append(
            {
                "bucket_open_ms_4h": bucket_ms,
                "bucket_open_iso_4h": _iso_from_ms(bucket_ms),
                "item_count": len(sorted_items),
                "top_title": sorted_items[0]["title"] if sorted_items else "",
                "titles": [item["title"] for item in sorted_items],
                "items": sorted_items,
            }
        )
    return markers


def build_market_overview_cache(
    *,
    fear_greed_rows: list[dict[str, Any]],
    futures_open_interest_rows: list[dict[str, Any]],
    sector_payload: dict[str, Any],
    etf_metrics: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Build a client-friendly cache payload for slow-changing market context."""
    latest_fear_greed = fear_greed_rows[0] if fear_greed_rows else {}
    previous_fear_greed = fear_greed_rows[1] if len(fear_greed_rows) > 1 else latest_fear_greed
    latest_open_interest = futures_open_interest_rows[0] if futures_open_interest_rows else {}

    return {
        "updated_at": _utc_now_iso(),
        "fear_greed": {
            "latest": latest_fear_greed,
            "previous": previous_fear_greed,
            "series": fear_greed_rows,
        },
        "futures_open_interest": {
            "latest": latest_open_interest,
            "series": futures_open_interest_rows,
        },
        "sector_spotlight": sector_payload,
        "etf_metrics": etf_metrics,
    }


def build_engine_summary_cache(outputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Build a lightweight summary payload for website hero sections."""
    assets: dict[str, Any] = {}
    for asset, output in outputs.items():
        signal = output["signal"]
        decision = output["decision"]
        assets[asset] = {
            "asset": signal["asset"],
            "overall_signal": signal["overall_signal"],
            "total_score": signal["total_score"],
            "action": decision["action"],
            "market_bias": decision["market_bias"],
            "conviction": decision["conviction"],
            "position_size_bucket": decision["position_size_bucket"],
            "why": decision["why"],
            "invalidations": decision["invalidations"],
        }

    return {
        "updated_at": _utc_now_iso(),
        "assets": assets,
    }


def build_asset_news_cache(
    *,
    asset: str,
    currency_id: str | None,
    news_rows: list[dict[str, Any]],
    lookback_days: int = 7,
    major_limit: int = 10,
    recent_limit: int = 30,
) -> dict[str, Any]:
    annotated_all, annotated_recent, annotated_major = _annotated_news_sets(
        asset,
        news_rows,
        major_limit=major_limit,
        recent_limit=recent_limit,
    )

    return {
        "updated_at": _utc_now_iso(),
        "asset": asset,
        "currency_id": currency_id,
        "lookback_days": lookback_days,
        "time_bucket": "4h",
        "major_items": annotated_major,
        "recent_items": annotated_recent,
        "markers_4h": _group_news_markers(annotated_recent),
        "summary": {
            "total_items": len(annotated_all),
            "major_count": len(annotated_major),
            "recent_count": len(annotated_recent),
            "has_news": bool(annotated_all),
        },
    }


def build_market_news_cache(
    *,
    scope: str,
    news_rows: list[dict[str, Any]],
    lookback_hours: int = 24,
    major_limit: int = 10,
    recent_limit: int = 30,
) -> dict[str, Any]:
    annotated_all, annotated_recent, annotated_major = _annotated_news_sets(
        scope,
        news_rows,
        major_limit=major_limit,
        recent_limit=recent_limit,
    )

    return {
        "updated_at": _utc_now_iso(),
        "scope": scope,
        "lookback_hours": lookback_hours,
        "time_bucket": "4h",
        "major_items": annotated_major,
        "recent_items": annotated_recent,
        "markers_4h": _group_news_markers(annotated_recent),
        "summary": {
            "total_items": len(annotated_all),
            "major_count": len(annotated_major),
            "recent_count": len(annotated_recent),
            "has_news": bool(annotated_all),
        },
    }


def build_news_event_rows(
    *,
    asset: str,
    currency_id: str | None,
    news_rows: list[dict[str, Any]],
    major_limit: int = 10,
    recent_limit: int = 30,
) -> list[dict[str, Any]]:
    annotated_all, _, _ = _annotated_news_sets(
        asset,
        news_rows,
        major_limit=major_limit,
        recent_limit=recent_limit,
    )
    return [
        {
            "asset": asset.lower(),
            "currency_id": currency_id,
            "news_id": item["id"],
            "release_time_ms": item["timestamp_ms"],
            "release_time_utc": item["timestamp_iso"],
            "bucket_open_ms_4h": item["bucket_open_ms_4h"],
            "bucket_open_utc_4h": item["bucket_open_iso_4h"],
            "title": item["title"],
            "source_link": item["source_link"],
            "original_link": item["original_link"],
            "category": item["category"],
            "category_label": item["category_label"],
            "author": item["author"],
            "nick_name": item["nick_name"],
            "tags": item["tags"],
            "matched_currencies": item["matched_currencies"],
            "feature_image": item["feature_image"],
            "impression_count": item["impression_count"],
            "like_count": item["like_count"],
            "reply_count": item["reply_count"],
            "retweet_count": item["retweet_count"],
            "importance_score": item["importance_score"],
            "is_major": item["is_major"],
            "raw_payload": item,
            "updated_at": _utc_now_iso(),
        }
        for item in annotated_all
        if item["timestamp_iso"] and item["bucket_open_iso_4h"]
    ]
