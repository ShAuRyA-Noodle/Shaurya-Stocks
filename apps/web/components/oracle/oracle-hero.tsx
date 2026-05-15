"use client"

import { useEffect, useRef } from "react"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"
import SplitType from "split-type"

import {
  formatPercent,
  formatRatio3,
  formatSharpe,
  formatYear,
} from "@/lib/oracle/format"
import type { BacktestReport } from "@/lib/oracle/types"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

interface OracleHeroProps {
  readonly report: BacktestReport
}

export function OracleHero({ report }: OracleHeroProps) {
  const rootRef = useRef<HTMLElement>(null)
  const headlineRef = useRef<HTMLHeadingElement>(null)
  const subRef = useRef<HTMLParagraphElement>(null)

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const root = rootRef.current
    const headline = headlineRef.current
    const sub = subRef.current
    if (!root || !headline || !sub) return

    const split = new SplitType(headline, { types: "chars,words", tagName: "span" })

    const ctx = gsap.context(() => {
      if (reduced) {
        gsap.set(split.chars, { yPercent: 0, opacity: 1 })
        return
      }
      gsap.set(split.chars, { yPercent: 110, opacity: 0 })
      gsap.set(sub, { y: 24, opacity: 0 })

      const tl = gsap.timeline({ defaults: { ease: "expo.out" } })
      tl.to(split.chars, {
        yPercent: 0,
        opacity: 1,
        duration: 1.0,
        stagger: 0.022,
      })
      tl.to(sub, { y: 0, opacity: 1, duration: 0.8 }, "-=0.5")
      tl.from(
        ".oracle-hero-stat",
        { y: 18, opacity: 0, duration: 0.6, stagger: 0.08 },
        "-=0.4",
      )
      tl.from(".oracle-hero-tag", { y: -12, opacity: 0, duration: 0.5 }, 0.05)
    }, root)

    return () => {
      ctx.revert()
      split.revert()
    }
  }, [])

  const startYear = formatYear(report.window.start)
  const endYear = formatYear(report.window.end)
  const sharpeText = formatSharpe(report.metrics.sharpe)
  const dsrText = formatRatio3(report.metrics.deflated_sharpe_p)
  const annRetText = formatPercent(report.metrics.annualized_return)

  return (
    <section
      ref={rootRef}
      className="relative pt-36 pb-24 px-6 overflow-hidden isolate"
      aria-labelledby="oracle-hero-title"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(55% 45% at 50% 30%, rgba(25,130,196,0.22) 0%, rgba(25,130,196,0.05) 45%, transparent 75%)",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.06]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(25,130,196,0.35) 1px, transparent 1px), linear-gradient(90deg, rgba(25,130,196,0.35) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
          maskImage:
            "radial-gradient(70% 60% at 50% 30%, #000 0%, transparent 80%)",
        }}
      />

      <div className="container mx-auto max-w-6xl">
        <div className="oracle-hero-tag inline-flex items-center gap-2 rounded-full border border-primary/40 bg-primary/5 px-4 py-1.5 mb-10">
          <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-primary">
            <span className="absolute inset-0 rounded-full bg-primary animate-ping opacity-70" />
          </span>
          <span className="text-[11px] font-mono tracking-[0.3em] uppercase text-primary">
            Verified backtest · {report.name}
          </span>
        </div>

        <h1
          id="oracle-hero-title"
          ref={headlineRef}
          className="text-[clamp(2.4rem,8vw,6.5rem)] font-semibold tracking-[-0.03em] leading-[0.95] text-foreground will-change-transform"
        >
          S&amp;P 500 momentum,
          <br />
          <span className="text-primary">walk-forward verified.</span>
        </h1>

        <p
          ref={subRef}
          className="mt-8 max-w-2xl text-base md:text-lg text-muted-foreground leading-relaxed"
        >
          Real daily closes from the S&amp;P 500 universe, {startYear}→{endYear}. A
          126-day momentum signal, rebalanced monthly, top-25 equal-weighted, with
          5 bps round-trip cost. Walk-forward — no in-sample tuning leaks into the
          equity curve below.
        </p>

        <dl className="mt-14 grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-4">
          <HeroStat label="Sharpe" value={sharpeText} />
          <HeroStat label="Deflated Sharpe P" value={dsrText} />
          <HeroStat label="Annualized return" value={annRetText} />
          <HeroStat
            label="Window"
            value={`${startYear}→${endYear}`}
            mono
          />
        </dl>
      </div>
    </section>
  )
}

interface HeroStatProps {
  readonly label: string
  readonly value: string
  readonly mono?: boolean
}

function HeroStat({ label, value, mono = false }: HeroStatProps) {
  return (
    <div className="oracle-hero-stat rounded-xl border border-border/60 bg-card/40 px-4 py-4 md:px-5 md:py-5 backdrop-blur-xl">
      <dt className="text-[10px] md:text-[11px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
        {label}
      </dt>
      <dd
        className={`mt-2 text-2xl md:text-3xl font-semibold tracking-[-0.02em] text-primary tabular-nums ${
          mono ? "font-mono text-xl md:text-2xl" : ""
        }`}
      >
        {value}
      </dd>
    </div>
  )
}
