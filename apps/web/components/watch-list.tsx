"use client"

import { Star, TrendingUp, TrendingDown } from "lucide-react"
import { glassPanel, glassPanelHover } from "@/lib/cn-utils"

export function WatchList() {
  const stocks = [
    { symbol: "AAPL", price: "178.24", change: "+2.3%", positive: true },
    { symbol: "TSLA", price: "242.67", change: "-1.8%", positive: false },
    { symbol: "NVDA", price: "489.32", change: "+5.2%", positive: true },
    { symbol: "MSFT", price: "378.91", change: "+0.9%", positive: true },
    { symbol: "AMZN", price: "148.23", change: "-0.4%", positive: false },
  ]

  return (
    <div className={`${glassPanelHover()} h-full p-6 rounded-2xl`}>
      <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
        <Star className="w-5 h-5 text-chart-4 fill-chart-4" />
        Watchlist
      </h3>
      <div className="space-y-3">
        {stocks.map((stock) => (
          <button
            key={stock.symbol}
            className={`w-full ${glassPanel()} p-3 rounded-lg hover:border-primary/40 transition-all group`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div
                  className={`w-8 h-8 rounded-md flex items-center justify-center ${
                    stock.positive ? "bg-chart-2/10" : "bg-chart-3/10"
                  }`}
                >
                  {stock.positive ? (
                    <TrendingUp className="w-4 h-4 text-chart-2" />
                  ) : (
                    <TrendingDown className="w-4 h-4 text-chart-3" />
                  )}
                </div>
                <div>
                  <div className="font-mono font-bold text-sm text-left">{stock.symbol}</div>
                  <div className="text-xs text-muted-foreground font-mono">${stock.price}</div>
                </div>
              </div>
              <div className={`font-mono text-sm font-semibold ${stock.positive ? "text-chart-2" : "text-chart-3"}`}>
                {stock.change}
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
