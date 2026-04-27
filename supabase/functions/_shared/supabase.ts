export class SupabasePublisher {
  constructor(
    private baseUrl: string,
    private serviceRoleKey: string,
  ) {}

  private get headers() {
    return {
      apikey: this.serviceRoleKey,
      Authorization: `Bearer ${this.serviceRoleKey}`,
      "Content-Type": "application/json",
      Prefer: "return=minimal,resolution=merge-duplicates",
    };
  }

  private async request(
    path: string,
    {
      method = "GET",
      params,
      body,
    }: {
      method?: string;
      params?: Record<string, string>;
      body?: unknown;
    } = {},
  ) {
    const url = new URL(`${this.baseUrl.replace(/\/$/, "")}/rest/v1/${path.replace(/^\//, "")}`);
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        url.searchParams.set(key, value);
      }
    }

    const response = await fetch(url.toString(), {
      method,
      headers: this.headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`Supabase ${response.status}: ${text || response.statusText}`);
    }
  }

  async insertDecisionRun({
    asset,
    output,
    story,
  }: {
    asset: string;
    output: Record<string, unknown>;
    story: Record<string, unknown>;
  }) {
    const signal = output.signal as Record<string, unknown>;
    const decision = output.decision as Record<string, unknown>;
    const snapshot = output.snapshot as Record<string, unknown>;
    await this.request("decision_runs", {
      method: "POST",
      body: {
        asset: asset.toLowerCase(),
        snapshot_time_utc: snapshot.snapshot_time_utc,
        reference_price: snapshot.reference_price,
        reference_price_date: snapshot.reference_price_date,
        price_source: snapshot.price_source,
        overall_signal: signal.overall_signal,
        total_score: signal.total_score,
        action: decision.action,
        market_bias: decision.market_bias,
        conviction: decision.conviction,
        position_size_bucket: decision.position_size_bucket,
        signal_output: output,
        signal_story: story,
      },
    });
  }

  async upsertLatestAssetState({
    asset,
    output,
    story,
  }: {
    asset: string;
    output: Record<string, unknown>;
    story: Record<string, unknown>;
  }) {
    const signal = output.signal as Record<string, unknown>;
    const decision = output.decision as Record<string, unknown>;
    const snapshot = output.snapshot as Record<string, unknown>;
    await this.request("latest_asset_state", {
      method: "POST",
      params: { on_conflict: "asset" },
      body: {
        asset: asset.toLowerCase(),
        snapshot_time_utc: snapshot.snapshot_time_utc,
        reference_price: snapshot.reference_price,
        reference_price_date: snapshot.reference_price_date,
        price_source: snapshot.price_source,
        overall_signal: signal.overall_signal,
        total_score: signal.total_score,
        action: decision.action,
        market_bias: decision.market_bias,
        conviction: decision.conviction,
        position_size_bucket: decision.position_size_bucket,
        signal_output: output,
        signal_story: story,
        updated_at: snapshot.snapshot_time_utc,
      },
    });
  }

  async upsertSiteCache({
    cacheKey,
    payload,
    source,
    refreshIntervalMinutes,
  }: {
    cacheKey: string;
    payload: Record<string, unknown>;
    source: string;
    refreshIntervalMinutes: number;
  }) {
    await this.request("site_cache", {
      method: "POST",
      params: { on_conflict: "cache_key" },
      body: {
        cache_key: cacheKey,
        payload,
        source,
        refresh_interval_minutes: refreshIntervalMinutes,
        updated_at: payload.updated_at,
      },
    });
  }
}

