from __future__ import annotations

import json
from urllib.error import HTTPError

import _bootstrap
from narralytica.clients import CoinDeskRSSClient
from narralytica.config import load_dotenv
from narralytica.site_payloads import build_market_news_cache, build_news_event_rows
from narralytica.supabase import SupabasePublisher, describe_http_error


MARKET_SCOPE = "CRYPTO_MARKET"
MARKET_ASSET_KEY = "market"
MARKET_CACHE_KEY = "news_chart_crypto"


def main() -> None:
    env = load_dotenv()
    client = CoinDeskRSSClient(
        feed_url=env.get("COINDESK_RSS_URL", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    )
    publisher = SupabasePublisher(
        env.get("SUPABASE_URL", ""),
        env.get("SUPABASE_SERVICE_ROLE_KEY", ""),
    )

    lookback_hours = int(env.get("COINDESK_LOOKBACK_HOURS", "24") or "24")
    request_limit = int(env.get("COINDESK_NEWS_LIMIT", "20") or "20")
    refresh_interval_minutes = int(env.get("COINDESK_REFRESH_MINUTES", "60") or "60")

    errors: list[dict[str, str]] = []
    try:
        news_rows = client.get_news(
            lookback_hours=lookback_hours,
            limit=request_limit,
        )
    except HTTPError as exc:
        message = describe_http_error(exc)
        print(f"[warn] CoinDesk RSS fetch failed: {message}")
        news_rows = []
        errors.append({"scope": MARKET_ASSET_KEY, "step": "fetch", "error": message})
    except Exception as exc:
        message = str(exc)
        print(f"[warn] CoinDesk RSS fetch failed: {message}")
        news_rows = []
        errors.append({"scope": MARKET_ASSET_KEY, "step": "fetch", "error": message})

    event_rows = build_news_event_rows(
        asset=MARKET_SCOPE,
        currency_id=None,
        news_rows=news_rows,
    )
    cache_payload = build_market_news_cache(
        scope=MARKET_SCOPE,
        news_rows=news_rows,
        lookback_hours=lookback_hours,
    )

    try:
        publisher.upsert_news_events(rows=event_rows)
    except HTTPError as exc:
        message = describe_http_error(exc)
        print(f"[warn] Supabase news_events upsert failed: {message}")
        errors.append({"scope": MARKET_ASSET_KEY, "step": "news_events", "error": message})
    except Exception as exc:
        message = str(exc)
        print(f"[warn] Supabase news_events upsert failed: {message}")
        errors.append({"scope": MARKET_ASSET_KEY, "step": "news_events", "error": message})

    try:
        publisher.upsert_site_cache(
            cache_key=MARKET_CACHE_KEY,
            payload=cache_payload,
            source="coindesk_rss_backfill",
            refresh_interval_minutes=refresh_interval_minutes,
        )
    except HTTPError as exc:
        message = describe_http_error(exc)
        print(f"[warn] Supabase site_cache upsert failed: {message}")
        errors.append({"scope": MARKET_ASSET_KEY, "step": "site_cache", "error": message})
    except Exception as exc:
        message = str(exc)
        print(f"[warn] Supabase site_cache upsert failed: {message}")
        errors.append({"scope": MARKET_ASSET_KEY, "step": "site_cache", "error": message})

    print(
        json.dumps(
            {
                "backfilled": True,
                "scope": MARKET_SCOPE,
                "cache_key": MARKET_CACHE_KEY,
                "lookback_hours": lookback_hours,
                "request_limit": request_limit,
                "event_row_count": len(event_rows),
                "summary": cache_payload.get("summary", {}),
                "errors": errors,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
