import { mockDashboard } from "@/lib/mock-dashboard";

function formatNumber(value: number): string {
  if (Math.abs(value) >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (Math.abs(value) >= 1_000) return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function stateClass(state: string): string {
  if (state === "bullish") return "stateBullish";
  if (state === "bearish") return "stateBearish";
  return "stateNeutral";
}

export default function HomePage() {
  const featured = mockDashboard.featuredStories[0];

  return (
    <main className="pageShell">
      <section className="hero">
        <div className="heroKicker">Narralytica / Design Lab</div>
        <div className="heroGrid">
          <div className="heroCopy">
            <h1>Signals first. Interpretation later.</h1>
            <p>
              This design-only dashboard is built to feel like a live decision surface even before we wire the backend.
              The raw engine remains the source of truth; the frontend just learns how to present it compactly, clearly,
              and with enough drama to feel worth opening every day.
            </p>
            <div className="heroChips">
              {mockDashboard.engineModes.map((mode) => (
                <span key={mode.name} className={`chip ${mode.active ? "chipActive" : ""}`}>
                  {mode.name}
                </span>
              ))}
            </div>
          </div>
          <div className="heroPanel">
            <div className="panelLabel">Current Preview</div>
            <div className="heroStatRow">
              <div>
                <span className="statCaption">Latest run</span>
                <strong>{mockDashboard.latestRunLabel}</strong>
              </div>
              <div>
                <span className="statCaption">Domain status</span>
                <strong>Designing</strong>
              </div>
            </div>
            <div className="heroStatRow">
              <div>
                <span className="statCaption">BTC action</span>
                <strong>{mockDashboard.assets.BTC.decision.action}</strong>
              </div>
              <div>
                <span className="statCaption">ETH action</span>
                <strong>{mockDashboard.assets.ETH.decision.action}</strong>
              </div>
            </div>
            <p className="heroPanelNote">
              The UI currently uses local mock data shaped like the website JSON. Later we can swap the source layer without
              rebuilding the visual system.
            </p>
          </div>
        </div>
      </section>

      <section className="contentGrid">
        <div className="leftRail">
          <section className="card cardFeature">
            <div className="cardHeader">
              <span className="sectionEyebrow">Featured Story</span>
              <span className={`pill ${stateClass(featured.signalState)}`}>{featured.signalState}</span>
            </div>
            <h2>{featured.headline}</h2>
            <p className="mutedLead">{featured.summary}</p>
            <div className="featureStats">
              <div className="miniStat">
                <span>Total score</span>
                <strong>{featured.totalScore}</strong>
              </div>
              <div className="miniStat">
                <span>Conviction</span>
                <strong>{featured.decision.conviction}</strong>
              </div>
              <div className="miniStat">
                <span>Action</span>
                <strong>{featured.decision.action}</strong>
              </div>
            </div>
            <div className="componentList">
              {featured.components.map((component) => (
                <article key={component.name} className="componentItem">
                  <div className="componentTop">
                    <h3>{component.name}</h3>
                    <span className={`pill ${stateClass(component.state)}`}>
                      {component.state} · {component.score}
                    </span>
                  </div>
                  <div className="meterTrack">
                    <div className="meterFill" style={{ width: `${component.visualScore}%` }} />
                  </div>
                  <p>{component.summary}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="cardHeader">
              <span className="sectionEyebrow">Snapshot Timeline</span>
            </div>
            <div className="timeline">
              {mockDashboard.timeline.map((item) => (
                <article key={`${item.engine}-${item.timestamp}`} className="timelineItem">
                  <div className="timelineTop">
                    <strong>{item.timestamp}</strong>
                    <span className="timelineEngine">{item.engine}</span>
                  </div>
                  <p>{item.note}</p>
                </article>
              ))}
            </div>
          </section>
        </div>

        <div className="rightRail">
          <section className="card">
            <div className="cardHeader">
              <span className="sectionEyebrow">Asset Dashboard</span>
            </div>
            <div className="assetGrid">
              {Object.entries(mockDashboard.assets).map(([asset, panel]) => (
                <article key={asset} className="assetCard">
                  <div className="assetTop">
                    <div>
                      <span className="assetTicker">{asset}</span>
                      <h3>{panel.title}</h3>
                    </div>
                    <span className={`pill ${stateClass(panel.signalState)}`}>{panel.signalState}</span>
                  </div>
                  <p className="assetSummary">{panel.summary}</p>
                  <div className="assetStats">
                    <div>
                      <span>Bias</span>
                      <strong>{panel.decision.marketBias}</strong>
                    </div>
                    <div>
                      <span>Action</span>
                      <strong>{panel.decision.action}</strong>
                    </div>
                    <div>
                      <span>Score</span>
                      <strong>{panel.totalScore}</strong>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="cardHeader">
              <span className="sectionEyebrow">JSON Contract Ideas</span>
            </div>
            <div className="contractList">
              {mockDashboard.contractIdeas.map((idea) => (
                <div key={idea.label} className="contractRow">
                  <div>
                    <strong>{idea.label}</strong>
                    <p>{idea.reason}</p>
                  </div>
                  <code>{idea.field}</code>
                </div>
              ))}
            </div>
          </section>

          <section className="card">
            <div className="cardHeader">
              <span className="sectionEyebrow">Future Layers</span>
            </div>
            <div className="futureStack">
              {mockDashboard.futureLayers.map((item) => (
                <article key={item.title} className="futureItem">
                  <h3>{item.title}</h3>
                  <p>{item.copy}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="card cardConsole">
            <div className="cardHeader">
              <span className="sectionEyebrow">Raw Output Taste Test</span>
            </div>
            <pre>{JSON.stringify(mockDashboard.assets.BTC.rawPreview, null, 2)}</pre>
          </section>
        </div>
      </section>

      <section className="footerBand">
        <div>
          <span className="sectionEyebrow">Deployment</span>
          <h2>Built to ship on Vercel when you’re ready.</h2>
        </div>
        <div className="footerStats">
          <div>
            <span>Framework</span>
            <strong>Next.js</strong>
          </div>
          <div>
            <span>Mode</span>
            <strong>Design only</strong>
          </div>
          <div>
            <span>Data source</span>
            <strong>Local mock JSON</strong>
          </div>
          <div>
            <span>Next step</span>
            <strong>Wire contract later</strong>
          </div>
        </div>
      </section>
    </main>
  );
}
