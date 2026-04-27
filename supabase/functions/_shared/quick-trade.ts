export const BTC_ETH_QUICK_TRADE_CONFIG: Record<string, { symbol: string; sodex_symbol: string }> = {
  BTC: { symbol: "BTCUSDT", sodex_symbol: "BTC-USD" },
  ETH: { symbol: "ETHUSDT", sodex_symbol: "ETH-USD" },
};

export const REFRESH_INTERVAL_MINUTES = 15;
export const CLIENT_MAX_DATA_AGE_MINUTES = 10;
export const CLIENT_REFRESH_BUFFER_MINUTES = 1;

function iso(dt: Date) {
  return dt.toISOString();
}

function safeFloat(value: unknown) {
  return value === null || value === undefined || value === "" ? null : Number(value);
}

function safeInt(value: unknown) {
  return value === null || value === undefined || value === "" ? null : Number(value);
}

function normalizeKlineRow(row: Record<string, unknown>) {
  return {
    open_time_ms: safeInt(row.t),
    open: safeFloat(row.o),
    high: safeFloat(row.h),
    low: safeFloat(row.l),
    close: safeFloat(row.c),
    base_volume: safeFloat(row.v),
    quote_volume: safeFloat(row.a),
    symbol: row.s ?? null,
  };
}

function normalizeFundingRow(row: Record<string, unknown>) {
  return {
    funding_time_ms: safeInt(row.fundingTime),
    funding_rate: safeFloat(row.fundingRate),
    mark_price: safeFloat(row.markPrice),
    symbol: row.symbol ?? null,
  };
}

function normalizeLongShortRow(row: Record<string, unknown>) {
  return {
    timestamp_ms: safeInt(row.timestamp),
    long_short_ratio: safeFloat(row.longShortRatio),
    long_account_share: safeFloat(row.longAccount),
    short_account_share: safeFloat(row.shortAccount),
    symbol: row.symbol ?? null,
  };
}

function normalizeOpenInterestRow(row: Record<string, unknown>) {
  return {
    timestamp_ms: safeInt(row.timestamp),
    sum_open_interest: safeFloat(row.sumOpenInterest),
    sum_open_interest_value: safeFloat(row.sumOpenInterestValue),
    symbol: row.symbol ?? null,
  };
}

function strategyPlaybook() {
  return {
    breakout_continuation: {
      label: "Breakout Continuation",
      purpose: "Catch fresh range breaks with follow-through.",
      primary_timeframe: "5m",
      confirmation_timeframe: "15m",
      client_rules: {
        range_lookback_candles_5m: 12,
        close_buffer_pct: 0.0004,
        follow_through_candles: 2,
        volume_sma_candles: 20,
      },
    },
    trend_pullback: {
      label: "Trend Pullback",
      purpose: "Join an existing trend after a controlled pullback.",
      primary_timeframe: "15m",
      confirmation_timeframe: "1h",
      client_rules: {
        trend_sma_fast: 20,
        trend_sma_slow: 50,
        reclaim_sma: 20,
        max_pullback_pct_from_fast_sma: 0.006,
      },
    },
    failed_break_reclaim: {
      label: "Failed Break / Reclaim",
      purpose: "Trade fast reversals after a liquidity sweep.",
      primary_timeframe: "5m",
      confirmation_timeframe: "15m",
      client_rules: {
        sweep_lookback_candles_5m: 20,
        reclaim_close_buffer_pct: 0.0003,
        reversal_follow_through_candles: 2,
      },
    },
    funding_oi_confirmation: {
      label: "Funding + OI Confirmation",
      purpose: "Confirm price moves with derivatives positioning context.",
      primary_timeframe: "5m",
      confirmation_timeframe: "5m",
      client_rules: {
        open_interest_change_window: 6,
        open_interest_expansion_pct: 0.8,
        funding_overheat_threshold: 0.0001,
        long_short_ratio_ceiling: 1.35,
        long_short_ratio_floor: 0.75,
      },
    },
  };
}

export function buildQuickTradeInputPayload({
  asset,
  symbol,
  sodexSymbol,
  klines5m,
  klines15m,
  klines1h,
  fundingRows,
  longShortRows,
  openInterestRows,
}: {
  asset: string;
  symbol: string;
  sodexSymbol: string;
  klines5m: Record<string, unknown>[];
  klines15m: Record<string, unknown>[];
  klines1h: Record<string, unknown>[];
  fundingRows: Record<string, unknown>[];
  longShortRows: Record<string, unknown>[];
  openInterestRows: Record<string, unknown>[];
}) {
  const snapshotAt = new Date();
  const freshUntil = new Date(snapshotAt.getTime() + CLIENT_MAX_DATA_AGE_MINUTES * 60_000);
  const nextExpected = new Date(snapshotAt.getTime() + REFRESH_INTERVAL_MINUTES * 60_000);
  const waitUntil = new Date(nextExpected.getTime() + CLIENT_REFRESH_BUFFER_MINUTES * 60_000);
  const latestClose = klines5m.length ? safeFloat(klines5m[klines5m.length - 1].c) : null;

  return {
    engine: "quick_trade_inputs_v1",
    updated_at: iso(snapshotAt),
    asset,
    symbol,
    market: "perps",
    sodex_symbol: sodexSymbol,
    server_schedule: {
      refresh_interval_minutes: REFRESH_INTERVAL_MINUTES,
      client_max_data_age_minutes: CLIENT_MAX_DATA_AGE_MINUTES,
      client_refresh_buffer_minutes: CLIENT_REFRESH_BUFFER_MINUTES,
      fresh_until: iso(freshUntil),
      next_expected_update_at: iso(nextExpected),
      wait_for_next_refresh_until: iso(waitUntil),
      client_rule: "If snapshot age is greater than 10 minutes, do not open a new quick trade. Wait until wait_for_next_refresh_until before trusting a new setup.",
    },
    latest_context: {
      reference_price: latestClose,
      reference_price_source: "sodex_perps_5m",
    },
    datasets: {
      klines: {
        "5m": klines5m.map(normalizeKlineRow),
        "15m": klines15m.map(normalizeKlineRow),
        "1h": klines1h.map(normalizeKlineRow),
      },
      funding_rates: fundingRows.map(normalizeFundingRow),
      long_short_ratio_1h: longShortRows.map(normalizeLongShortRow),
      open_interest_5m: openInterestRows.map(normalizeOpenInterestRow),
    },
    strategy_playbook: strategyPlaybook(),
  };
}

