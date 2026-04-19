from __future__ import annotations

import json

import _bootstrap
from narralytica.clients import BinanceMarketClient
from narralytica.signal_engine import summarize_price_confirmation


def main() -> None:
    client = BinanceMarketClient()
    klines = client.get_spot_klines(symbol="BTCUSDT", interval="1d", limit=5)
    summary = summarize_price_confirmation(klines)

    output = {
        "sample_count": len(klines),
        "latest_kline": klines[-1] if klines else None,
        "summary": {
            "label": summary.label,
            "score": summary.score,
            "details": summary.details,
        },
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
