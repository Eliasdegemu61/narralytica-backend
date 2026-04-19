# Additional Metrics For Engine

This note documents the four new metrics we want to add to the decision engine after the original four-component setup:

- ETF trend
- positioning
- price confirmation
- funding rates

The four additions covered here are:

1. `fgi_indicator`
2. `futures_open_interest`
3. trading-pair depth asymmetry
4. sector/index breadth regime

The goal is not to make the engine more complicated for its own sake. The goal is to add four interpretable signals that answer four different questions:

- Is the market emotionally stretched?
- Is leverage building or cooling?
- Is spot liquidity structurally easier to push higher or lower?
- Is the move broad across crypto, or narrow and fragile?

## 1. Fear & Greed Index

### Endpoint

- SoSoValue analysis chart: `GET /analyses/fgi_indicator`

### Raw data shape

The chart exposes a single time series field:

- `crypto_fear_&_greed_index`

Recent live sample pulled on April 19, 2026:

- 27
- 26
- 21

### What it means

This is a sentiment and regime gauge, not a direct directional predictor.

- Low values mean fear, risk aversion, panic, or exhaustion.
- High values mean greed, crowding, and a market that may already be extended.

This metric is most useful as a filter on other signals:

- fear plus improving structure can support a contrarian long
- greed plus stretched leverage can reduce confidence in fresh longs

### Interpretation rules

- Very low: contrarian bullish only if flows/price/liquidity are improving
- Neutral: little edge by itself
- Very high: caution against chasing longs

### Suggested scoring use

Use this as a modest overlay rather than a dominant component.

Example scoring:

- `<= 25`: `+1` if other trend/flow signals are already bullish
- `26-60`: `0`
- `>= 75`: `-1` if leverage and price are already extended

Important: do not make extreme fear automatically bullish. Fear should only help a bullish score if other components are stabilizing or improving.

### Significance / update behavior

- Significance: medium
- Frequency of impact: occasional to moderate

This matters most at emotional extremes. In the middle of the range it usually adds little.

## 2. Futures Open Interest

### Endpoint

- SoSoValue analysis chart: `GET /analyses/futures_open_interest`

### Raw data shape

This chart exposes aggregate and venue-level open interest:

- `all`
- `binance`
- `cme`
- `okex`
- `bybit`
- `bitget`
- `deribit`
- `btc_price`

Recent live sample pulled on April 19, 2026:

- total open interest moved from about `56.64B` to `61.69B`
- BTC price at the latest point was about `75,691.76`

### What it means

Open interest measures the total size of active futures positions.

- Rising OI means leverage is being added
- Falling OI means leverage is being closed

By itself, rising OI is not bullish or bearish. The interpretation depends on price:

- price up + OI up: trend participation is building
- price down + OI up: shorts may be pressing, or late leverage may be entering
- price up + OI down: squeeze / short covering is possible
- price down + OI down: long liquidation / deleveraging is possible

### Interpretation rules

For this engine, we should keep the interpretation simple:

- bullish when price is stable/up and OI is expanding from a non-extreme base
- bearish when price is weak and OI is still expanding aggressively
- neutral when OI is flat or when leverage is unwinding without a clean directional message

Venue split also matters:

- rising CME share usually supports a more institutional interpretation
- rising offshore OI with weak price can indicate speculative crowding

### Suggested scoring use

Use OI as a leverage-confirmation component.

Example scoring:

- `+2` if 3-day or 5-day OI trend is up and price is also holding/up
- `-2` if OI is rising while price trend is clearly weakening
- `0` if OI is flat or falling without a strong directional implication

Risk guardrail:

- if OI is accelerating too quickly after a strong move, cap bullish conviction even if the label stays bullish

### Significance / update behavior

- Significance: high
- Frequency of impact: frequent

This is one of the most active and useful additions because leverage conditions can change fast and often matter for short-horizon signal quality.

## 3. Trading-Pair Depth Asymmetry

### Endpoint

- `GET /currencies/{currency_id}/pairs`

For BTC and ETH the relevant `currency_id` values from the live API are:

- BTC: `1673723677362319866`
- ETH: `1673723677362319867`

### Raw data shape

Each pair record contains:

- `base`
- `target`
- `market`
- `price`
- `turnover_24h`
- `cost_to_move_up_usd`
- `cost_to_move_down_usd`

Recent live samples pulled on April 19, 2026:

BTC on Binance:

- `turnover_24h`: `706,663,048`
- `cost_to_move_up_usd`: `12,533,988`
- `cost_to_move_down_usd`: `19,151,674`

ETH on Binance:

- `turnover_24h`: `430,310,224`
- `cost_to_move_up_usd`: `15,976,757`
- `cost_to_move_down_usd`: `33,191,636`

### What it means

This endpoint is a spot liquidity and depth proxy.

- `cost_to_move_up_usd` is the estimated capital needed to push the asset up by 2%
- `cost_to_move_down_usd` is the estimated capital needed to push the asset down by 2%

This lets us measure directional liquidity asymmetry.

If it takes much more money to push price down than up:

- downside is better supported
- the order book is more resilient underneath
- the setup leans bullish

If it takes much less money to push price down than up:

- downside is fragile
- sell pressure can move the market more easily
- the setup leans bearish

### Interpretation rules

We should not rely on one venue only. Use the top venues by `turnover_24h`, then compute a turnover-weighted asymmetry score:

- bullish when `cost_to_move_down_usd` is materially larger than `cost_to_move_up_usd`
- bearish when `cost_to_move_up_usd` is materially larger than `cost_to_move_down_usd`
- neutral when the difference is small or mixed across top exchanges

This is especially valuable because it describes market structure, not just trailing returns.

### Suggested scoring use

Suggested metric:

- `depth_ratio = cost_to_move_down_usd / cost_to_move_up_usd`

Example scoring:

- `>= 1.20`: `+2`
- `1.05 to 1.19`: `+1`
- `0.95 to 1.04`: `0`
- `0.80 to 0.94`: `-1`
- `< 0.80`: `-2`

Implementation note:

- compute a turnover-weighted ratio across the top 3-5 venues
- ignore illiquid venues with low turnover to avoid noise

### Significance / update behavior

- Significance: high
- Frequency of impact: frequent

This can change often and should be treated as an active microstructure signal, especially for short-term and swing decision support.

## 4. Sector / Index Breadth Regime

### Endpoints

- `GET /currencies/sector-spotlight`
- `GET /indices`
- `GET /indices/{index_ticker}/market-snapshot`
- optionally `GET /indices/{index_ticker}/klines`

### Raw data shape

Sector spotlight provides:

- sector `name`
- sector `change_pct_24h`
- sector `marketcap_dom`
- spotlight theme `name`
- spotlight theme `change_pct_24h`

Recent live sample pulled on April 19, 2026:

- `BTC` sector: `change_pct_24h = -0.0064`, `marketcap_dom = 0.5867`
- `ETH` sector: `change_pct_24h = -0.0201`, `marketcap_dom = 0.1085`
- `Layer1` sector: `change_pct_24h = -0.0094`, `marketcap_dom = 0.0811`
- `AI` sector: `change_pct_24h = -0.0078`, `marketcap_dom = 0.0033`

Live index catalog pulled on April 19, 2026 includes:

- `ssiRWA`
- `ssiDeFi`
- `ssiMeme`
- `ssiAI`
- `ssiDePIN`
- `ssiSocialFi`
- `ssiMAG7`
- `ssiLayer1`
- `ssiPayFi`
- `ssiNFT`
- `ssiGameFi`
- `ssiCeFi`
- `ssiLayer2`

Recent live index snapshot samples:

- `ssiLayer1`: `24h = -1.08%`, `7d = +5.56%`, `1m = +4.17%`
- `ssiMAG7`: `24h = -0.70%`, `7d = +6.15%`, `1m = +1.99%`

### What it means

This metric measures whether the market move is broad or narrow.

That matters because narrow moves are less trustworthy than broad ones.

Examples:

- BTC up while major sectors and indices are also improving: stronger regime support
- BTC up while breadth is weak and most sectors are red: narrower and less durable move
- ETH bullish signal while Layer1 and ETH-related breadth are weak: lower confidence

Sector spotlight gives a coarse breadth map.
Indices give a better structured thematic confirmation layer.

### Interpretation rules

For BTC:

- bullish when BTC is strong and broad market proxies are not strongly diverging against it
- extra bullish when Layer1, CeFi, or MAG7-style crypto leaders are also improving
- bearish when BTC is trying to rally but broad sectors/themes are rolling over

For ETH:

- bullish when ETH sector and Layer1-style breadth are improving together
- bearish when ETH is weak relative to both BTC and broader L1 breadth

### Suggested scoring use

Use breadth as a confirmation component, not the lead signal.

Example scoring:

- `+2` when asset sector and at least one relevant index have positive short-term trend
- `+1` when breadth is mildly supportive
- `0` when mixed
- `-1` when breadth is broadly weak against the asset thesis
- `-2` when the asset is diverging sharply against broad sector/index weakness

Suggested index mapping:

- BTC: emphasize `ssiMAG7`, `ssiCeFi`, broad sector conditions, and BTC sector dominance behavior
- ETH: emphasize `ssiLayer1`, `ssiDeFi`, and ETH sector behavior

### Significance / update behavior

- Significance: medium to high
- Frequency of impact: moderate

This should not flip wildly intraday in our daily engine, but it can matter a lot when a move is trying to expand or fade.

## Recommended Engine Role

These four additions should not all carry equal weight.

Recommended practical hierarchy:

1. futures open interest
2. trading-pair depth asymmetry
3. sector/index breadth regime
4. fear & greed index

Reason:

- OI and depth asymmetry are closer to tradable structure
- breadth improves confidence and filters narrow moves
- FGI is best used as a regime modifier, not a primary trigger

## Proposed Usage Summary

Suggested behavior inside the engine:

- `futures_open_interest`: active structural component
- `depth_asymmetry`: active structural component
- `breadth_regime`: confirmation component
- `fear_greed`: regime modifier / confidence adjustment

If we want to keep the engine interpretable, we should avoid letting all four dominate at once. A clean approach is:

- let OI and depth contribute full component scores
- let breadth contribute a medium score
- let FGI either contribute a small score or adjust conviction only

## How Often These Matter

High-frequency / active:

- futures open interest
- trading-pair depth asymmetry

Moderate-frequency / contextual:

- sector/index breadth regime

Occasional / extreme-regime filter:

- fear & greed index

## ETF Endpoint vs Analysis ETF Charts

We should continue using the regular ETF endpoints as the canonical ETF source:

- `/etfs/summary-history`
- `/etfs/{ticker}/history`
- `/etfs/{ticker}/market-snapshot`

Why:

- they are more granular
- their fields are clearer
- they are easier to score directly

The `analyses` ETF charts are still useful as a context layer, but they should not replace the core ETF data we already use.

## Sources

- Analysis chart list:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/9.-analysis-charts/list
- Trading pairs:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/1.-currency-and-pairs/pairs
- Sector spotlight:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/1.-currency-and-pairs/sector-spotlight
- Index list:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/3.-sosovalue-index/list
- Index market snapshot:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/3.-sosovalue-index/market-snapshot
- Index klines:
  https://sosovalue-1.gitbook.io/sosovalue-api-doc/3.-sosovalue-index/klines
