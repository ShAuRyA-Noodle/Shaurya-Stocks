"use client"

import { useEffect, useState } from "react"
import { Activity } from "lucide-react"
import { glassPanelHover, neonGlowGreen, neonGlowRed } from "@/lib/cn-utils"
import { apiGet } from "@/lib/api"

export function VolatilityMeter() {
  const [volatility, setVolatility] = useState<number | null>(null)

  useEffect(() => {
    let cancelled = false
    const fetchVix = async () => {
      try {
        const res = await apiGet("/macro/latest?series=VIXCLS")
        if (!cancelled && typeof res?.value === "number") setVolatility(res.value)
      } catch { /* keep last known */ }
    }
    fetchVix()
    const interval = setInterval(fetchVix, 60_000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  const v = volatility ?? 0
  const getColor = () => {
    if (volatility == null) return "text-muted-foreground"
    if (v < 35) return "text-chart-2"
    if (v < 60) return "text-chart-4"
    return "text-chart-3"
  }

  const getGlow = () => {
    if (volatility == null || v >= 35 && v < 60) return ""
    if (v < 35) return neonGlowGreen()
    return neonGlowRed()
  }

  return (
    <div className={`${glassPanelHover()} ${getGlow()} h-full p-6 rounded-2xl`}>
      <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
        <Activity className="w-5 h-5 text-chart-4" />
        Market Volatility
      </h3>
      <div className="flex flex-col items-center justify-center py-4">
        <div className={`text-6xl font-bold font-mono tabular-nums mb-2 ${getColor()}`}>
          {volatility == null ? "—" : volatility.toFixed(1)}
        </div>
        <div className="text-muted-foreground font-mono text-sm">VIX Index</div>
        {/* Circular progress */}
        <div className="relative mt-6 w-32 h-32">
          <svg className="w-full h-full -rotate-90">
            <circle cx="64" cy="64" r="56" stroke="currentColor" strokeWidth="8" fill="none" className="text-border" />
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${(v / 100) * 351.86} 351.86`}
              className={`${getColor()} transition-all duration-500`}
              strokeLinecap="round"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-xs font-mono text-muted-foreground">
              {volatility == null ? "—" : v < 35 ? "LOW" : v < 60 ? "MODERATE" : "HIGH"}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
