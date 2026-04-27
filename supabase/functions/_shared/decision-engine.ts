import type { Action, Conviction, MarketBias } from "./types.ts";

function componentsByName(signal: Record<string, unknown>) {
  const components = Array.isArray(signal.components) ? signal.components as Record<string, unknown>[] : [];
  return Object.fromEntries(components.map((component) => [String(component.name), component]));
}

function scoreBands(maxScore: number) {
  const mediumThreshold = Math.max(1, Math.round(maxScore * (4 / 15)));
  const highThreshold = Math.max(mediumThreshold + 1, Math.round(maxScore * (8 / 15)));
  return { mediumThreshold, highThreshold };
}

function baseBiasAndConviction(totalScore: number, maxScore: number): [MarketBias, Conviction] {
  const { mediumThreshold, highThreshold } = scoreBands(maxScore);
  if (totalScore >= highThreshold) return ["long", "high"];
  if (totalScore >= mediumThreshold) return ["long", "medium"];
  if (totalScore > -mediumThreshold && totalScore < mediumThreshold) return ["neutral", "low"];
  if (totalScore > -highThreshold) return ["short", "medium"];
  return ["short", "high"];
}

function agreementState(components: Record<string, Record<string, unknown>>) {
  const available = Object.values(components).filter((component) => component.label !== "unavailable");
  const bullish = available.filter((component) => component.label === "bullish").length;
  const bearish = available.filter((component) => component.label === "bearish").length;
  const threshold = available.length ? Math.max(2, Math.ceil(available.length * 0.625)) : 2;
  if (bullish >= threshold) return { agreement: "strong", direction: "bullish" };
  if (bearish >= threshold) return { agreement: "strong", direction: "bearish" };
  return { agreement: "mixed", direction: null };
}

function downgradeConviction(conviction: Conviction): Conviction {
  return conviction === "high" ? "medium" : "low";
}

function positionSizeBucket(action: Action, conviction: Conviction) {
  if (action === "wait") return "small";
  if (conviction === "high") return "large";
  if (conviction === "medium") return "medium";
  return "small";
}

function fundingStronglyBearish(component: Record<string, unknown>) {
  return component.label !== "unavailable" && Number(component.score ?? 0) <= -2;
}

function fundingExtremelyNegative(component: Record<string, unknown>) {
  if (component.label === "unavailable") return false;
  const details = (component.details ?? {}) as Record<string, unknown>;
  return Number(details.latest_funding_rate ?? 0) <= Number(details.extreme_threshold ?? 0) * -1;
}

function buildWhy(action: Action, marketBias: MarketBias, agreement: string, components: Record<string, Record<string, unknown>>) {
  const reasons: string[] = [];
  const reasonMap: Record<string, Record<string, string>> = {
    etf_trend: { bullish: "ETF trend is bullish", bearish: "ETF trend is bearish" },
    price_confirmation: { bullish: "price confirmation is supportive", bearish: "price confirmation is weakening" },
    positioning: { bullish: "positioning is supporting the long side", bearish: "positioning is favoring the short side" },
    funding_rates: { bullish: "funding is not overcrowded against longs", bearish: "funding is less supportive for aggressive leverage" },
    futures_open_interest: { bullish: "open interest is confirming the move", bearish: "open interest is building against weak price" },
    depth_asymmetry: { bullish: "spot depth is more resilient on the downside", bearish: "spot depth looks fragile on the downside" },
    breadth_regime: { bullish: "breadth is supporting the asset move", bearish: "breadth is diverging against the asset move" },
    fear_greed: { bullish: "fear is elevated but stabilizing", bearish: "greed is stretched" },
  };
  const priority = ["etf_trend", "price_confirmation", "futures_open_interest", "depth_asymmetry", "positioning", "funding_rates", "breadth_regime", "fear_greed"];
  for (const name of priority) {
    const component = components[name];
    if (!component) continue;
    const message = reasonMap[name]?.[String(component.label)];
    if (message) reasons.push(message);
  }
  if (agreement === "mixed") reasons.push("signals are mixed across components");
  if (action === "wait" && marketBias === "neutral") reasons.push("overall score does not show a strong directional edge");
  return reasons.slice(0, 4);
}

function buildInvalidations(action: Action, marketBias: MarketBias, components: Record<string, Record<string, unknown>>) {
  const invalidations: string[] = [];
  const etfAvailable = components.etf_trend?.label !== "unavailable";
  const positioningAvailable = components.positioning?.label !== "unavailable";
  const fundingAvailable = components.funding_rates?.label !== "unavailable";
  const oiAvailable = components.futures_open_interest?.label !== "unavailable";

  if (action === "spot_long" || action === "perps_long") {
    invalidations.push("price component flips bearish");
    invalidations.push("depth asymmetry turns bearish");
    if (etfAvailable) invalidations.push("ETF 5-day flow turns negative");
    if (oiAvailable) invalidations.push("open interest starts building against price");
  } else if (action === "perps_short") {
    invalidations.push("price component flips bullish");
    invalidations.push("depth asymmetry turns bullish");
    if (positioningAvailable) invalidations.push("positioning stops supporting the short");
    if (fundingAvailable) invalidations.push("funding becomes too negative for fresh shorts");
  } else if (marketBias === "long") {
    invalidations.push("price confirmation turns clearly bullish with stronger agreement");
    invalidations.push("depth asymmetry improves materially");
  } else if (marketBias === "short") {
    invalidations.push("price confirmation turns clearly bearish with stronger agreement");
    invalidations.push("breadth deteriorates further against the asset");
  } else {
    invalidations.push("at least 5 components align in one direction");
    invalidations.push("total score moves out of the neutral band");
  }

  return invalidations.slice(0, 4);
}

export function decideFromSignal(signal: Record<string, unknown>) {
  const totalScore = Number(signal.total_score ?? 0);
  const maxScore = Number(signal.max_score ?? 15);
  const { mediumThreshold, highThreshold } = scoreBands(maxScore);
  const components = componentsByName(signal);
  let [marketBias, conviction] = baseBiasAndConviction(totalScore, maxScore);
  const { agreement, direction } = agreementState(components);
  if (agreement === "mixed") conviction = downgradeConviction(conviction);

  const etf = components.etf_trend ?? {};
  const price = components.price_confirmation ?? {};
  const positioning = components.positioning ?? {};
  const funding = components.funding_rates ?? {};
  const openInterest = components.futures_open_interest ?? {};
  const depth = components.depth_asymmetry ?? {};
  const hasDerivativesConfirmation = funding.label !== "unavailable" || openInterest.label !== "unavailable";

  let action: Action = "wait";
  if (
    totalScore >= highThreshold &&
    price.label === "bullish" &&
    depth.label !== "bearish" &&
    ["bullish", "neutral", "unavailable"].includes(String(openInterest.label)) &&
    ["bullish", "neutral", "unavailable"].includes(String(funding.label)) &&
    hasDerivativesConfirmation &&
    agreement === "strong" &&
    direction === "bullish" &&
    marketBias === "long" &&
    conviction !== "low"
  ) {
    action = "perps_long";
  } else if (
    totalScore >= mediumThreshold &&
    ["bullish", "unavailable"].includes(String(etf.label)) &&
    price.label !== "bearish" &&
    depth.label !== "bearish" &&
    !fundingStronglyBearish(funding) &&
    marketBias === "long" &&
    conviction !== "low"
  ) {
    action = "spot_long";
  } else if (
    totalScore <= -highThreshold &&
    price.label === "bearish" &&
    ["bearish", "unavailable"].includes(String(positioning.label)) &&
    depth.label === "bearish" &&
    !fundingExtremelyNegative(funding) &&
    agreement === "strong" &&
    direction === "bearish" &&
    marketBias === "short" &&
    conviction !== "low"
  ) {
    action = "perps_short";
  }

  return {
    asset: String(signal.asset ?? ""),
    market_bias: marketBias,
    conviction,
    action,
    setup: action === "wait" ? "wait" : "trend_follow",
    position_size_bucket: positionSizeBucket(action, conviction),
    why: buildWhy(action, marketBias, agreement, components),
    invalidations: buildInvalidations(action, marketBias, components),
  };
}

