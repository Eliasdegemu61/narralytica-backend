import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

import { BinanceMarketClient, SoDEXMarketClient, SoSoValueClient } from "../_shared/clients.ts";
import { decideFromSignal } from "../_shared/decision-engine.ts";
import { buildQuickTradeInputPayload, BTC_ETH_QUICK_TRADE_CONFIG } from "../_shared/quick-trade.ts";
import { buildEnrichedOutput, buildSignalStory } from "../_shared/result-writer.ts";
import { buildAssetSignalSnapshot, ASSET_CONFIG } from "../_shared/signal-engine.ts";
import { buildEngineSummaryCache, buildMarketOverviewCache } from "../_shared/site-payloads.ts";
import { SupabasePublisher } from "../_shared/supabase.ts";

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body, null, 2), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function requiredEnv(name: string) {
  const value = Deno.env.get(name);
  if (!value) throw new Error(`Missing required env var: ${name}`);
  return value;
}

function optionalEnv(name: string) {
  return Deno.env.get(name) ?? "";
}

async function safeAnalysisChartRows(
  soso: SoSoValueClient,
  chartName: string | null | undefined,
  limit = 5,
) {
  if (!chartName) return null;
  try {
    const rows = await soso.getAnalysisChart(chartName, limit);
    return rows.length ? rows : null;
  } catch (error) {
    console.warn(`[warn] SoSoValue chart unavailable for ${chartName}: ${String(error)}`);
    return null;
  }
}

async function safeCurrencyKlines(
  soso: SoSoValueClient,
  asset: string,
  currencyId: string | null,
) {
  if (!currencyId) return null;
  try {
    const rows = await soso.getCurrencyKlines(currencyId, "1d", 5);
    if (rows.length < 5) return null;
    return [...rows]
      .sort((a, b) => Number(a.timestamp ?? 0) - Number(b.timestamp ?? 0))
      .map((row) => ({
        t: row.timestamp,
        o: row.open,
        c: row.close,
        source: "soso_currency_klines",
      }));
  } catch (error) {
    console.warn(`[warn] SoSoValue price unavailable for ${asset}: ${String(error)}`);
    return null;
  }
}

async function safePairRows(
  soso: SoSoValueClient,
  asset: string,
  currencyId: string | null,
) {
  if (!currencyId) return null;
  try {
    const rows = await soso.getCurrencyPairs(currencyId, 5);
    return rows.length ? rows : null;
  } catch (error) {
    console.warn(`[warn] SoSoValue pair depth unavailable for ${asset}: ${String(error)}`);
    return null;
  }
}

async function safeIndexSnapshots(
  soso: SoSoValueClient,
  asset: string,
  indexTickers: string[],
) {
  const snapshots: Record<string, Record<string, unknown>> = {};
  for (const ticker of indexTickers) {
    try {
      snapshots[ticker] = await soso.getIndexMarketSnapshot(ticker);
    } catch (error) {
      console.warn(`[warn] SoSoValue index snapshot unavailable for ${asset} / ${ticker}: ${String(error)}`);
    }
  }
  return snapshots;
}

function buildPositioningRows(chartRows: Record<string, unknown>[] | null) {
  if (!chartRows?.length) return null;
  return [...chartRows]
    .sort((a, b) => Number(a.timestamp ?? 0) - Number(b.timestamp ?? 0))
    .map((row) => {
      const ratio = Number(row["long/short_ratio"] ?? 1);
      const denominator = ratio + 1;
      return {
        longShortRatio: ratio,
        longAccount: ratio / denominator,
        shortAccount: 1 / denominator,
        timestamp: row.timestamp,
      };
    });
}

function buildFundingRows(chartRows: Record<string, unknown>[] | null) {
  if (!chartRows?.length) return null;
  return [...chartRows]
    .sort((a, b) => Number(a.timestamp ?? 0) - Number(b.timestamp ?? 0))
    .map((row) => ({
      fundingRate: row.binance ?? 0,
      fundingTime: row.timestamp,
      markPrice: row.btc_price ?? 0,
    }));
}

async function runCoreSignals(publisher: SupabasePublisher, soso: SoSoValueClient) {
  const stepStartedAt = new Date().toISOString();
  const errors: Array<Record<string, string>> = [];

  const sectorPayload = await soso.getSectorSpotlight();
  const fearGreedRows = (await safeAnalysisChartRows(soso, "fgi_indicator", 5)) ?? [];
  const futuresOpenInterestRows = (await safeAnalysisChartRows(soso, "futures_open_interest", 5)) ?? [];

  const etfMetrics: Record<string, Record<string, unknown>> = {};
  for (const [asset, config] of Object.entries(ASSET_CONFIG)) {
    const etfType = String(config.etf_type ?? "");
    if (!etfType) continue;
    try {
      etfMetrics[asset.toLowerCase()] = await soso.getCurrentEtfMetrics(etfType);
    } catch (error) {
      console.warn(`[warn] SoSoValue ETF metrics unavailable for ${asset}: ${String(error)}`);
      errors.push({ asset: asset.toLowerCase(), step: "etf_metrics", error: String(error) });
    }
  }

  const outputs: Record<string, { signal: Record<string, unknown>; decision: Record<string, unknown> }> = {};
  const stories: Record<string, Record<string, unknown>> = {};
  const enrichedOutputs: Record<string, Record<string, unknown>> = {};

  for (const [asset, config] of Object.entries(ASSET_CONFIG)) {
    try {
      const currencyId = config.currency_id ? String(config.currency_id) : null;
      const indexSnapshots = await safeIndexSnapshots(
        soso,
        asset,
        Array.isArray(config.index_tickers) ? config.index_tickers.map(String) : [],
      );
      const positioningRows = buildPositioningRows(
        await safeAnalysisChartRows(soso, config.positioning_chart ? String(config.positioning_chart) : null, 5),
      );
      const fundingRows = buildFundingRows(
        await safeAnalysisChartRows(soso, config.funding_chart ? String(config.funding_chart) : null, 5),
      );

      const signal = buildAssetSignalSnapshot(asset, {
        etfRows: config.etf_type ? await soso.getEtfHistoricalInflow(String(config.etf_type)) : null,
        positioningRows,
        klines: await safeCurrencyKlines(soso, asset, currencyId),
        fundingRows,
        fearGreedRows,
        futuresOpenInterestRows: config.has_futures_open_interest ? futuresOpenInterestRows : null,
        pairRows: await safePairRows(soso, asset, currencyId),
        sectorPayload,
        indexSnapshots,
      });
      const decision = decideFromSignal(signal);
      const assetKey = asset.toLowerCase();
      const output = { signal, decision };
      const story = buildSignalStory(signal, decision);
      const enriched = buildEnrichedOutput(output);

      outputs[assetKey] = output;
      stories[assetKey] = story;
      enrichedOutputs[assetKey] = enriched;
    } catch (error) {
      console.warn(`[warn] Core signal build failed for ${asset}: ${String(error)}`);
      errors.push({ asset: asset.toLowerCase(), step: "build_signal", error: String(error) });
    }
  }

  for (const [asset, enrichedOutput] of Object.entries(enrichedOutputs)) {
    try {
      await publisher.insertDecisionRun({
        asset,
        output: enrichedOutput,
        story: stories[asset],
      });
    } catch (error) {
      console.warn(`[warn] Supabase decision_runs insert failed for ${asset}: ${String(error)}`);
      errors.push({ asset, step: "decision_runs", error: String(error) });
    }

    try {
      await publisher.upsertLatestAssetState({
        asset,
        output: enrichedOutput,
        story: stories[asset],
      });
    } catch (error) {
      console.warn(`[warn] Supabase latest_asset_state upsert failed for ${asset}: ${String(error)}`);
      errors.push({ asset, step: "latest_asset_state", error: String(error) });
    }
  }

  const siteCache = {
    engine_summary: buildEngineSummaryCache(outputs),
    market_overview: buildMarketOverviewCache({
      fearGreedRows,
      futuresOpenInterestRows,
      sectorPayload,
      etfMetrics,
    }),
  };

  try {
    await publisher.upsertSiteCache({
      cacheKey: "engine_summary",
      payload: siteCache.engine_summary,
      source: "decision_engine",
      refreshIntervalMinutes: 15,
    });
  } catch (error) {
    console.warn(`[warn] Supabase site_cache upsert failed for engine_summary: ${String(error)}`);
    errors.push({ asset: "all", step: "engine_summary", error: String(error) });
  }

  try {
    await publisher.upsertSiteCache({
      cacheKey: "market_overview",
      payload: siteCache.market_overview,
      source: "decision_engine",
      refreshIntervalMinutes: 15,
    });
  } catch (error) {
    console.warn(`[warn] Supabase site_cache upsert failed for market_overview: ${String(error)}`);
    errors.push({ asset: "all", step: "market_overview", error: String(error) });
  }

  return {
    started_at: stepStartedAt,
    finished_at: new Date().toISOString(),
    asset_count: Object.keys(enrichedOutputs).length,
    cache_keys: ["engine_summary", "market_overview"],
    errors,
  };
}

async function safePerpsKlines(
  sodex: SoDEXMarketClient,
  asset: string,
  symbol: string,
  interval: string,
  limit: number,
) {
  try {
    return await sodex.getPerpsKlines(symbol, interval, limit);
  } catch (error) {
    console.warn(`[warn] SoDEX ${interval} klines unavailable for ${asset}: ${String(error)}`);
    return [];
  }
}

async function safeLongShortRatio(
  binance: BinanceMarketClient,
  asset: string,
  symbol: string,
  period = "1h",
  limit = 24,
) {
  try {
    return await binance.getGlobalLongShortRatio(symbol, period, limit);
  } catch (error) {
    console.warn(`[warn] Binance long/short ratio unavailable for ${asset}: ${String(error)}`);
    return [];
  }
}

async function safeFundingRates(
  binance: BinanceMarketClient,
  asset: string,
  symbol: string,
  limit = 24,
) {
  try {
    return await binance.getFundingRates(symbol, limit);
  } catch (error) {
    console.warn(`[warn] Binance funding unavailable for ${asset}: ${String(error)}`);
    return [];
  }
}

async function safeOpenInterest(
  binance: BinanceMarketClient,
  asset: string,
  symbol: string,
  period = "5m",
  limit = 48,
) {
  try {
    return await binance.getOpenInterestHist(symbol, period, limit);
  } catch (error) {
    console.warn(`[warn] Binance open interest unavailable for ${asset}: ${String(error)}`);
    return [];
  }
}

async function runQuickTradeSnapshots(
  publisher: SupabasePublisher,
  sodex: SoDEXMarketClient,
  binance: BinanceMarketClient,
) {
  const stepStartedAt = new Date().toISOString();
  const errors: Array<Record<string, string>> = [];
  const cacheKeys: string[] = [];

  for (const [asset, config] of Object.entries(BTC_ETH_QUICK_TRADE_CONFIG)) {
    try {
      const payload = buildQuickTradeInputPayload({
        asset,
        symbol: config.symbol,
        sodexSymbol: config.sodex_symbol,
        klines5m: await safePerpsKlines(sodex, asset, config.sodex_symbol, "5m", 288),
        klines15m: await safePerpsKlines(sodex, asset, config.sodex_symbol, "15m", 192),
        klines1h: await safePerpsKlines(sodex, asset, config.sodex_symbol, "1h", 168),
        fundingRows: await safeFundingRates(binance, asset, config.symbol, 24),
        longShortRows: await safeLongShortRatio(binance, asset, config.symbol, "1h", 24),
        openInterestRows: await safeOpenInterest(binance, asset, config.symbol, "5m", 48),
      });

      const cacheKey = `quick_trade_inputs_${asset.toLowerCase()}`;
      await publisher.upsertSiteCache({
        cacheKey,
        payload,
        source: "quick_trade_engine",
        refreshIntervalMinutes: 15,
      });
      cacheKeys.push(cacheKey);
    } catch (error) {
      console.warn(`[warn] Quick trade snapshot failed for ${asset}: ${String(error)}`);
      errors.push({ asset: asset.toLowerCase(), step: "quick_trade_site_cache", error: String(error) });
    }
  }

  return {
    started_at: stepStartedAt,
    finished_at: new Date().toISOString(),
    asset_count: cacheKeys.length,
    cache_keys: cacheKeys,
    errors,
  };
}

serve(async (request) => {
  try {
    const configuredSecret = optionalEnv("RUN_ENGINES_SECRET");
    if (configuredSecret) {
      const providedSecret = request.headers.get("x-run-engines-secret");
      if (providedSecret !== configuredSecret) {
        return jsonResponse({ error: "Unauthorized" }, 401);
      }
    }

    if (request.method !== "POST" && request.method !== "GET") {
      return jsonResponse({ error: "Method not allowed" }, 405);
    }

    const publisher = new SupabasePublisher(
      requiredEnv("SUPABASE_URL"),
      requiredEnv("SUPABASE_SERVICE_ROLE_KEY"),
    );

    const soso = new SoSoValueClient(requiredEnv("SOSO_API_KEY"));
    const sodex = new SoDEXMarketClient();
    const binance = new BinanceMarketClient();

    let core = {
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      asset_count: 0,
      cache_keys: [] as string[],
      errors: [] as Array<Record<string, string>>,
    };
    try {
      core = await runCoreSignals(publisher, soso);
    } catch (error) {
      core = {
        started_at: new Date().toISOString(),
        finished_at: new Date().toISOString(),
        asset_count: 0,
        cache_keys: [],
        errors: [{ asset: "all", step: "core_signals", error: String(error) }],
      };
    }

    let quickTrade = {
      started_at: new Date().toISOString(),
      finished_at: new Date().toISOString(),
      asset_count: 0,
      cache_keys: [] as string[],
      errors: [] as Array<Record<string, string>>,
    };
    try {
      quickTrade = await runQuickTradeSnapshots(publisher, sodex, binance);
    } catch (error) {
      quickTrade = {
        started_at: new Date().toISOString(),
        finished_at: new Date().toISOString(),
        asset_count: 0,
        cache_keys: [],
        errors: [{ asset: "all", step: "quick_trade_snapshots", error: String(error) }],
      };
    }

    const allErrors = [...core.errors, ...quickTrade.errors];
    return jsonResponse({
      ok: allErrors.length === 0,
      ran_at: new Date().toISOString(),
      order: ["core_signals", "quick_trade_snapshots"],
      core_signals: core,
      quick_trade_snapshots: quickTrade,
      error_count: allErrors.length,
    });
  } catch (error) {
    return jsonResponse(
      {
        ok: false,
        error: String(error),
      },
      500,
    );
  }
});
