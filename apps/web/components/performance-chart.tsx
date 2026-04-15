"use client"

import { useEffect, useState } from "react"
import { TrendingUp } from "lucide-react"
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { apiGet } from "@/lib/api"
import { glassPanelHover } from "@/lib/cn-utils"

type EquityPoint = {
  date: string
  total_equity: number
}

type MetricsResponse = {
  equity_curve: EquityPoint[]
  drawdown: { date: string; drawdown: number }[]
  summary: {
    start_equity: number
    end_equity: number
    max_drawdown: number
    cagr?: number
    sharpe?: number
  }
}

export function PerformanceChart() {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiGet("/metrics")
      .then(setMetrics)
      .catch((err) => {
        console.error("Metrics load failed:", err)
        setError("Failed to load performance metrics")
      })
  }, [])

  if (error) {
    return (
      <div className={`${glassPanelHover()} p-6 rounded-2xl text-red-400`}>
        {error}
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className={`${glassPanelHover()} p-6 rounded-2xl`}>
        Loading performance…
      </div>
    )
  }

  /**
   * Recharts expects flat objects.
   * We map API equity_curve → chart-friendly shape.
   */
  const chartData = metrics.equity_curve.map((p) => ({
    date: p.date,
    value: p.total_equity,
  }))

  return (
    <div className={`${glassPanelHover()} h-full p-6 rounded-2xl`}>
      {/* ---------------- HEADER ---------------- */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-chart-2" />
          Portfolio Performance
        </h3>

        <div className="flex flex-col text-right gap-1">
          <div className="text-2xl font-bold font-mono text-chart-2">
            {metrics.summary.end_equity.toFixed(2)}
          </div>
          <div className="text-xs text-muted-foreground font-mono">
            Max DD {(metrics.summary.max_drawdown * 100).toFixed(2)}%
          </div>
        </div>
      </div>

      {/* ---------------- CHART ---------------- */}
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgb(34,197,94)" stopOpacity={0.35} />
              <stop offset="100%" stopColor="rgb(34,197,94)" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(255,255,255,0.05)"
          />

          <XAxis
            dataKey="date"
            hide
          />

          <YAxis
            domain={["auto", "auto"]}
            stroke="rgba(255,255,255,0.3)"
            style={{ fontSize: "11px", fontFamily: "monospace" }}
          />

          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(8,8,8,0.95)",
              border: "1px solid rgba(34,197,94,0.25)",
              borderRadius: "8px",
              fontSize: "12px",
              fontFamily: "monospace",
            }}
            formatter={(value: number) => value.toFixed(2)}
          />

          <Area
            type="monotone"
            dataKey="value"
            stroke="rgb(34,197,94)"
            strokeWidth={2}
            fill="url(#equityGradient)"
            dot={false}
            animationDuration={800}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
