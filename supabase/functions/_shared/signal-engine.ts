import type { SignalComponent } from "./types.ts";

function toFloat(value: unknown) {
  if (value === null || value === undefined || value === "") return 0;
  return Number(value);
}

function timestampMsToIso(timestampMs: number) {
  return new Date(timestampMs).toISOString().slice(0, 10);
}

function labelFromScore(score: number): SignalComponent["label"] {
  if (score > 0) return "bullish";
  if (score < 0) return "bearish";
  return "neutral";
}

export const ASSET_CONFIG: Record<string, Record<string, unknown>> = {
  BTC: {
    symbol: "BTCUSDT",
    etf_type: "us-btc-spot",
    currency_id: "1673723677362319866",
    sector_name: "BTC",
    index_tickers: ["ssiMAG7", "ssiCeFi"],
    positioning_chart: "binance_btcusdt_futures_long_short_ratio_1d",
    funding_chart: "funding_rate",
    has_futures_open_interest: true,
  },
  ETH: {
    symbol: "ETHUSDT",
    etf_type: "us-eth-spot",
    currency_id: "1673723677362319867",
    sector_name: "ETH",
    index_tickers: ["ssiLayer1", "ssiDeFi"],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
  SOL: {
    symbol: "SOLUSDT",
    etf_type: null,
    currency_id: "1673723677362319875",
    sector_name: "Layer1",
    index_tickers: ["ssiLayer1"],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
  XRP: {
    symbol: "XRPUSDT",
    etf_type: null,
    currency_id: "1673723677362319871",
    sector_name: "PayFi",
    index_tickers: ["ssiPayFi"],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
  ADA: {
    symbol: "ADAUSDT",
    etf_type: null,
    currency_id: "1673723677362319873",
    sector_name: "Layer1",
    index_tickers: ["ssiLayer1"],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
  DOGE: {
    symbol: "DOGEUSDT",
    etf_type: null,
    currency_id: "1673723677362319874",
    sector_name: "Meme",
    index_tickers: ["ssiMeme"],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
  AVAX: {
    symbol: "AVAXUSDT",
    etf_type: null,
    currency_id: "1673723677362319883",
    sector_name: "Layer1",
    index_tickers: ["ssiLayer1"],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
  LINK: {
    symbol: "LINKUSDT",
    etf_type: null,
    currency_id: "1673723677362319887",
    sector_name: "DeFi",
    index_tickers: ["ssiDeFi"],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
  HBAR: {
    symbol: "HBARUSDT",
    etf_type: null,
    currency_id: "1673723677362319900",
    sector_name: "Layer1",
    index_tickers: ["ssiLayer1"],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
  SUI: {
    symbol: "SUIUSDT",
    etf_type: null,
    currency_id: "1673723677362319954",
    sector_name: "Layer1",
    index_tickers: ["ssiLayer1"],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
  BNB: {
    symbol: "BNBUSDT",
    etf_type: null,
    currency_id: "1673723677362319869",
    sector_name: "CeFi",
    index_tickers: ["ssiCeFi"],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
  SOSO: {
    symbol: "SOSOUSDT",
    etf_type: null,
    currency_id: null,
    sector_name: null,
    index_tickers: [],
    positioning_chart: null,
    funding_chart: null,
    has_futures_open_interest: false,
  },
};

const FUNDING_EXTREME_THRESHOLD = 0.0001;
const ETF_WEIGHTED_STRONG_SCORE = 3;
const ETF_CONTRADICTION_CAP_SCORE = 2;

export function summarizeUnavailableComponent(name: string, asset: string, reason: string): SignalComponent {
  return { name, score: 0, label: "unavailable", details: { asset, reason } };
}

function summarizeMissingEtf(asset: string): SignalComponent {
  return summarizeUnavailableComponent("etf_trend", asset, "No ETF source configured for this asset");
}

function summarizeEtfTrend(rows: Record<string, unknown>[]): SignalComponent {
  if (!rows.length) throw new Error("ETF historical data is empty");
  const latest = rows[0];
  const recent = rows.slice(0, 5);
  const latestInflow = toFloat(latest.totalNetInflow);
  const recentInflows = recent.map((row) => toFloat(row.totalNetInflow));
  const positiveDays = recentInflows.filter((value) => value > 0).length;
  const fiveDaySum = recentInflows.reduce((sum, value) => sum + value, 0);

  let score = 0;
  if (latestInflow > 0) score += 1;
  else if (latestInflow < 0) score -= 1;
  if (fiveDaySum > 0) score += 1;
  else if (fiveDaySum < 0) score -= 1;

  return {
    name: "etf_trend",
    score,
    label: labelFromScore(score),
    details: {
      latest_date: latest.date,
      latest_net_inflow_usd: latestInflow,
      five_day_net_inflow_usd: fiveDaySum,
      positive_days_last_5: positiveDays,
    },
  };
}

function summarizePositioning(rows: Record<string, unknown>[]): SignalComponent {
  if (!rows.length) throw new Error("Positioning data is empty");
  const latest = rows[rows.length - 1];
  const ratios = rows.map((row) => toFloat(row.longShortRatio));
  const latestRatio = toFloat(latest.longShortRatio);
  const avgRatio = ratios.reduce((sum, value) => sum + value, 0) / ratios.length;
  let score = 0;
  if (latestRatio > 1.0) score += 1;
  else if (latestRatio < 0.95) score -= 1;
  if (latestRatio > avgRatio) score += 1;
  else if (latestRatio < avgRatio) score -= 1;
  return {
    name: "positioning",
    score,
    label: labelFromScore(score),
    details: {
      latest_date: timestampMsToIso(Number(latest.timestamp ?? 0)),
      latest_long_short_ratio: latestRatio,
      latest_long_account_share: toFloat(latest.longAccount),
      latest_short_account_share: toFloat(latest.shortAccount),
      average_ratio_sample: avgRatio,
    },
  };
}

function summarizePriceConfirmation(klines: Record<string, unknown>[]): SignalComponent {
  if (klines.length < 5) throw new Error("At least 5 klines are required");
  const ordered = [...klines].sort((a, b) => Number(a.t) - Number(b.t));
  const closes = ordered.map((row) => toFloat(row.c));
  const latest = ordered[ordered.length - 1];
  const latestClose = toFloat(latest.c);
  const latestOpen = toFloat(latest.o);
  const sma3 = closes.slice(-3).reduce((sum, value) => sum + value, 0) / 3;
  const sma5 = closes.reduce((sum, value) => sum + value, 0) / closes.length;
  const dailyReturnPct = ((latestClose / latestOpen) - 1) * 100;
  const sampleReturnPct = ((closes[closes.length - 1] / closes[0]) - 1) * 100;
  let score = 0;
  if (latestClose > sma3) score += 1;
  else if (latestClose < sma3) score -= 1;
  if (sma3 > sma5) score += 1;
  else if (sma3 < sma5) score -= 1;
  return {
    name: "price_confirmation",
    score,
    label: labelFromScore(score),
    details: {
      latest_date: timestampMsToIso(Number(latest.t ?? 0)),
      latest_close: latestClose,
      daily_return_pct: dailyReturnPct,
      sample_return_pct: sampleReturnPct,
      sma_3: sma3,
      sma_5: sma5,
      source: latest.source ?? "market_klines",
    },
  };
}

function summarizeFunding(rows: Record<string, unknown>[]): SignalComponent {
  if (!rows.length) throw new Error("Funding data is empty");
  const latest = rows[rows.length - 1];
  const latestFunding = toFloat(latest.fundingRate);
  const avgFunding = rows.reduce((sum, row) => sum + toFloat(row.fundingRate), 0) / rows.length;
  let score = 0;
  if (latestFunding > FUNDING_EXTREME_THRESHOLD) score -= 1;
  else if (latestFunding < -FUNDING_EXTREME_THRESHOLD) score += 1;
  if (latestFunding > avgFunding) score -= 1;
  else if (latestFunding < avgFunding) score += 1;
  return {
    name: "funding_rates",
    score,
    label: labelFromScore(score),
    details: {
      latest_time: timestampMsToIso(Number(latest.fundingTime ?? 0)),
      latest_funding_rate: latestFunding,
      average_funding_rate_sample: avgFunding,
      extreme_threshold: FUNDING_EXTREME_THRESHOLD,
      sample_size: rows.length,
      mark_price: toFloat(latest.markPrice),
    },
  };
}

function summarizeFearGreed(rows: Record<string, unknown>[]): SignalComponent {
  if (!rows.length) throw new Error("Fear & greed data is empty");
  const latest = rows[0];
  const previous = rows[1] ?? latest;
  const latestValue = toFloat(latest["crypto_fear_&_greed_index"]);
  const previousValue = toFloat(previous["crypto_fear_&_greed_index"]);
  let score = 0;
  if (latestValue <= 25 && latestValue >= previousValue) score = 1;
  else if (latestValue >= 75 && latestValue >= previousValue) score = -1;
  return {
    name: "fear_greed",
    score,
    label: labelFromScore(score),
    details: {
      latest_date: timestampMsToIso(Number(latest.timestamp ?? 0)),
      latest_index_value: latestValue,
      previous_index_value: previousValue,
    },
  };
}

function summarizeFuturesOpenInterest(rows: Record<string, unknown>[]): SignalComponent {
  if (rows.length < 2) throw new Error("At least 2 futures open-interest rows are required");
  const latest = rows[0];
  const previous = rows[1];
  const latestOi = toFloat(latest.all);
  const previousOi = toFloat(previous.all);
  const latestPrice = toFloat(latest.btc_price);
  const previousPrice = toFloat(previous.btc_price);
  const oiChangePct = previousOi ? ((latestOi / previousOi) - 1) * 100 : 0;
  const priceChangePct = previousPrice ? ((latestPrice / previousPrice) - 1) * 100 : 0;
  let score = 0;
  if (oiChangePct > 1 && priceChangePct >= 0) score = 2;
  else if (oiChangePct > 0.5 && priceChangePct >= -0.5) score = 1;
  else if (oiChangePct > 1 && priceChangePct < -0.5) score = -2;
  else if (oiChangePct > 0.5 && priceChangePct < 0) score = -1;
  return {
    name: "futures_open_interest",
    score,
    label: labelFromScore(score),
    details: {
      latest_date: timestampMsToIso(Number(latest.timestamp ?? 0)),
      latest_open_interest: latestOi,
      previous_open_interest: previousOi,
      open_interest_change_pct: oiChangePct,
      latest_reference_price: latestPrice,
      reference_price_change_pct: priceChangePct,
      binance_open_interest: toFloat(latest.binance),
      cme_open_interest: toFloat(latest.cme),
    },
  };
}

function summarizeDepthAsymmetry(asset: string, rows: Record<string, unknown>[]): SignalComponent {
  if (!rows.length) throw new Error("Pair depth data is empty");
  const topRows = [...rows].sort((a, b) => toFloat(b.turnover_24h) - toFloat(a.turnover_24h)).slice(0, 5);
  const totalTurnover = topRows.reduce((sum, row) => sum + toFloat(row.turnover_24h), 0) || 1;
  let weightedUp = 0;
  let weightedDown = 0;
  const markets = topRows.map((row) => {
    const turnover = toFloat(row.turnover_24h);
    const weight = turnover / totalTurnover;
    const up = toFloat(row.cost_to_move_up_usd);
    const down = toFloat(row.cost_to_move_down_usd);
    weightedUp += up * weight;
    weightedDown += down * weight;
    return {
      market: row.market,
      price: toFloat(row.price),
      turnover_24h: turnover,
      cost_to_move_up_usd: up,
      cost_to_move_down_usd: down,
    };
  });
  const depthRatio = weightedUp ? weightedDown / weightedUp : 1;
  const score = depthRatio >= 1.2 ? 2 : depthRatio >= 1.05 ? 1 : depthRatio > 0.94 ? 0 : depthRatio >= 0.8 ? -1 : -2;
  return {
    name: "depth_asymmetry",
    score,
    label: labelFromScore(score),
    details: {
      asset,
      depth_ratio: depthRatio,
      weighted_cost_to_move_up_usd: weightedUp,
      weighted_cost_to_move_down_usd: weightedDown,
      markets_used: markets,
    },
  };
}

function getSectorRow(sectorPayload: Record<string, unknown>, sectorName: string) {
  const sectors = Array.isArray(sectorPayload.sector) ? sectorPayload.sector as Record<string, unknown>[] : [];
  return sectors.find((row) => String(row.name ?? "").trim().toUpperCase() === sectorName.toUpperCase()) ?? null;
}

function summarizeBreadthRegime(asset: string, sectorPayload: Record<string, unknown>, indexSnapshots: Record<string, Record<string, unknown>>): SignalComponent {
  const config = ASSET_CONFIG[asset];
  const sectorName = String(config.sector_name ?? "");
  if (!sectorName) {
    return summarizeUnavailableComponent("breadth_regime", asset, "No breadth mapping configured for this asset");
  }
  const sectorRow = getSectorRow(sectorPayload, sectorName);
  const sectorChange = sectorRow ? toFloat(sectorRow.change_pct_24h) : 0;
  const sectorDom = sectorRow ? toFloat(sectorRow.marketcap_dom) : 0;
  const relevant = Object.fromEntries(Object.entries(indexSnapshots).filter(([, snapshot]) => snapshot && Object.keys(snapshot).length));
  const positive = Object.values(relevant).filter((snapshot) => toFloat(snapshot.roi_7d) > 0).length;
  const negative = Object.values(relevant).filter((snapshot) => toFloat(snapshot.roi_7d) < 0).length;
  let score = 0;
  if (sectorChange > 0 && positive >= 1) score = 1;
  else if (sectorChange < 0 && negative >= 1) score = -1;
  return {
    name: "breadth_regime",
    score,
    label: labelFromScore(score),
    details: {
      sector_name: sectorName,
      sector_change_pct_24h: sectorChange,
      sector_marketcap_dom: sectorDom,
      index_snapshots: relevant,
    },
  };
}

function weightedComponentScore(component: SignalComponent) {
  if (component.label === "unavailable") return 0;
  if (component.name === "etf_trend") {
    if (component.score >= 2) return ETF_WEIGHTED_STRONG_SCORE;
    if (component.score <= -2) return -ETF_WEIGHTED_STRONG_SCORE;
  }
  return component.score;
}

function componentScoreCap(component: SignalComponent) {
  if (component.label === "unavailable") return 0;
  if (component.name === "etf_trend") return ETF_WEIGHTED_STRONG_SCORE;
  if (component.name === "breadth_regime" || component.name === "fear_greed") return 1;
  return 2;
}

function scoreBands(maxScore: number) {
  const mediumThreshold = Math.max(1, Math.round(maxScore * (4 / 15)));
  const highThreshold = Math.max(mediumThreshold + 1, Math.round(maxScore * (8 / 15)));
  return { mediumThreshold, highThreshold };
}

function applyEtfPriceConflictRule(
  etfComponent: SignalComponent,
  priceComponent: SignalComponent,
  weightedScores: Record<string, number>,
) {
  const adjusted = { ...weightedScores };
  const etfScore = adjusted[etfComponent.name] ?? 0;
  const priceScore = adjusted[priceComponent.name] ?? 0;
  if (etfScore >= ETF_CONTRADICTION_CAP_SCORE && priceScore === -2) {
    adjusted[etfComponent.name] = ETF_CONTRADICTION_CAP_SCORE;
  } else if (etfScore <= -ETF_CONTRADICTION_CAP_SCORE && priceScore === 2) {
    adjusted[etfComponent.name] = -ETF_CONTRADICTION_CAP_SCORE;
  }
  return adjusted;
}

function finalizeSignalSnapshot(asset: string, components: SignalComponent[]) {
  const weightedScores = Object.fromEntries(components.map((component) => [component.name, weightedComponentScore(component)]));
  const componentMap = Object.fromEntries(components.map((component) => [component.name, component]));
  const adjustedScores = applyEtfPriceConflictRule(
    componentMap.etf_trend,
    componentMap.price_confirmation,
    weightedScores,
  );
  const available = components.filter((component) => component.label !== "unavailable");
  const unavailable = components.filter((component) => component.label === "unavailable").map((component) => component.name);
  const maxScore = components.reduce((sum, component) => sum + componentScoreCap(component), 0);
  const { mediumThreshold } = scoreBands(maxScore);
  const totalScore = Object.values(adjustedScores).reduce((sum, value) => sum + value, 0);
  const overallSignal = totalScore >= mediumThreshold ? "bullish" : totalScore <= -mediumThreshold ? "bearish" : "neutral";

  return {
    asset,
    overall_signal: overallSignal,
    total_score: totalScore,
    available_component_count: available.length,
    unavailable_components: unavailable,
    max_score: maxScore,
    components: components.map((component) => ({
      name: component.name,
      label: component.label,
      score: adjustedScores[component.name],
      details: {
        ...component.details,
        raw_score: component.score,
        effective_score: adjustedScores[component.name],
      },
    })),
  };
}

export function buildAssetSignalSnapshot(
  asset: string,
  {
    etfRows,
    positioningRows,
    klines,
    fundingRows,
    fearGreedRows,
    futuresOpenInterestRows,
    pairRows,
    sectorPayload,
    indexSnapshots,
  }: {
    etfRows: Record<string, unknown>[] | null;
    positioningRows: Record<string, unknown>[] | null;
    klines: Record<string, unknown>[] | null;
    fundingRows: Record<string, unknown>[] | null;
    fearGreedRows: Record<string, unknown>[] | null;
    futuresOpenInterestRows: Record<string, unknown>[] | null;
    pairRows: Record<string, unknown>[] | null;
    sectorPayload: Record<string, unknown>;
    indexSnapshots: Record<string, Record<string, unknown>>;
  },
) {
  const normalizedAsset = asset.toUpperCase();
  const components: SignalComponent[] = [
    etfRows ? summarizeEtfTrend(etfRows) : summarizeMissingEtf(normalizedAsset),
    positioningRows ? summarizePositioning(positioningRows) : summarizeUnavailableComponent("positioning", normalizedAsset, "No positioning source configured for this asset"),
    klines ? summarizePriceConfirmation(klines) : summarizeUnavailableComponent("price_confirmation", normalizedAsset, "No price source configured for this asset"),
    fundingRows ? summarizeFunding(fundingRows) : summarizeUnavailableComponent("funding_rates", normalizedAsset, "No funding source configured for this asset"),
    futuresOpenInterestRows ? summarizeFuturesOpenInterest(futuresOpenInterestRows) : summarizeUnavailableComponent("futures_open_interest", normalizedAsset, "No futures open-interest source configured for this asset"),
    pairRows ? summarizeDepthAsymmetry(normalizedAsset, pairRows) : summarizeUnavailableComponent("depth_asymmetry", normalizedAsset, "No trading pair depth data is available for this asset"),
    summarizeBreadthRegime(normalizedAsset, sectorPayload, indexSnapshots),
    fearGreedRows ? summarizeFearGreed(fearGreedRows) : summarizeUnavailableComponent("fear_greed", normalizedAsset, "Fear & greed data is unavailable"),
  ];
  return finalizeSignalSnapshot(normalizedAsset, components);
}

