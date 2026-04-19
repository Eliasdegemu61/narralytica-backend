type ComponentPreview = {
  name: string;
  state: "bullish" | "bearish" | "neutral";
  score: number;
  visualScore: number;
  summary: string;
};

type StoryPreview = {
  headline: string;
  summary: string;
  signalState: "bullish" | "bearish" | "neutral";
  totalScore: number;
  decision: {
    action: string;
    conviction: string;
    marketBias: string;
  };
  components: ComponentPreview[];
};

export const mockDashboard = {
  latestRunLabel: "April 19, 2026 / 8-metric engine",
  engineModes: [
    { name: "DE4 Archive", active: false },
    { name: "DE8 Current", active: true },
    { name: "AI Layer Later", active: false },
  ],
  featuredStories: [
    {
      headline: "ETH leans constructive, but the engine still prefers patience.",
      summary:
        "The design direction assumes users should see the engine's posture immediately: constructive bias, supportive depth, but not enough clean confirmation to escalate from observation into confident action.",
      signalState: "bullish",
      totalScore: 7,
      decision: {
        action: "wait",
        conviction: "low",
        marketBias: "long",
      },
      components: [
        { name: "ETF Trend", state: "bullish", score: 3, visualScore: 94, summary: "Institutional demand still acts like the anchor beneath the thesis." },
        { name: "Positioning", state: "bullish", score: 2, visualScore: 82, summary: "Crowd direction remains supportive, but not enough to overrule weak structure." },
        { name: "Funding", state: "bullish", score: 2, visualScore: 84, summary: "Leverage pressure is not yet overcrowded against longs." },
        { name: "Futures OI", state: "bearish", score: -2, visualScore: 18, summary: "Open interest is still the main spoiler, showing leverage building into weak price." },
      ],
    } satisfies StoryPreview,
  ],
  assets: {
    BTC: {
      title: "Quiet strength, blocked by leverage stress",
      signalState: "bullish",
      totalScore: 5,
      summary: "BTC keeps a constructive backbone from ETF and depth, but the action remains restrained.",
      decision: {
        action: "wait",
        marketBias: "long",
      },
      rawPreview: {
        asset: "BTC",
        overall_signal: "bullish",
        total_score: 5,
        action: "wait",
        conviction: "low",
      },
    },
    ETH: {
      title: "More supportive than BTC, still not released",
      signalState: "bullish",
      totalScore: 7,
      summary: "ETH looks stronger on paper, but the dashboard should still make caution feel visible.",
      decision: {
        action: "wait",
        marketBias: "long",
      },
      rawPreview: {
        asset: "ETH",
        overall_signal: "bullish",
        total_score: 7,
        action: "wait",
        conviction: "low",
      },
    },
  },
  timeline: [
    {
      engine: "DE4",
      timestamp: "2026-04-18 21:40",
      note: "First archived snapshot from the earlier 4-metric engine.",
    },
    {
      engine: "DE4",
      timestamp: "2026-04-19 19:31",
      note: "Last design-era DE4 reference point before the engine expanded.",
    },
    {
      engine: "DE8",
      timestamp: "2026-04-19 20:32",
      note: "First 8-metric run with the new structural overlays.",
    },
    {
      engine: "DE8",
      timestamp: "2026-04-19 21:05",
      note: "Latest DE8 reference run used for tomorrow's assessment trail.",
    },
  ],
  contractIdeas: [
    {
      field: "headline.title",
      label: "Need a strong top line",
      reason: "The hero should not have to derive a headline from low-level state every time.",
    },
    {
      field: "decision_summary.summary",
      label: "Compact explainer text",
      reason: "Useful for cards, mobile modules, and Telegram later without extra AI help.",
    },
    {
      field: "component_cards[].visual_score",
      label: "UI-ready meters",
      reason: "Lets the frontend render confidence bars without baking in scoring math.",
    },
    {
      field: "evidence.total_score",
      label: "Keep the raw number visible",
      reason: "The dashboard should expose conviction mechanically, not hide it in prose.",
    },
  ],
  futureLayers: [
    {
      title: "Comparison view",
      copy: "Side-by-side snapshots for DE4 vs DE8, then later yesterday vs today with outcome grading.",
    },
    {
      title: "Interpretation drawer",
      copy: "Reserved for the later AI layer, but visually planned now so the contract can support it cleanly.",
    },
    {
      title: "Domain-ready shell",
      copy: "A branded container that can go live early even while the engine continues proving itself.",
    },
  ],
};
