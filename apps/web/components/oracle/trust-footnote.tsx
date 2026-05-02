import Link from "next/link"
import { ArrowUpRight } from "lucide-react"

import type { BacktestReport } from "@/lib/oracle/types"
import { formatRatio2, formatRatio3, formatSharpe } from "@/lib/oracle/format"

interface TrustFootnoteProps {
  readonly report: BacktestReport
}

export function TrustFootnote({ report }: TrustFootnoteProps) {
  const m = report.metrics
  return (
    <section
      id="trust"
      className="relative px-6 py-20 md:py-28 border-t border-border/40"
      aria-labelledby="oracle-trust-title"
    >
      <div className="container mx-auto max-w-3xl">
        <div className="text-[11px] font-mono tracking-[0.3em] uppercase text-primary mb-4">
          What these numbers mean
        </div>
        <h2
          id="oracle-trust-title"
          className="text-2xl md:text-4xl font-semibold tracking-[-0.02em] mb-6"
        >
          Read the credibility contract.
        </h2>
        <div className="space-y-5 text-base md:text-lg text-muted-foreground leading-relaxed">
          <p>
            A raw Sharpe of{" "}
            <span className="text-foreground tabular-nums">
              {formatSharpe(m.sharpe)}
            </span>{" "}
            on its own is not a claim. The number that matters is the{" "}
            <span className="text-primary">Deflated Sharpe P-value</span> —
            the probability that the true Sharpe is positive after correcting
            for selection bias across <span className="tabular-nums">{m.dsr_n_trials}</span>{" "}
            candidate configs and the non-normality of returns
            (skew{" "}
            <span className="tabular-nums">{formatRatio2(m.return_skew)}</span>,
            kurtosis{" "}
            <span className="tabular-nums">{formatRatio2(m.return_kurtosis)}</span>).
            For this run that probability is{" "}
            <span className="text-primary tabular-nums">
              {formatRatio3(m.deflated_sharpe_p)}
            </span>
            .
          </p>
          <p>
            This is a momentum baseline — the null hypothesis any ML pipeline
            in this repo has to beat. It is what a 6-month price trend, equal-
            weighted across the top 25 names and rebalanced monthly with 5 bps
            transaction cost, actually returned on real S&amp;P 500 daily closes.
            Walk-forward, no peeking. The full credibility contract — what is
            and is not used, how each mechanism prevents a specific way numbers
            get inflated — is in <code className="font-mono text-primary">TRUST.md</code>.
          </p>
        </div>
        <div className="mt-10 flex flex-wrap gap-3">
          <Link
            href="https://github.com/ShAuRyA-Noodle/Shaurya-Stocks/blob/main/TRUST.md"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-full border border-primary/40 px-5 py-3 text-sm font-mono uppercase tracking-[0.2em] text-primary hover:bg-primary/10 transition-colors"
          >
            Read TRUST.md
            <ArrowUpRight className="w-4 h-4" />
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-full border border-border/60 px-5 py-3 text-sm font-mono uppercase tracking-[0.2em] text-muted-foreground hover:text-foreground hover:border-foreground/40 transition-colors"
          >
            Back to home
          </Link>
        </div>
      </div>
    </section>
  )
}
