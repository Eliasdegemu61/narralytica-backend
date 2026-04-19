from __future__ import annotations

import json

import _bootstrap
from narralytica.clients import BinanceMarketClient, SoDEXMarketClient, SoSoValueClient
from narralytica.config import load_dotenv
from narralytica.decision_engine import decide_from_signal
from narralytica.result_writer import write_result_files, write_signal_snapshot_bundle
from narralytica.signal_engine import ASSET_CONFIG, build_asset_signal_snapshot


def _build_output(
    asset: str,
    *,
    etf_type: str,
    binance_symbol: str,
    sodex_symbol: str,
    currency_id: str,
    index_tickers: tuple[str, ...],
    soso: SoSoValueClient,
    binance: BinanceMarketClient,
    sodex: SoDEXMarketClient,
    sector_payload: dict[str, object],
    fear_greed_rows: list[dict[str, object]],
    futures_open_interest_rows: list[dict[str, object]],
) -> dict[str, object]:
    index_snapshots = {
        ticker: soso.get_index_market_snapshot(ticker)
        for ticker in index_tickers
    }
    signal = build_asset_signal_snapshot(
        asset,
        etf_rows=soso.get_etf_historical_inflow(etf_type),
        positioning_rows=binance.get_global_long_short_ratio(symbol=binance_symbol, period="1d", limit=5),
        klines=sodex.get_perps_klines(symbol=sodex_symbol, interval="1d", limit=5),
        funding_rows=binance.get_funding_rates(symbol=binance_symbol, limit=5),
        fear_greed_rows=fear_greed_rows,
        futures_open_interest_rows=futures_open_interest_rows,
        pair_rows=soso.get_currency_pairs(currency_id, page_size=5),
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
    binance = BinanceMarketClient()
    sodex = SoDEXMarketClient()
    sector_payload = soso.get_sector_spotlight()
    fear_greed_rows = soso.get_analysis_chart("fgi_indicator", limit=5)
    futures_open_interest_rows = soso.get_analysis_chart("futures_open_interest", limit=5)

    outputs = {
        "btc": _build_output(
            "BTC",
            etf_type="us-btc-spot",
            binance_symbol="BTCUSDT",
            sodex_symbol="BTC-USD",
            currency_id=ASSET_CONFIG["BTC"]["currency_id"],
            index_tickers=ASSET_CONFIG["BTC"]["index_tickers"],
            soso=soso,
            binance=binance,
            sodex=sodex,
            sector_payload=sector_payload,
            fear_greed_rows=fear_greed_rows,
            futures_open_interest_rows=futures_open_interest_rows,
        ),
        "eth": _build_output(
            "ETH",
            etf_type="us-eth-spot",
            binance_symbol="ETHUSDT",
            sodex_symbol="ETH-USD",
            currency_id=ASSET_CONFIG["ETH"]["currency_id"],
            index_tickers=ASSET_CONFIG["ETH"]["index_tickers"],
            soso=soso,
            binance=binance,
            sodex=sodex,
            sector_payload=sector_payload,
            fear_greed_rows=fear_greed_rows,
            futures_open_interest_rows=futures_open_interest_rows,
        ),
    }

    result_files = {
        asset: write_result_files(asset, output)
        for asset, output in outputs.items()
    }
    snapshot = write_signal_snapshot_bundle(assets=("btc", "eth"))

    print(
        json.dumps(
            {
                "outputs": outputs,
                "result_files": result_files,
                "snapshot": snapshot,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
