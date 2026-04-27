function utcNowIso() {
  return new Date().toISOString();
}

export function buildEngineSummaryCache(outputs: Record<string, { signal: Record<string, unknown>; decision: Record<string, unknown> }>) {
  const assets: Record<string, unknown> = {};
  for (const [asset, output] of Object.entries(outputs)) {
    assets[asset] = {
      asset: output.signal.asset,
      overall_signal: output.signal.overall_signal,
      total_score: output.signal.total_score,
      action: output.decision.action,
      market_bias: output.decision.market_bias,
      conviction: output.decision.conviction,
      position_size_bucket: output.decision.position_size_bucket,
      why: output.decision.why,
      invalidations: output.decision.invalidations,
    };
  }
  return {
    updated_at: utcNowIso(),
    assets,
  };
}

export function buildMarketOverviewCache({
  fearGreedRows,
  futuresOpenInterestRows,
  sectorPayload,
  etfMetrics,
}: {
  fearGreedRows: Record<string, unknown>[];
  futuresOpenInterestRows: Record<string, unknown>[];
  sectorPayload: Record<string, unknown>;
  etfMetrics: Record<string, Record<string, unknown>>;
}) {
  return {
    updated_at: utcNowIso(),
    fear_greed: {
      latest: fearGreedRows[0] ?? {},
      previous: fearGreedRows[1] ?? fearGreedRows[0] ?? {},
      series: fearGreedRows,
    },
    futures_open_interest: {
      latest: futuresOpenInterestRows[0] ?? {},
      series: futuresOpenInterestRows,
    },
    sector_spotlight: sectorPayload,
    etf_metrics: etfMetrics,
  };
}

