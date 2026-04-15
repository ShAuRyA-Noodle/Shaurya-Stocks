"use client"

import { useEffect, useState } from "react"
import {
  ArrowUpRight,
  ArrowDownRight,
  ChevronRight,
  TrendingUp,
} from "lucide-react"

import { apiGet } from "@/lib/api"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { SignalDetailView } from "@/components/signal-detail-view"
import { glassPanel, glassPanelHover } from "@/lib/cn-utils"

/* -----------------------------
   UI SIGNAL SHAPE (UNCHANGED)
-------------------------------- */
interface Signal {
  id: string
  symbol: string
  type: "BUY" | "SELL" | "HOLD"
  confidence: number
  entry: number
  target: number
  stopLoss: number
  timeframe: string
  features: {
    rsi: number
    macd: number
    sentiment: number
    volume: number
  }
}

/* -----------------------------
   API SIGNAL SHAPE
-------------------------------- */
interface ApiSignal {
  symbol: string
  date: string
  signal: "BUY" | "SELL" | "HOLD"
  confidence: number
  run_timestamp?: string
}

/* -----------------------------
   MAIN COMPONENT
-------------------------------- */
export function SignalCards() {
  const [signals, setSignals] = useState<Signal[]>([])
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiGet("/signals")
      .then((res) => {
        const apiSignals: ApiSignal[] = res.signals ?? []

        /* -----------------------------------------
           KEEP ONLY LATEST SIGNAL PER SYMBOL
        ------------------------------------------ */
        const latestBySymbol = new Map<string, ApiSignal>()

        apiSignals.forEach((s) => {
          const existing = latestBySymbol.get(s.symbol)

          const currentTs = s.run_timestamp
            ? new Date(s.run_timestamp).getTime()
            : 0

          const existingTs = existing?.run_timestamp
            ? new Date(existing.run_timestamp).getTime()
            : 0

          if (!existing || currentTs > existingTs) {
            latestBySymbol.set(s.symbol, s)
          }
        })

        /* -----------------------------------------
           MAP → UI SHAPE (PRICES INTENTIONAL PLACEHOLDERS)
        ------------------------------------------ */
        const mapped: Signal[] = Array.from(latestBySymbol.values()).map(
          (s, idx) => ({
            id: `${s.symbol}-${s.date}-${idx}`,
            symbol: s.symbol,
            type: s.signal,
            confidence: s.confidence * 100,
            entry: 0,
            target: 0,
            stopLoss: 0,
            timeframe: "1D",
            features: {
              rsi: 0,
              macd: 0,
              sentiment: 0,
              volume: 0,
            },
          })
        )

        setSignals(mapped)
      })
      .catch((err) => {
        console.error("Failed to load signals:", err)
        setError("Unable to load signals")
      })
  }, [])

  if (error) {
    return (
      <div className={`${glassPanel()} p-6 rounded-2xl text-red-400`}>
        {error}
      </div>
    )
  }

  return (
    <>
      {/* ---------------- HEADER ---------------- */}
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-2xl font-bold flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-primary" />
            Active Signals
          </h3>

          <div className={`${glassPanel()} px-3 py-1 rounded-full`}>
            <span className="text-xs font-mono text-muted-foreground">
              {signals.length} <span className="text-primary">LIVE</span>
            </span>
          </div>
        </div>

        {/* ---------------- GRID ---------------- */}
        {signals.length === 0 ? (
          <div className={`${glassPanel()} p-6 rounded-2xl text-muted-foreground`}>
            No signals available today
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {signals.map((signal, index) => (
              <SignalCard
                key={signal.id}
                signal={signal}
                delay={index * 100}
                onClick={() => setSelectedSignal(signal)}
              />
            ))}
          </div>
        )}
      </div>

      {/* ---------------- DETAIL MODAL ---------------- */}
      <Dialog open={!!selectedSignal} onOpenChange={() => setSelectedSignal(null)}>
        <DialogContent
          className={`${glassPanel()} border-primary/20 max-w-3xl`}
          aria-describedby="signal-details"
        >
          <DialogHeader>
            <DialogTitle className="text-2xl font-bold font-mono">
              {selectedSignal?.symbol} Signal Analysis
            </DialogTitle>
          </DialogHeader>
          {selectedSignal && <SignalDetailView signal={selectedSignal} />}
        </DialogContent>
      </Dialog>
    </>
  )
}

/* -----------------------------
   SIGNAL CARD (UNCHANGED UI)
-------------------------------- */
function SignalCard({
  signal,
  delay,
  onClick,
}: {
  signal: Signal
  delay: number
  onClick: () => void
}) {
  const isBuy = signal.type === "BUY"
  const borderColor = isBuy ? "border-chart-2/50" : "border-chart-3/50"
  const hoverGlowClass = isBuy
    ? "hover:shadow-[0_0_10px_rgba(57,255,20,0.3),0_0_20px_rgba(57,255,20,0.2)]"
    : "hover:shadow-[0_0_10px_rgba(255,0,60,0.3),0_0_20px_rgba(255,0,60,0.2)]"
  const bgGradient = isBuy
    ? "bg-linear-to-br from-chart-2/5 to-transparent"
    : "bg-linear-to-br from-chart-3/5 to-transparent"

  return (
    <button
      onClick={onClick}
      className={`${glassPanelHover()} ${hoverGlowClass} relative overflow-hidden rounded-2xl p-6 text-left border-2 ${borderColor} transition-all duration-300`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className={`absolute inset-0 ${bgGradient} opacity-50`} />

      <div className="relative z-10">
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="text-2xl font-bold font-mono mb-1">
              {signal.symbol}
            </div>
            <div className="text-xs font-mono text-muted-foreground">
              {signal.timeframe}
            </div>
          </div>

          <div
            className={`px-3 py-1 rounded-full font-mono font-semibold text-sm flex items-center gap-1 ${
              isBuy
                ? "bg-chart-2/20 text-chart-2"
                : "bg-chart-3/20 text-chart-3"
            }`}
          >
            {isBuy ? (
              <ArrowUpRight className="w-4 h-4" />
            ) : (
              <ArrowDownRight className="w-4 h-4" />
            )}
            {signal.type}
          </div>
        </div>

        <div className="mb-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-muted-foreground">
              AI Confidence
            </span>
            <span className="text-lg font-bold font-mono text-primary">
              {signal.confidence.toFixed(1)}%
            </span>
          </div>

          <div className="w-full h-1.5 bg-border/30 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary rounded-full transition-all duration-700"
              style={{ width: `${signal.confidence}%` }}
            />
          </div>
        </div>

        <div className="pt-3 border-t border-border/30 flex items-center justify-between">
          <span className="text-xs font-mono font-semibold uppercase">
            View Analysis
          </span>
          <ChevronRight className="w-4 h-4" />
        </div>
      </div>
    </button>
  )
}