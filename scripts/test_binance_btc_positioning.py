from __future__ import annotations

import json

import _bootstrap
from narralytica.clients import BinanceMarketClient
from narralytica.signal_engine import summarize_positioning


def main() -> None:
    client = BinanceMarketClient()
    rows = client.get_global_long_short_ratio(symbol="BTCUSDT", period="1d", limit=5)
    summary = summarize_positioning(rows)

    output = {
        "sample_count": len(rows),
        "rows": rows,
        "summary": {
            "label": summary.label,
            "score": summary.score,
            "details": summary.details,
        },
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
