# Narralytica Backend

Python signal jobs for generating Narralytica asset signals and publishing the latest state to Supabase.

The backend is responsible for:

- building multi-factor asset signals
- generating decision outputs and explanation payloads
- publishing latest signal state to Supabase
- refreshing website cache payloads
- generating quick-trade snapshots

## How The Decision Engine Works

The engine is a multi-factor scoring system, not a single-indicator signal.

Each asset is evaluated through up to 8 signal families:

1. ETF trend
2. Positioning
3. Price confirmation
4. Funding rates
5. Futures open interest
6. Depth asymmetry
7. Breadth regime
8. Fear and greed

The engine does not require every asset to have all 8 inputs at all times.

How coverage works:
- major assets can use the full stack when data is available
- every supported token is still evaluated on at least 4 meaningful inputs
- assets with missing institutional or derivatives coverage fall back to the metrics that are available for them

What this means in practice:
- the system is not bluffing with one headline metric
- signals are formed from multiple independent checks
- the engine can still produce a decision when some data families are unavailable, but with less overall context than a fully covered major asset

The final output is converted into:
- an overall signal state
- a directional action
- a conviction level
- a position-size bucket
- invalidation guidance

The exact weighting and threshold logic are intentionally kept private, but the decision process is based on real multi-source market inputs rather than a single price rule.

## Signal Inputs

- SoSoValue ETF trend
- Binance long/short positioning
- SoDEX perps price and kline context
- Binance funding rates
- SoSoValue futures open interest
- SoSoValue pair-depth asymmetry
- SoSoValue sector and index breadth regime
- SoSoValue fear and greed overlay

Primary endpoint sources behind those inputs:

- SoSoValue ETF trend:
  `https://api.sosovalue.xyz/openapi/v2/etf/historicalInflowChart`
- SoSoValue ETF current metrics:
  `https://api.sosovalue.xyz/openapi/v2/etf/currentEtfDataMetrics`
- Binance global long/short positioning:
  `https://fapi.binance.com/futures/data/globalLongShortAccountRatio`
- SoDEX perps kline context:
  `https://mainnet-gw.sodex.dev/api/v1/perps/markets/{symbol}/klines`
- Binance funding rates:
  `https://fapi.binance.com/fapi/v1/fundingRate`
- SoSoValue futures open interest:
  chart-based futures open interest feed from the SoSoValue analysis API
- SoSoValue pair-depth asymmetry:
  SoSoValue currency pairs and market depth data
- SoSoValue sector and index breadth regime:
  SoSoValue sector spotlight plus index market snapshot data
- SoSoValue fear and greed overlay:
  chart-based fear and greed feed from the SoSoValue analysis API

## Setup

### Quick Start For Reviewers

1. Create a local `.env` file in the project root.
2. Add the required keys shown below.
3. Run the main signal bot:

```bash
python scripts/daily_signals.py
```

4. Run the quick-trade bot if needed:

```bash
python scripts/quick_trade_snapshots.py
```

5. If Supabase credentials are configured, the outputs will be published to the database automatically.

### What You Need

- Python 3.11+
- a valid `SOSO_API_KEY`
- optional Supabase project credentials if you want live publishing

### Environment Variables

The scripts expect a `.env` file in the project root with:

```env
SOSO_API_KEY=your_sosovalue_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
```

What each variable is for:

- `SOSO_API_KEY`
  Required. Used by the backend to fetch SoSoValue ETF, breadth, fear and greed, and related market data.
- `SUPABASE_URL`
  Optional, but required for live publishing. This is your Supabase project URL.
- `SUPABASE_SERVICE_ROLE_KEY`
  Optional, but required for live publishing. This is the backend write key used to publish signals and cache payloads into Supabase.

If `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are present, the backend publishes live outputs automatically.

No third-party packages are required. The code uses only the Python standard library.

### What Happens When You Run It

- `python scripts/daily_signals.py`
  This is the main signal bot. It builds the latest multi-factor asset decisions across the supported asset set.
- `python scripts/quick_trade_snapshots.py`
  This is the quick-trade bot. It builds the BTC and ETH tactical quick-trade payloads.
- if Supabase is configured, the backend publishes into:
  - `latest_asset_state`
  - `decision_runs`
  - `site_cache`
  - `news_events`

### Minimal Review Flow

For a judge or reviewer, the simplest path is:

1. Configure `.env`
2. Run `python scripts/daily_signals.py` to generate the main signal outputs
3. Run `python scripts/quick_trade_snapshots.py` to generate the Quick Trade cache payloads
4. Confirm fresh rows appear in Supabase
5. Open the website frontend and verify the latest signals render correctly

## Scripts

- `python scripts/btc_signal.py`
- `python scripts/eth_signal.py`
- `python scripts/daily_signals.py`
- `python scripts/quick_trade_snapshots.py`

If Supabase env vars are configured, the daily runner also publishes:

- historical rows into `decision_runs`
- one latest row per asset into `latest_asset_state`
- historical news rows into `news_events`
- shared cache payloads into `site_cache`

Create those tables in Supabase with:

- [supabase/schema.sql](/c:/Users/elias/Desktop/narralytica_v2/supabase/schema.sql)

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
- `site_cache` now includes per-asset news cache keys like `news_chart_btc`.
- `news_events` stores individual historical news items for website timelines and chart overlays.
- Keep request frequency low while iterating. These scripts intentionally do only a handful of calls.
