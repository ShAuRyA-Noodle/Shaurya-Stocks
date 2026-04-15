"use client"

import { ArrowDown, ArrowUp } from "lucide-react"
import { glassPanelHover } from "@/lib/cn-utils"

export function MarketOverview() {
  const indices = [
    { symbol: "SPY", value: "445.23", change: "+1.24", percent: "+0.28%", positive: true },
    { symbol: "QQQ", value: "378.91", change: "-0.82", percent: "-0.22%", positive: false },
    { symbol: "DIA", value: "348.67", change: "+2.15", percent: "+0.62%", positive: true },
  ]

  return (
    <div className={`${glassPanelHover()} h-full p-6 rounded-2xl`}>
      <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
        <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
        Market Overview
      </h3>
      <div className="space-y-4">
        {indices.map((index) => (
          <div key={index.symbol} className="flex items-center justify-between">
            <div>
              <div className="font-mono font-bold text-foreground">{index.symbol}</div>
              <div className="text-2xl font-bold font-mono tabular-nums">${index.value}</div>
            </div>
            <div className="text-right">
              <div
                className={`flex items-center gap-1 font-mono text-sm ${
                  index.positive ? "text-chart-2" : "text-chart-3"
                }`}
              >
                {index.positive ? <ArrowUp className="w-4 h-4" /> : <ArrowDown className="w-4 h-4" />}
                {index.change}
              </div>
              <div className={`font-mono text-sm ${index.positive ? "text-chart-2" : "text-chart-3"}`}>
                {index.percent}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
