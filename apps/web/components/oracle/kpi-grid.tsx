"use client"

import { useEffect, useRef } from "react"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

import {
  formatPercent,
  formatRatio2,
  formatRatio3,
  formatSharpe,
  formatTurnover,
} from "@/lib/oracle/format"
import type { BacktestReport } from "@/lib/oracle/types"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

interface KpiGridProps {
  readonly report: BacktestReport
}

interface Kpi {
  readonly label: string
  readonly value: string
  readonly note: string
}

function buildKpis(report: BacktestReport): readonly Kpi[] {
  const m = report.metrics
  const wf = report.walk_forward
  return [
    {
      label: "Sharpe",
      value: formatSharpe(m.sharpe),
      note: "Annualized · raw, before deflation",
    },
    {
      label: "Annualized return",
      value: formatPercent(m.annualized_return),
      note: `Total ${formatPercent(m.total_return)} over the window`,
    },
    {
      label: "Annualized vol",
      value: formatPercent(m.annualized_vol),
      note: "σ of monthly returns, annualized",
    },
    {
      label: "Max drawdown",
      value: formatPercent(m.max_drawdown),
      note: "Peak-to-trough on equity curve",
    },
    {
      label: "Turnover",
      value: formatTurnover(m.turnover),
      note: `${formatRatio2(m.turnover)} portfolio rotations · ${wf.cost_bps.toFixed(0)} bps cost applied`,
    },
    {
      label: "Deflated Sharpe P",
      value: formatRatio3(m.deflated_sharpe_p),
      note: `n_trials=${m.dsr_n_trials} · σ_SR=${m.dsr_sharpes_std.toFixed(2)}`,
    },
    {
      label: "Skew",
      value: formatRatio2(m.return_skew),
      note: "Of monthly returns",
    },
    {
      label: "Kurtosis",
      value: formatRatio2(m.return_kurtosis),
      note: "Excess · monthly returns",
    },
  ]
}

export function KpiGrid({ report }: KpiGridProps) {
  const rootRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const root = rootRef.current
    if (!root || reduced) return

    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".oracle-kpi",
        { y: 32, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.7,
          ease: "power3.out",
          stagger: 0.06,
          scrollTrigger: { trigger: root, start: "top 80%" },
        },
      )
    }, root)

    return () => ctx.revert()
  }, [])

  const kpis = buildKpis(report)

  return (
    <section
      ref={rootRef}
      id="kpis"
      className="relative px-6 py-20 md:py-28 border-t border-border/40"
      aria-labelledby="oracle-kpis-title"
    >
      <div className="container mx-auto max-w-7xl">
        <div className="flex items-end justify-between flex-wrap gap-6 mb-12">
          <div>
            <div className="text-[11px] font-mono tracking-[0.3em] uppercase text-primary mb-3">
              Headline metrics
            </div>
            <h2
              id="oracle-kpis-title"
              className="text-3xl md:text-5xl font-semibold tracking-[-0.02em]"
            >
              The numbers, eight of them.
            </h2>
          </div>
          <p className="text-sm text-muted-foreground max-w-sm">
            All figures computed from the equity curve below. No selection,
            no smoothing. Source:{" "}
            <code className="font-mono text-primary">report.json</code>.
          </p>
        </div>

        <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          {kpis.map((k) => (
            <div
              key={k.label}
              className="oracle-kpi group rounded-2xl border border-border/60 bg-card/40 backdrop-blur-xl p-5 md:p-6 transition-colors hover:border-primary/50"
            >
              <dt className="text-[10px] md:text-[11px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
                {k.label}
              </dt>
              <dd className="mt-3 text-3xl md:text-4xl font-semibold tracking-[-0.025em] text-primary tabular-nums">
                {k.value}
              </dd>
              <p className="mt-3 text-[11px] md:text-xs font-mono text-muted-foreground/80 leading-relaxed">
                {k.note}
              </p>
            </div>
          ))}
        </dl>
      </div>
    </section>
  )
}
