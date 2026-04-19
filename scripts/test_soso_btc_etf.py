from __future__ import annotations

import json

import _bootstrap
from narralytica.clients import SoSoValueClient
from narralytica.config import load_dotenv
from narralytica.signal_engine import summarize_etf_trend


def main() -> None:
    env = load_dotenv()
    client = SoSoValueClient(env.get("SOSO_API_KEY", ""))
    historical = client.get_etf_historical_inflow("us-btc-spot")
    current = client.get_current_etf_metrics("us-btc-spot")
    summary = summarize_etf_trend(historical)

    output = {
        "historical_sample_count": len(historical),
        "historical_latest": historical[0] if historical else None,
        "current_totals": {
            "dailyNetInflow": current.get("dailyNetInflow"),
            "totalNetAssets": current.get("totalNetAssets"),
            "totalTokenHoldings": current.get("totalTokenHoldings"),
        },
        "summary": {
            "label": summary.label,
            "score": summary.score,
            "details": summary.details,
        },
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
