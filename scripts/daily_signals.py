from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError

import _bootstrap
from narralytica.clients import SoSoValueClient
from narralytica.config import load_dotenv
from narralytica.decision_engine import decide_from_signal
from narralytica.result_writer import build_enriched_output, build_signal_story
from narralytica.site_payloads import build_engine_summary_cache, build_market_overview_cache
from narralytica.signal_engine import ASSET_CONFIG, build_asset_signal_snapshot
from narralytica.supabase import SupabasePublisher, describe_http_error


def _safe_analysis_chart_rows(
    soso: SoSoValueClient,
    *,
    chart_name: str | None,
    limit: int = 5,
) -> list[dict[str, object]] | None:
    if not chart_name:
        return None
    try:
        rows = soso.get_analysis_chart(chart_name, limit=limit)
        if rows:
            return rows
    except Exception as exc:
        print(f"[warn] SoSoValue chart unavailable for {chart_name}: {exc}")
    return None


def _safe_currency_klines(soso: SoSoValueClient, *, asset: str, currency_id: str) -> list[dict[str, object]] | None:
    try:
        rows = soso.get_currency_klines(currency_id, interval="1d", limit=5)
        if rows and len(rows) >= 5:
            ordered = sorted(rows, key=lambda row: int(row["timestamp"]))
            normalized = [
                {
                    "t": row["timestamp"],
                    "o": row["open"],
                    "c": row["close"],
                    "source": "soso_currency_klines_1d",
                }
                for row in ordered
            ]
            try:
                snapshot = soso.get_currency_market_snapshot(currency_id)
                latest_price = snapshot.get("price")
                if latest_price is not None:
                    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
                    normalized[-1] = {
                        **normalized[-1],
                        "t": now_ms,
                        "c": latest_price,
                        "source": "soso_market_snapshot_with_1d_context",
                    }
            except Exception as exc:
                print(f"[warn] SoSoValue market snapshot unavailable for {asset}: {exc}")

            return normalized
    except Exception as exc:
        print(f"[warn] SoSoValue price unavailable for {asset}: {exc}")
    return None


def _safe_pair_rows(soso: SoSoValueClient, *, asset: str, currency_id: str) -> list[dict[str, object]] | None:
    try:
        rows = soso.get_currency_pairs(currency_id, page_size=5)
        return rows or None
    except Exception as exc:
        print(f"[warn] SoSoValue pair depth unavailable for {asset}: {exc}")
        return None


def _safe_index_snapshots(soso: SoSoValueClient, *, asset: str, index_tickers: tuple[str, ...]) -> dict[str, dict[str, object]]:
    snapshots: dict[str, dict[str, object]] = {}
    for ticker in index_tickers:
        try:
            snapshots[ticker] = soso.get_index_market_snapshot(ticker)
        except Exception as exc:
            print(f"[warn] SoSoValue index snapshot unavailable for {asset} / {ticker}: {exc}")
    return snapshots


def _build_positioning_rows(chart_rows: list[dict[str, object]] | None) -> list[dict[str, object]] | None:
    if not chart_rows:
        return None
    ordered = sorted(chart_rows, key=lambda row: int(row["timestamp"]))
    normalized_rows: list[dict[str, object]] = []
    for row in ordered:
        ratio = float(row.get("long/short_ratio", 1.0) or 1.0)
        denominator = ratio + 1.0
        normalized_rows.append(
            {
                "longShortRatio": ratio,
                "longAccount": ratio / denominator,
                "shortAccount": 1.0 / denominator,
                "timestamp": row["timestamp"],
            }
        )
    return normalized_rows


def _build_funding_rows(chart_rows: list[dict[str, object]] | None) -> list[dict[str, object]] | None:
    if not chart_rows:
        return None
    ordered = sorted(chart_rows, key=lambda row: int(row["timestamp"]))
    return [
        {
            "fundingRate": row.get("binance", 0),
            "fundingTime": row["timestamp"],
            "markPrice": row.get("btc_price", 0),
        }
        for row in ordered
    ]


def _build_output(
    asset: str,
    *,
    config: dict[str, object],
    soso: SoSoValueClient,
    sector_payload: dict[str, object],
    fear_greed_rows: list[dict[str, object]] | None,
    futures_open_interest_rows: list[dict[str, object]] | None,
) -> dict[str, object]:
    raw_currency_id = config.get("currency_id")
    currency_id = str(raw_currency_id) if raw_currency_id else None
    index_snapshots = _safe_index_snapshots(
        soso,
        asset=asset,
        index_tickers=tuple(config.get("index_tickers", ())),
    )
    positioning_rows = _build_positioning_rows(
        _safe_analysis_chart_rows(soso, chart_name=config.get("positioning_chart"), limit=5)
    )
    funding_rows = _build_funding_rows(
        _safe_analysis_chart_rows(soso, chart_name=config.get("funding_chart"), limit=5)
    )
    signal = build_asset_signal_snapshot(
        asset,
        etf_rows=soso.get_etf_historical_inflow(str(config["etf_type"])) if config.get("etf_type") else None,
        positioning_rows=positioning_rows,
        klines=_safe_currency_klines(soso, asset=asset, currency_id=currency_id) if currency_id else None,
        funding_rows=funding_rows,
        fear_greed_rows=fear_greed_rows,
        futures_open_interest_rows=futures_open_interest_rows if config.get("has_futures_open_interest") else None,
        pair_rows=_safe_pair_rows(soso, asset=asset, currency_id=currency_id) if currency_id else None,
        sector_payload=sector_payload,
        index_snapshots=index_snapshots,
    )
    return {
        "signal": signal,
        "decision": decide_from_signal(signal),
    }


def main() -> None:
    env = load_dotenv()
    soso = SoSoValueClient(env.get("SOSO_API_KEY", ""))
    sector_payload = soso.get_sector_spotlight()
    fear_greed_rows = _safe_analysis_chart_rows(soso, chart_name="fgi_indicator", limit=5)
    futures_open_interest_rows = _safe_analysis_chart_rows(soso, chart_name="futures_open_interest", limit=5)
    etf_metrics = {
        asset.lower(): soso.get_current_etf_metrics(str(config["etf_type"]))
        for asset, config in ASSET_CONFIG.items()
        if config.get("etf_type")
    }

    outputs = {
        asset.lower(): _build_output(
            asset,
            config=config,
            soso=soso,
            sector_payload=sector_payload,
            fear_greed_rows=fear_greed_rows,
            futures_open_interest_rows=futures_open_interest_rows,
        )
        for asset, config in ASSET_CONFIG.items()
    }

    stories = {
        asset: build_signal_story(output["signal"], output["decision"])
        for asset, output in outputs.items()
    }
    enriched_outputs = {
        asset: build_enriched_output(output)
        for asset, output in outputs.items()
    }
    site_cache = {
        "engine_summary": build_engine_summary_cache(outputs),
        "market_overview": build_market_overview_cache(
            fear_greed_rows=fear_greed_rows,
            futures_open_interest_rows=futures_open_interest_rows,
            sector_payload=sector_payload,
            etf_metrics=etf_metrics,
        ),
    }

    published_to_supabase = False
    supabase_errors: list[dict[str, str]] = []
    supabase_url = env.get("SUPABASE_URL", "")
    supabase_service_role_key = env.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if supabase_url and supabase_service_role_key:
        publisher = SupabasePublisher(supabase_url, supabase_service_role_key)
        for asset, enriched_output in enriched_outputs.items():
            try:
                publisher.insert_decision_run(
                    asset=asset,
                    output=enriched_output,
                    story=stories[asset],
                )
            except HTTPError as exc:
                message = describe_http_error(exc)
                print(f"[warn] Supabase decision_runs insert failed for {asset}: {message}")
                supabase_errors.append({"asset": asset, "step": "decision_runs", "error": message})
            except Exception as exc:
                message = str(exc)
                print(f"[warn] Supabase decision_runs insert failed for {asset}: {message}")
                supabase_errors.append({"asset": asset, "step": "decision_runs", "error": message})

            try:
                publisher.upsert_latest_asset_state(
                    asset=asset,
                    output=enriched_output,
                    story=stories[asset],
                )
            except HTTPError as exc:
                message = describe_http_error(exc)
                print(f"[warn] Supabase latest_asset_state upsert failed for {asset}: {message}")
                supabase_errors.append({"asset": asset, "step": "latest_asset_state", "error": message})
            except Exception as exc:
                message = str(exc)
                print(f"[warn] Supabase latest_asset_state upsert failed for {asset}: {message}")
                supabase_errors.append({"asset": asset, "step": "latest_asset_state", "error": message})

        try:
            publisher.upsert_site_cache(
                cache_key="engine_summary",
                payload=site_cache["engine_summary"],
                source="decision_engine",
                refresh_interval_minutes=15,
            )
        except HTTPError as exc:
            message = describe_http_error(exc)
            print(f"[warn] Supabase site_cache upsert failed for engine_summary: {message}")
            supabase_errors.append({"asset": "all", "step": "engine_summary", "error": message})
        except Exception as exc:
            message = str(exc)
            print(f"[warn] Supabase site_cache upsert failed for engine_summary: {message}")
            supabase_errors.append({"asset": "all", "step": "engine_summary", "error": message})

        try:
            publisher.upsert_site_cache(
                cache_key="market_overview",
                payload=site_cache["market_overview"],
                source="decision_engine",
                refresh_interval_minutes=15,
            )
        except HTTPError as exc:
            message = describe_http_error(exc)
            print(f"[warn] Supabase site_cache upsert failed for market_overview: {message}")
            supabase_errors.append({"asset": "all", "step": "market_overview", "error": message})
        except Exception as exc:
            message = str(exc)
            print(f"[warn] Supabase site_cache upsert failed for market_overview: {message}")
            supabase_errors.append({"asset": "all", "step": "market_overview", "error": message})

        published_to_supabase = True

    print(
        json.dumps(
            {
                "outputs": outputs,
                "site_cache": site_cache,
                "supabase_errors": supabase_errors,
                "published_to_supabase": published_to_supabase,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
