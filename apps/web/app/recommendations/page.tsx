import type { Metadata } from "next"
import { Brain, TrendingUp, TrendingDown, Minus, Activity, AlertTriangle } from "lucide-react"

import { loadLlmArtifacts } from "@/lib/oracle/load-llm-artifacts"
import { loadStaticSignals } from "@/lib/oracle/load-artifacts"

export const dynamic = "force-static"

export const metadata: Metadata = {
  title: "Recommendations — ORACLE",
  description:
    "Daily LLM + ML signals. Sentiment, catalysts, macro regime, and AI-generated briefing.",
}

const REGIME_TONE: Record<string, { color: string; label: string }> = {
  risk_on: { color: "text-[#8AC926] border-[#8AC926]/40 bg-[#8AC926]/10", label: "RISK ON" },
  risk_off: { color: "text-[#FF595E] border-[#FF595E]/40 bg-[#FF595E]/10", label: "RISK OFF" },
  neutral: { color: "text-[#FFCA3A] border-[#FFCA3A]/40 bg-[#FFCA3A]/10", label: "NEUTRAL" },
}

const SEVERITY_TONE: Record<string, string> = {
  high: "text-[#FF595E]",
  medium: "text-[#FFCA3A]",
  low: "text-muted-foreground",
}

export default function RecommendationsPage() {
  const { regime, briefing, catalysts, sentiment } = loadLlmArtifacts()
  const signals = loadStaticSignals().slice(0, 12)

  const regimeKey = regime?.regime ?? "neutral"
  const regimeTone = REGIME_TONE[regimeKey] ?? REGIME_TONE.neutral

  // Top catalysts (non-none, sorted by severity)
  const sevRank = { high: 3, medium: 2, low: 1 }
  const topCatalysts = [...catalysts]
    .filter((c) => c.catalyst_type !== "none")
    .sort((a, b) => (sevRank[b.severity] ?? 0) - (sevRank[a.severity] ?? 0))
    .slice(0, 10)

  // Top sentiment shifts (sorted by |mean|)
  const topSentiment = [...sentiment]
    .sort((a, b) => Math.abs(b.sentiment_mean) - Math.abs(a.sentiment_mean))
    .slice(0, 8)

  return (
    <main id="oracle-recommendations" className="relative">
      {/* ── HEADER ──────────────────────────────────────────────────────── */}
      <section className="relative px-6 py-20 md:py-28">
        <div className="container mx-auto max-w-6xl">
          <div className="flex items-center gap-3 mb-3">
            <div className="text-[11px] font-mono tracking-[0.3em] uppercase text-primary">
              Daily AI briefing
            </div>
            {regime && regimeTone && (
              <span
                className={`text-[10px] font-mono tracking-[0.15em] uppercase border rounded px-2 py-0.5 ${regimeTone.color}`}
              >
                {regimeTone.label}
              </span>
            )}
          </div>
          <h1 className="text-4xl md:text-6xl font-semibold tracking-[-0.025em] mb-6">
            {briefing?.headline || "Today's signals."}
          </h1>
          {briefing?.narrative ? (
            <p className="text-base md:text-lg text-muted-foreground max-w-3xl leading-relaxed">
              {briefing.narrative}
            </p>
          ) : (
            <p className="text-base md:text-lg text-muted-foreground max-w-3xl leading-relaxed">
              Briefing not generated yet. The daily 5-layer LLM pipeline runs after market close
              (21:30 UTC). Once the cron has been enabled, this page shows: macro regime,
              sentiment-driven names, catalyst-tagged events, and a narrative summary.
            </p>
          )}
          {briefing && (
            <div className="mt-6 flex flex-wrap gap-2 text-[10px] font-mono uppercase tracking-[0.15em] text-muted-foreground/60">
              <span className="border border-border/50 rounded px-2 py-0.5">
                Date · {briefing.date}
              </span>
              <span className="border border-border/50 rounded px-2 py-0.5">
                Model · {briefing.model}
              </span>
              <span className="border border-border/50 rounded px-2 py-0.5">
                {briefing.n_picks} picks
              </span>
            </div>
          )}
        </div>
      </section>

      {/* ── MACRO REGIME ────────────────────────────────────────────────── */}
      {regime && (
        <section className="relative px-6 py-12 border-t border-border/40">
          <div className="container mx-auto max-w-6xl">
            <div className="flex items-center gap-2 mb-6">
              <Activity className="w-4 h-4 text-primary" />
              <h2 className="text-xs font-mono tracking-[0.3em] uppercase text-primary">
                Macro regime · Layer 3
              </h2>
            </div>
            <div className="rounded-2xl border border-border/60 bg-card/40 backdrop-blur-xl p-6 md:p-8">
              <div className="flex flex-wrap items-baseline justify-between gap-4 mb-4">
                <span className={`text-3xl md:text-5xl font-semibold ${regimeTone.color.split(" ")[0]}`}>
                  {regimeTone.label}
                </span>
                <span className="text-sm font-mono text-muted-foreground tabular-nums">
                  conviction {(regime.confidence * 100).toFixed(0)}% · n={regime.n_headlines} headlines
                </span>
              </div>
              <p className="text-base text-muted-foreground leading-relaxed">{regime.rationale}</p>
            </div>
          </div>
        </section>
      )}

      {/* ── ML SIGNALS (top picks) ──────────────────────────────────────── */}
      <section className="relative px-6 py-12 border-t border-border/40">
        <div className="container mx-auto max-w-6xl">
          <div className="flex items-center gap-2 mb-6">
            <Brain className="w-4 h-4 text-primary" />
            <h2 className="text-xs font-mono tracking-[0.3em] uppercase text-primary">
              ML model picks · LightGBM 2026
            </h2>
          </div>
          {signals.length === 0 ? (
            <div className="rounded-2xl border border-border/40 bg-card/20 p-10 text-center text-sm font-mono text-muted-foreground">
              No predictions yet — run <code className="text-primary">quant ml predict</code> to populate.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {signals.slice(0, 8).map((s, i) => {
                const dir = s.direction
                const DirIcon = dir === "long" ? TrendingUp : dir === "short" ? TrendingDown : Minus
                const tone =
                  dir === "long" ? "text-[#8AC926]" : dir === "short" ? "text-[#FF595E]" : "text-muted-foreground"
                return (
                  <article
                    key={`${s.symbol}-${i}`}
                    className="rounded-2xl border border-border/60 bg-card/40 backdrop-blur-xl p-5 hover:border-primary/50 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="text-xs font-mono text-muted-foreground">
                        #{s.rank_in_universe}
                      </div>
                      <div className={`flex items-center gap-1 text-xs font-mono ${tone}`}>
                        <DirIcon className="w-3.5 h-3.5" />
                        {dir === "long" ? "BUY" : dir === "short" ? "SELL" : "HOLD"}
                      </div>
                    </div>
                    <div className="text-2xl font-semibold tracking-[-0.02em]">{s.symbol}</div>
                    <div className="text-[10px] font-mono text-muted-foreground/60 mt-1">
                      score {s.score >= 0 ? "+" : ""}{s.score.toFixed(3)}
                    </div>
                    <div className="mt-4 h-1 rounded-full bg-border overflow-hidden">
                      <div
                        className={`h-full transition-all duration-700 ${
                          dir === "long" ? "bg-[#8AC926]" : dir === "short" ? "bg-[#FF595E]" : "bg-primary"
                        }`}
                        style={{ width: `${Math.min(100, s.confidence * 100)}%` }}
                      />
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </div>
      </section>

      {/* ── CATALYSTS (Layer 2) ─────────────────────────────────────────── */}
      {topCatalysts.length > 0 && (
        <section className="relative px-6 py-12 border-t border-border/40">
          <div className="container mx-auto max-w-6xl">
            <div className="flex items-center gap-2 mb-6">
              <AlertTriangle className="w-4 h-4 text-primary" />
              <h2 className="text-xs font-mono tracking-[0.3em] uppercase text-primary">
                Catalyst tags · Layer 2
              </h2>
            </div>
            <div className="rounded-2xl border border-border/60 bg-card/30 backdrop-blur-xl divide-y divide-border/40">
              {topCatalysts.map((c, i) => (
                <div
                  key={`${c.symbol}-${c.date}-${i}`}
                  className="flex items-start justify-between gap-4 p-4 md:p-5"
                >
                  <div className="flex items-baseline gap-3 min-w-0">
                    <span className="text-lg font-semibold tracking-[-0.02em] text-foreground shrink-0">
                      {c.symbol}
                    </span>
                    <span className="text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground/60 shrink-0">
                      {c.catalyst_type.replace(/_/g, " ")}
                    </span>
                    <span className="text-sm text-muted-foreground truncate">{c.summary}</span>
                  </div>
                  <span
                    className={`text-[10px] font-mono uppercase tracking-[0.18em] shrink-0 ${SEVERITY_TONE[c.severity] ?? ""}`}
                  >
                    {c.severity}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── SENTIMENT (Layer 1) ─────────────────────────────────────────── */}
      {topSentiment.length > 0 && (
        <section className="relative px-6 py-12 border-t border-border/40">
          <div className="container mx-auto max-w-6xl">
            <div className="flex items-center gap-2 mb-6">
              <TrendingUp className="w-4 h-4 text-primary" />
              <h2 className="text-xs font-mono tracking-[0.3em] uppercase text-primary">
                News sentiment · Layer 1
              </h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {topSentiment.map((s, i) => {
                const positive = s.sentiment_mean > 0
                const tone = positive ? "text-[#8AC926]" : "text-[#FF595E]"
                return (
                  <div
                    key={`${s.symbol}-${s.date}-${i}`}
                    className="rounded-xl border border-border/60 bg-card/30 backdrop-blur-xl p-4"
                  >
                    <div className="flex items-baseline justify-between">
                      <span className="text-lg font-semibold tracking-[-0.02em]">{s.symbol}</span>
                      <span className={`text-sm font-mono tabular-nums ${tone}`}>
                        {s.sentiment_mean >= 0 ? "+" : ""}{s.sentiment_mean.toFixed(2)}
                      </span>
                    </div>
                    <div className="mt-1 text-[10px] font-mono text-muted-foreground/60">
                      n={s.sentiment_count} · {s.date}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </section>
      )}

      {/* ── FOOTER ──────────────────────────────────────────────────────── */}
      <section className="relative px-6 py-20 border-t border-border/40">
        <div className="container mx-auto max-w-6xl">
          <p className="text-xs font-mono text-muted-foreground/60 tracking-[0.15em] uppercase leading-relaxed">
            Generated by 5-layer LLM pipeline: DeepSeek V4 Flash (sentiment) + Kimi K2.5 (catalysts,
            regime, sanity, briefing). Refreshed daily at 21:30 UTC by GitHub Actions cron. All
            data from real Alpaca + news APIs. No synthetic paths.
          </p>
        </div>
      </section>
    </main>
  )
}
