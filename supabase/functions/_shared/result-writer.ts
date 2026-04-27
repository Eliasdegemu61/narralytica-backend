function utcNowIso() {
  return new Date().toISOString();
}

function componentMap(signal: Record<string, unknown>) {
  const components = Array.isArray(signal.components) ? signal.components as Record<string, unknown>[] : [];
  return Object.fromEntries(components.map((component) => [String(component.name), component]));
}

function snapshotMetadata(signal: Record<string, unknown>) {
  const priceComponent = componentMap(signal).price_confirmation ?? {};
  const details = (priceComponent.details ?? {}) as Record<string, unknown>;
  return {
    snapshot_time_utc: utcNowIso(),
    asset: signal.asset,
    reference_price: details.latest_close ?? null,
    reference_price_date: details.latest_date ?? null,
    price_source: details.source ?? "unknown",
  };
}

function visualScore(component: Record<string, unknown>) {
  const label = String(component.label ?? "neutral");
  const score = Number(component.score ?? 0);
  if (label === "bullish") return Math.min(95, 55 + score * 15);
  if (label === "bearish") return Math.max(5, 45 + score * 15);
  if (label === "unavailable") return 50;
  return 50;
}

function componentStory(component: Record<string, unknown>) {
  const name = String(component.name ?? "");
  const details = (component.details ?? {}) as Record<string, unknown>;
  const unavailable = component.label === "unavailable";

  const base = {
    name,
    state: component.label,
    score: component.score,
    score_display: unavailable ? "Unavailable" : component.score,
    visual_score: visualScore(component),
    summary: "Component state unavailable.",
    calc_hint: "Derived from the current signal engine.",
    evidence: details,
  };

  const variants: Record<string, Record<string, unknown>> = {
    etf_trend: {
      name: "ETF Trend",
      summary: unavailable ? "ETF data is unavailable for this asset." : component.label === "bullish" ? "ETF flows remain supportive." : "ETF flow momentum is fading.",
      calc_hint: "Latest ETF flow and the recent 5-period aggregate are used to frame institutional demand.",
    },
    positioning: {
      name: "Positioning",
      summary: unavailable ? "Positioning data is unavailable for this asset." : component.label === "bullish" ? "Positioning supports the long side." : component.label === "bearish" ? "Short-side positioning still dominates." : "Positioning is balanced rather than directional.",
      calc_hint: "The latest long-short ratio is compared with both 1.0 and its recent average.",
    },
    price_confirmation: {
      name: "Price Confirmation",
      summary: unavailable ? "Price data is unavailable for this asset." : component.label === "bullish" ? "Price is confirming momentum." : component.label === "bearish" ? "Price action is weakening." : "Price is holding without full confirmation.",
      calc_hint: "Recent close, daily return, and short moving averages are compared for confirmation.",
    },
    funding_rates: {
      name: "Funding",
      summary: unavailable ? "Funding data is unavailable for this asset." : component.label === "bullish" ? "Funding is easing crowding pressure." : component.label === "bearish" ? "Funding argues against aggressive leverage." : "Funding is not showing a strong edge.",
      calc_hint: "Latest funding is compared with both an extreme threshold and the recent average.",
    },
    futures_open_interest: {
      name: "Futures Open Interest",
      summary: unavailable ? "Open-interest data is unavailable for this asset." : component.label === "bullish" ? "Open interest is confirming price participation." : component.label === "bearish" ? "Open interest is building against weak price." : "Open interest is not giving a strong edge.",
      calc_hint: "Recent total open interest is compared with price direction to detect leverage support or crowding.",
    },
    depth_asymmetry: {
      name: "Depth Asymmetry",
      summary: unavailable ? "Pair-depth data is unavailable for this asset." : component.label === "bullish" ? "Spot depth is more resilient on the downside." : component.label === "bearish" ? "Spot depth looks fragile on the downside." : "Spot depth is balanced rather than directional.",
      calc_hint: "Turnover-weighted pair depth compares the cost to move price down versus up by 2%.",
    },
    breadth_regime: {
      name: "Breadth Regime",
      summary: unavailable ? "Breadth data is unavailable for this asset." : component.label === "bullish" ? "Breadth is supporting the asset move." : component.label === "bearish" ? "Breadth is diverging against the asset move." : "Breadth is mixed across sectors and indices.",
      calc_hint: "Relevant sector performance and index snapshots are used to judge whether the move is broad or narrow.",
    },
    fear_greed: {
      name: "Fear & Greed",
      summary: unavailable ? "Fear & greed data is unavailable." : component.label === "bullish" ? "Fear is elevated but stabilizing." : component.label === "bearish" ? "Greed is stretched." : "Sentiment is not at an extreme.",
      calc_hint: "Fear & greed is used as a light regime filter rather than a primary trigger.",
    },
  };

  return {
    ...base,
    ...(variants[name] ?? {}),
  };
}

export function buildSignalStory(signal: Record<string, unknown>, decision: Record<string, unknown>) {
  const components = componentMap(signal);
  const signalComponents = Array.isArray(signal.components) ? signal.components as Record<string, unknown>[] : [];
  const bullish = signalComponents.filter((component) => component.label === "bullish").map((component) => String(component.name));
  const bearish = signalComponents.filter((component) => component.label === "bearish").map((component) => String(component.name));
  const titleMap: Record<string, string> = {
    etf_trend: "ETF Trend",
    positioning: "Positioning",
    price_confirmation: "Price Confirmation",
    funding_rates: "Funding",
    futures_open_interest: "Futures Open Interest",
    depth_asymmetry: "Depth Asymmetry",
    breadth_regime: "Breadth Regime",
    fear_greed: "Fear & Greed",
  };

  const action = String(decision.action ?? "wait");
  const headline =
    action === "spot_long"
      ? {
        title: `${signal.asset} favors spot accumulation`,
        summary: "Institutional flow is supportive, but the setup is cleaner for spot than for leverage.",
      }
      : action === "perps_long"
        ? {
          title: `${signal.asset} favors leveraged upside`,
          summary: "Directional components are aligned enough to support a trend-following perps long.",
        }
        : action === "perps_short"
          ? {
            title: `${signal.asset} favors downside continuation`,
            summary: "Bearish components are aligned enough to justify a trend-following perps short.",
          }
          : {
            title: `${signal.asset} remains in wait mode`,
            summary: "The engine sees useful information, but not enough clean alignment for action.",
          };

  return {
    asset: signal.asset,
    updated_at: utcNowIso(),
    headline,
    component_cards: signalComponents.map(componentStory),
    decision_summary: {
      action: decision.action,
      market_bias: decision.market_bias,
      conviction: decision.conviction,
      setup: decision.setup,
      position_size_bucket: decision.position_size_bucket,
      summary: Array.isArray(decision.why) ? decision.why.join(" | ") : "",
    },
    evidence: {
      total_score: signal.total_score,
      overall_signal: signal.overall_signal,
      supporting_components: bullish.map((name) => titleMap[name] ?? name),
      opposing_components: bearish.map((name) => titleMap[name] ?? name),
      raw_data_used: {
        etf: components.etf_trend?.details,
        positioning: components.positioning?.details,
        price: components.price_confirmation?.details,
        funding: components.funding_rates?.details,
        open_interest: components.futures_open_interest?.details,
        depth: components.depth_asymmetry?.details,
        breadth: components.breadth_regime?.details,
        fear_greed: components.fear_greed?.details,
      },
      calculation_notes: {
        etf: "ETF trend uses the latest flow and the recent 5-period aggregate.",
        positioning: "Positioning compares the latest long-short ratio with 1.0 and its recent sample average.",
        price: "Price confirmation uses the latest close, daily return, and short moving averages from recent daily candles.",
        funding: "Funding compares the latest print with an extreme threshold and with the recent funding average.",
        open_interest: "Open interest compares recent aggregate futures interest with price direction for leverage confirmation.",
        depth: "Depth asymmetry uses turnover-weighted pair depth to compare downside support against upside resistance.",
        breadth: "Breadth compares the asset sector and relevant SoSoValue indices to determine whether the move is broad or narrow.",
        fear_greed: "Fear & greed is used as a light sentiment filter at emotional extremes.",
      },
    },
    why: decision.why,
    invalidations: decision.invalidations,
  };
}

export function buildEnrichedOutput(output: { signal: Record<string, unknown>; decision: Record<string, unknown> }) {
  return {
    snapshot: snapshotMetadata(output.signal),
    ...output,
  };
}

