import { buildUrl, fetchJson } from "./http.ts";

export class SoSoValueClient {
  constructor(private apiKey: string) {}

  private get headers() {
    return { "x-soso-api-key": this.apiKey };
  }

  async getEtfHistoricalInflow(etfType: string) {
    const payload = await fetchJson<{ data?: unknown }>(
      "https://api.sosovalue.xyz/openapi/v2/etf/historicalInflowChart",
      {
        method: "POST",
        headers: {
          ...this.headers,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ type: etfType }),
      },
    );
    return Array.isArray(payload.data) ? payload.data as Record<string, unknown>[] : [];
  }

  async getCurrentEtfMetrics(etfType: string) {
    const payload = await fetchJson<{ data?: unknown }>(
      "https://api.sosovalue.xyz/openapi/v2/etf/currentEtfDataMetrics",
      {
        method: "POST",
        headers: {
          ...this.headers,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ type: etfType }),
      },
    );
    return typeof payload.data === "object" && payload.data ? payload.data as Record<string, unknown> : {};
  }

  async getAnalysisChart(chartName: string, limit = 5) {
    const payload = await fetchJson<{ data?: unknown }>(
      buildUrl(`https://api.sosovalue.xyz/openapi/v1/analyses/${chartName}`, { limit }),
      { headers: this.headers },
    );
    return Array.isArray(payload.data) ? payload.data as Record<string, unknown>[] : [];
  }

  async getCurrencyPairs(currencyId: string, pageSize = 5) {
    const payload = await fetchJson<{ data?: unknown }>(
      buildUrl(`https://api.sosovalue.xyz/openapi/v1/currencies/${currencyId}/pairs`, { page_size: pageSize }),
      { headers: this.headers },
    );
    if (typeof payload.data === "object" && payload.data && Array.isArray((payload.data as Record<string, unknown>).list)) {
      return (payload.data as Record<string, unknown>).list as Record<string, unknown>[];
    }
    return [];
  }

  async getCurrencyKlines(currencyId: string, interval = "1d", limit = 5) {
    const payload = await fetchJson<{ data?: unknown }>(
      buildUrl(`https://api.sosovalue.xyz/openapi/v1/currencies/${currencyId}/klines`, { interval, limit }),
      { headers: this.headers },
    );
    return Array.isArray(payload.data) ? payload.data as Record<string, unknown>[] : [];
  }

  async getSectorSpotlight() {
    const payload = await fetchJson<{ data?: unknown }>(
      "https://api.sosovalue.xyz/openapi/v1/currencies/sector-spotlight",
      { headers: this.headers },
    );
    return typeof payload.data === "object" && payload.data ? payload.data as Record<string, unknown> : {};
  }

  async getIndexMarketSnapshot(ticker: string) {
    const payload = await fetchJson<{ data?: unknown }>(
      `https://api.sosovalue.xyz/openapi/v1/indices/${ticker}/market-snapshot`,
      { headers: this.headers },
    );
    return typeof payload.data === "object" && payload.data ? payload.data as Record<string, unknown> : {};
  }
}

export class BinanceMarketClient {
  async getGlobalLongShortRatio(symbol: string, period = "1d", limit = 5) {
    return await fetchJson<Record<string, unknown>[]>(
      buildUrl("https://fapi.binance.com/futures/data/globalLongShortAccountRatio", {
        symbol,
        period,
        limit,
      }),
    );
  }

  async getFundingRates(symbol: string, limit = 5) {
    return await fetchJson<Record<string, unknown>[]>(
      buildUrl("https://fapi.binance.com/fapi/v1/fundingRate", { symbol, limit }),
    );
  }

  async getOpenInterestHist(symbol: string, period = "5m", limit = 48) {
    return await fetchJson<Record<string, unknown>[]>(
      buildUrl("https://fapi.binance.com/futures/data/openInterestHist", {
        symbol,
        period,
        limit,
        contractType: "PERPETUAL",
      }),
    );
  }
}

export class SoDEXMarketClient {
  async getPerpsKlines(symbol: string, interval = "1d", limit = 5) {
    const payload = await fetchJson<{ data?: unknown }>(
      buildUrl(`https://mainnet-gw.sodex.dev/api/v1/perps/markets/${symbol}/klines`, {
        interval,
        limit,
      }),
    );
    return Array.isArray(payload.data) ? payload.data as Record<string, unknown>[] : [];
  }
}

