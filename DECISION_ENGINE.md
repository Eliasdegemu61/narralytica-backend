# Decision Engine

This document explains how the Narralytica decision engine works after the move from a 4-metric model to an 8-metric model.

The engine is designed to answer one practical question:

- should we be long, short, or waiting right now?

It does that by combining slow institutional signals, medium-speed market structure signals, and fast crowding or sentiment signals into one interpretable score.

## Engine Overview

The engine now uses 8 components:

1. ETF trend
2. positioning
3. price confirmation
4. funding rates
5. futures open interest
6. depth asymmetry
7. breadth regime
8. fear & greed

These are not equal in meaning.

- ETF trend is a stronger institutional signal.
- Price, open interest, and depth are stronger structural signals.
- Breadth is a confirmation layer.
- Fear & greed is a light overlay.

## Scoring Philosophy

Each component produces:

- a `label`: `bullish`, `bearish`, `neutral`, or `unavailable`
- a `raw_score`
- an `effective_score`

The final `total_score` is built from effective scores.

Why have both raw and effective scores?

- raw score tells us what the metric itself said
- effective score tells us how much influence it was allowed to have in the final model

This matters because some components are deliberately weighted differently.

## Final Component Weights

Current scoring behavior in code:

- ETF trend:
  raw range `-2 .. +2`
  effective range `-3 .. +3` when ETF is strong
- positioning:
  raw and effective range `-2 .. +2`
- price confirmation:
  raw and effective range `-2 .. +2`
- funding rates:
  raw and effective range `-2 .. +2`
- futures open interest:
  raw and effective range `-2 .. +2`
- depth asymmetry:
  raw and effective range `-2 .. +2`
- breadth regime:
  raw and effective range `-1 .. +1`
- fear & greed:
  raw and effective range `-1 .. +1`

Maximum bullish total is `+15`.
Maximum bearish total is `-15`.

## ETF / Price Contradiction Rule

ETF is intentionally stronger than funding or breadth, but ETF should not dominate when price is strongly contradicting it.

The engine applies this rule before total score is calculated:

- if ETF effective score is strongly bullish and price score is `-2`, ETF is clipped back to `+2`
- if ETF effective score is strongly bearish and price score is `+2`, ETF is clipped back to `-2`

Why:

- ETF is slower
- price is faster
- if fast price action sharply disagrees, ETF should still matter, but not dominate

## Decision Bands

The engine maps total score to a base bias:

- `+8 to +15`: long, high conviction
- `+4 to +7`: long, medium conviction
- `-3 to +3`: neutral, low conviction
- `-4 to -7`: short, medium conviction
- `-8 to -15`: short, high conviction

Then the decision layer checks structural gates before choosing:

- `spot_long`
- `perps_long`
- `perps_short`
- `wait`

## The 8 Metrics

### 1. ETF Trend

#### Why it exists

ETF flow is our institutional demand proxy.

This is one of the strongest components because it measures real spot allocation interest rather than just trader positioning.

#### API

- current implementation uses SoSoValue ETF v2 endpoints:
  - `POST /openapi/v2/etf/historicalInflowChart`

#### Example response shape

```json
[
  {
    "date": "2026-04-17",
    "totalNetInflow": 663911366.465
  }
]
```

#### What we use

- latest day net inflow
- 5-day net inflow sum
- number of positive days in the recent sample

#### Raw scoring

- `+1` if latest flow is positive
- `-1` if latest flow is negative
- `+1` if 5-day flow is positive
- `-1` if 5-day flow is negative

That gives ETF a raw score from `-2` to `+2`.

#### Effective weighting

- strong ETF raw `+2` becomes effective `+3`
- strong ETF raw `-2` becomes effective `-3`

unless the price contradiction rule clips it.

### 2. Positioning

#### Why it exists

Positioning tells us whether account-level crowd direction is leaning long or short.

#### API

- Binance futures:
  - `GET /futures/data/globalLongShortAccountRatio`

#### Example response shape

```json
[
  {
    "longShortRatio": "0.795",
    "longAccount": "0.4429",
    "shortAccount": "0.5571",
    "timestamp": 1776556800000
  }
]
```

#### What we use

- latest long/short ratio
- latest long and short account shares
- comparison against recent average ratio

#### Scoring

- `+1` if latest ratio is above `1.0`
- `-1` if latest ratio is below `0.95`
- `+1` if latest ratio is above recent average
- `-1` if latest ratio is below recent average

Range: `-2 .. +2`

### 3. Price Confirmation

#### Why it exists

Price is the fast structural check.

Even if flows look good, price still has to confirm.

#### API

- SoDEX perps klines:
  - `GET /api/v1/perps/markets/{symbol}/klines`

#### Example response shape

```json
[
  {
    "t": 1776556800000,
    "o": "75653.0",
    "c": "75537.0"
  }
]
```

#### What we use

- latest close
- latest open
- 3-day simple moving average
- 5-day simple moving average
- daily return
- sample return

#### Scoring

- `+1` if latest close is above `sma_3`
- `-1` if latest close is below `sma_3`
- `+1` if `sma_3 > sma_5`
- `-1` if `sma_3 < sma_5`

Range: `-2 .. +2`

### 4. Funding Rates

#### Why it exists

Funding is a crowding signal, not a pure directional signal.

It helps us avoid entering longs when leverage is already too crowded, and avoid entering shorts when shorting is already too crowded.

#### API

- Binance futures:
  - `GET /fapi/v1/fundingRate`

#### Example response shape

```json
[
  {
    "fundingRate": "-0.00012276",
    "fundingTime": 1776556800000,
    "markPrice": "75807.7"
  }
]
```

#### What we use

- latest funding rate
- recent average funding
- extreme threshold, currently `0.0001`

#### Scoring

- `+1` if latest funding is meaningfully negative
- `-1` if latest funding is meaningfully positive
- `+1` if latest funding is below recent average
- `-1` if latest funding is above recent average

Range: `-2 .. +2`

### 5. Futures Open Interest

#### Why it exists

Open interest tells us whether leverage is being added or removed.

This is important because rising leverage can confirm a move or warn that a weak move is being crowded into.

#### API

- SoSoValue analysis chart:
  - `GET /openapi/v1/analyses/futures_open_interest`

#### Example response shape

```json
[
  {
    "timestamp": "1776470400000",
    "all": 61692410495,
    "binance": 10776372519,
    "cme": 9748849037,
    "btc_price": 75691.76
  }
]
```

#### What we use

- total open interest
- previous total open interest
- BTC reference price change alongside OI
- venue split, especially Binance and CME

#### Scoring

- `+2` when OI is rising and price is holding or improving
- `+1` when OI is improving with only mild price support
- `0` when the signal is mixed
- `-1` when OI is rising into a weak move
- `-2` when OI is expanding aggressively while price weakens

Range: `-2 .. +2`

### 6. Depth Asymmetry

#### Why it exists

This is our spot microstructure signal.

It measures how much capital it takes to push price up or down by 2%.

That gives us a read on whether downside is well supported or fragile.

#### API

- SoSoValue pairs endpoint:
  - `GET /openapi/v1/currencies/{currency_id}/pairs`

BTC currency id:

- `1673723677362319866`

ETH currency id:

- `1673723677362319867`

#### Example response shape

```json
{
  "list": [
    {
      "market": "Binance",
      "price": 75425.0,
      "turnover_24h": 706663048.0,
      "cost_to_move_up_usd": 12533988,
      "cost_to_move_down_usd": 19151674
    }
  ]
}
```

#### What we use

- top 3 to 5 venues by turnover
- turnover-weighted cost to move price up
- turnover-weighted cost to move price down
- `depth_ratio = weighted_down / weighted_up`

#### Scoring

- `>= 1.20`: `+2`
- `1.05 to 1.19`: `+1`
- `0.95 to 1.04`: `0`
- `0.80 to 0.94`: `-1`
- `< 0.80`: `-2`

Range: `-2 .. +2`

### 7. Breadth Regime

#### Why it exists

Breadth tells us whether a move is broad or narrow.

Broad moves are healthier than isolated ones.

#### APIs

- sector view:
  - `GET /openapi/v1/currencies/sector-spotlight`
- index list:
  - `GET /openapi/v1/indices`
- index snapshot:
  - `GET /openapi/v1/indices/{ticker}/market-snapshot`

#### Example sector response shape

```json
{
  "sector": [
    {
      "name": "BTC",
      "change_pct_24h": -0.0064,
      "marketcap_dom": 0.5867
    }
  ]
}
```

#### Example index snapshot shape

```json
{
  "price": 13.8829,
  "change_pct_24h": -0.007,
  "roi_7d": 0.0615,
  "roi_1m": 0.0199
}
```

#### Asset mappings

For BTC we currently emphasize:

- sector: `BTC`
- indices: `ssiMAG7`, `ssiCeFi`

For ETH we currently emphasize:

- sector: `ETH`
- indices: `ssiLayer1`, `ssiDeFi`

#### Scoring

- `+1` when asset sector is supportive and at least one relevant index has positive trend
- `0` when mixed
- `-1` when sector and relevant breadth are working against the thesis

Range: `-1 .. +1`

### 8. Fear & Greed

#### Why it exists

This is a regime overlay, not a primary driver.

It helps at emotional extremes:

- deep fear can support contrarian longs if structure is improving
- deep greed can reduce confidence in fresh longs

#### API

- SoSoValue analysis chart:
  - `GET /openapi/v1/analyses/fgi_indicator`

#### Example response shape

```json
[
  {
    "timestamp": "1776528000000",
    "crypto_fear_&_greed_index": 27
  }
]
```

#### Scoring

- `+1` when fear is very elevated and stabilizing
- `0` in the middle
- `-1` when greed is extreme and still stretching

Range: `-1 .. +1`

## Why ETF Data Still Uses the Regular ETF Endpoints

The engine still uses the regular ETF endpoints as the canonical ETF source instead of the `analyses` ETF charts.

Why:

- clearer field semantics
- better granularity
- easier to score directly
- fewer hidden assumptions

The `analyses` ETF charts are still useful for context and cross-checking, but they are not the primary scoring source.

## How Actions Are Chosen

After total score is computed, the engine chooses actions with extra structural gates.

### `perps_long`

Requires:

- high enough total score
- bullish price confirmation
- depth not bearish
- open interest not bearish
- funding not bearish
- strong multi-component agreement

### `spot_long`

Requires:

- medium or high long bias
- ETF trend bullish
- price not bearish
- depth not bearish
- funding not strongly bearish

### `perps_short`

Requires:

- strongly negative total score
- bearish price confirmation
- bearish positioning
- bearish depth
- funding not already too negative
- strong bearish agreement

### `wait`

Chosen when:

- total score is neutral
- or structural components conflict too much
- or conviction is downgraded by mixed agreement

## Output Structure

Each signal snapshot returns:

- `asset`
- `overall_signal`
- `total_score`
- `components`

Each component includes:

- `name`
- `label`
- `score`
- `details.raw_score`
- `details.effective_score`

This lets us see both the raw metric state and the weighted effect used in the final engine.

## Files In The Repo

Core logic lives in:

- [signal_engine.py](C:/Users/elias/Desktop/narralytica_v2/src/narralytica/signal_engine.py)
- [decision_engine.py](C:/Users/elias/Desktop/narralytica_v2/src/narralytica/decision_engine.py)
- [clients.py](C:/Users/elias/Desktop/narralytica_v2/src/narralytica/clients.py)
- [result_writer.py](C:/Users/elias/Desktop/narralytica_v2/src/narralytica/result_writer.py)

Runners live in:

- [btc_signal.py](C:/Users/elias/Desktop/narralytica_v2/scripts/btc_signal.py)
- [eth_signal.py](C:/Users/elias/Desktop/narralytica_v2/scripts/eth_signal.py)
- [daily_signals.py](C:/Users/elias/Desktop/narralytica_v2/scripts/daily_signals.py)

## Sources

- ETF summary/history docs:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/2.-etf/summary-history
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/2.-etf/history
- Trading pairs:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/1.-currency-and-pairs/pairs
- Sector spotlight:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/1.-currency-and-pairs/sector-spotlight
- Index list and snapshots:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/3.-sosovalue-index/list
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/3.-sosovalue-index/market-snapshot
- Analysis charts:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/9.-analysis-charts/list
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/9.-analysis-charts/chart-data
