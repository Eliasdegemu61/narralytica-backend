# Narralytica BTC Signal Probes

Small Python scripts for testing BTC and ETH signal inputs with low request volume:

- SoSoValue ETF trend
- Binance long/short positioning
- SoDEX perps price/klines
- Binance funding rates
- SoSoValue futures open interest
- SoSoValue pair-depth asymmetry
- SoSoValue sector/index breadth regime
- SoSoValue fear & greed overlay
- Dedicated BTC and ETH signal runners
- Auto-written results for backend and website display

## Setup

The scripts expect a `.env` file in the project root with:

```env
SOSO_API_KEY=your_key_here
```

No third-party packages are required. The code uses only the Python standard library.

## Scripts

- `python scripts/btc_signal.py`
- `python scripts/eth_signal.py`
- `python scripts/daily_signals.py`

Each run also refreshes:

- `results/btc/signal_output.json`
- `results/btc/signal_story.json`
- `results/eth/signal_output.json`
- `results/eth/signal_story.json`

The daily runner also saves a timestamped bundle in `signal_snapshots/YYYY-MM-DD_HH-MM-SS/` so each day's calls can be assessed on following days without losing the original reference point.

Engine design notes live in:

- `DECISION_ENGINE.md`
- `ADDITIONAL_METRICS_FOR_ENGINE.md`

## Data sources

- SoSoValue ETF historical inflow:
  `https://api.sosovalue.xyz/openapi/v2/etf/historicalInflowChart`
- SoSoValue ETF current metrics:
  `https://api.sosovalue.xyz/openapi/v2/etf/currentEtfDataMetrics`
- Binance global long/short ratio:
  `https://fapi.binance.com/futures/data/globalLongShortAccountRatio`
- SoDEX perps klines:
  `https://mainnet-gw.sodex.dev/api/v1/perps/markets/{symbol}/klines`
- Binance funding rates:
  `https://fapi.binance.com/fapi/v1/fundingRate`

## Notes

- The live SoSoValue ETF historical response currently returns `data` as a list directly.
- The live SoSoValue ETF current metrics response returns `data` as an object with totals plus `list`.
- ETF is wired for BTC and ETH only.
- Price confirmation now uses SoDEX perps daily klines with lowercase interval `1d`.
- Funding uses a configurable extreme threshold in code, currently `0.0001` (`0.01%`).
- `signal_output.json` is the machine-friendly payload; `signal_story.json` is the website-friendly explanation layer.
- Keep request frequency low while iterating. These scripts intentionally do only a handful of calls.
