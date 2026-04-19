from __future__ import annotations

import json

import _bootstrap
from narralytica.clients import BinanceMarketClient, SoDEXMarketClient, SoSoValueClient
from narralytica.config import load_dotenv
from narralytica.decision_engine import decide_from_signal
from narralytica.result_writer import write_result_files
from narralytica.signal_engine import ASSET_CONFIG, build_asset_signal_snapshot


def main() -> None:
    env = load_dotenv()
    soso = SoSoValueClient(env.get("SOSO_API_KEY", ""))
    binance = BinanceMarketClient()
    sodex = SoDEXMarketClient()
    sector_payload = soso.get_sector_spotlight()
    fear_greed_rows = soso.get_analysis_chart("fgi_indicator", limit=5)
    futures_open_interest_rows = soso.get_analysis_chart("futures_open_interest", limit=5)

    signal = build_asset_signal_snapshot(
        "BTC",
        etf_rows=soso.get_etf_historical_inflow("us-btc-spot"),
        positioning_rows=binance.get_global_long_short_ratio(symbol="BTCUSDT", period="1d", limit=5),
        klines=sodex.get_perps_klines(symbol="BTC-USD", interval="1d", limit=5),
        funding_rows=binance.get_funding_rates(symbol="BTCUSDT", limit=5),
        fear_greed_rows=fear_greed_rows,
        futures_open_interest_rows=futures_open_interest_rows,
        pair_rows=soso.get_currency_pairs(ASSET_CONFIG["BTC"]["currency_id"], page_size=5),
        sector_payload=sector_payload,
        index_snapshots={
            ticker: soso.get_index_market_snapshot(ticker)
            for ticker in ASSET_CONFIG["BTC"]["index_tickers"]
        },
    )
    output = {
        "signal": signal,
        "decision": decide_from_signal(signal),
    }
    write_result_files("btc", output)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
