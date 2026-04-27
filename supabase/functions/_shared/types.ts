export type ComponentState = "bullish" | "bearish" | "neutral" | "unavailable";
export type Action = "wait" | "spot_long" | "perps_long" | "perps_short";
export type MarketBias = "long" | "short" | "neutral";
export type Conviction = "low" | "medium" | "high";

export interface SignalComponent {
  name: string;
  score: number;
  label: ComponentState;
  details: Record<string, unknown>;
}

