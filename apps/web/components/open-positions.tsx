"use client"

import { useEffect, useState } from "react"
import { Target, TrendingUp, DollarSign, Percent, ArrowUpRight, Layers3, AlertCircle, ChevronRight, Activity } from "lucide-react"
import { glassPanel, glassPanelHover } from "@/lib/cn-utils"
import { apiGet } from "@/lib/api"

interface Position {
  symbol: string
  quantity: number
  entry_price: number
  side: "LONG"
}

export function OpenPositions() {
  const [positions, setPositions] = useState<Position[]>([])
  const [mockCurrentPrices, setMockCurrentPrices] = useState<Record<string, number>>({})
  const [totalValue, setTotalValue] = useState(0)
  const [totalPnL, setTotalPnL] = useState(0)

  useEffect(() => {
    apiGet("/positions").then((res) => {
      const fetchedPositions = res.positions ?? []
      setPositions(fetchedPositions)

      // Mock current prices (in production, fetch real-time prices)
      const prices: Record<string, number> = {}
      let totalVal = 0
      let totalProfit = 0

      fetchedPositions.forEach((p: Position) => {
        const currentPrice = p.entry_price * (1 + (Math.random() - 0.3) * 0.1)
        prices[p.symbol] = currentPrice
        const positionValue = currentPrice * p.quantity
        const pnl = (currentPrice - p.entry_price) * p.quantity
        totalVal += positionValue
        totalProfit += pnl
      })

      setMockCurrentPrices(prices)
      setTotalValue(totalVal)
      setTotalPnL(totalProfit)
    })
  }, [])

  useEffect(() => {
    // Update prices every 2 seconds to simulate live data
    const interval = setInterval(() => {
      setMockCurrentPrices(prev => {
        const updated = { ...prev }
        let totalVal = 0
        let totalProfit = 0

        positions.forEach(p => {
          if (updated[p.symbol]) {
            updated[p.symbol] = updated[p.symbol] * (1 + (Math.random() - 0.5) * 0.005)
            const positionValue = updated[p.symbol] * p.quantity
            const pnl = (updated[p.symbol] - p.entry_price) * p.quantity
            totalVal += positionValue
            totalProfit += pnl
          }
        })

        setTotalValue(totalVal)
        setTotalPnL(totalProfit)

        return updated
      })
    }, 2000)

    return () => clearInterval(interval)
  }, [positions])

  const calculatePnL = (position: Position) => {
    const currentPrice = mockCurrentPrices[position.symbol] || position.entry_price
    return (currentPrice - position.entry_price) * position.quantity
  }

  const calculatePnLPercent = (position: Position) => {
    const currentPrice = mockCurrentPrices[position.symbol] || position.entry_price
    return ((currentPrice - position.entry_price) / position.entry_price) * 100
  }

  return (
    <div className={`${glassPanelHover()} rounded-2xl overflow-hidden flex flex-col h-full`}>
      {/* Header */}
      <div className="p-6 border-b border-border/50 bg-linear-to-br from-background via-card to-background">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Target className="w-5 h-5 text-primary" />
            Active Positions
          </h3>
          <div className="flex items-center gap-3">
            <div className={`${glassPanel()} px-3 py-1.5 rounded-lg flex items-center gap-2`}>
              <div className="relative">
                <Activity className="w-3.5 h-3.5 text-primary" />
                <div className="absolute inset-0 bg-primary rounded-full blur animate-pulse" />
              </div>
              <span className="text-xs font-mono text-primary font-semibold">REAL-TIME</span>
            </div>
          </div>
        </div>

        {/* Portfolio Overview */}
        {positions.length > 0 && (
          <div className="grid grid-cols-3 gap-4">
            <div className={`${glassPanel()} p-4 rounded-xl relative overflow-hidden`}>
              <div className="absolute top-0 right-0 w-24 h-24 bg-primary/10 rounded-full blur-3xl" />
              <div className="relative z-10">
                <div className="flex items-center gap-2 mb-2">
                  <Layers3 className="w-4 h-4 text-primary" />
                  <span className="text-xs text-muted-foreground font-mono font-semibold">OPEN</span>
                </div>
                <div className="text-3xl font-bold font-mono">{positions.length}</div>
                <div className="text-xs text-muted-foreground mt-1">Active contracts</div>
              </div>
            </div>

            <div className={`${glassPanel()} p-4 rounded-xl relative overflow-hidden`}>
              <div className="absolute top-0 right-0 w-24 h-24 bg-chart-2/10 rounded-full blur-3xl" />
              <div className="relative z-10">
                <div className="flex items-center gap-2 mb-2">
                  <DollarSign className="w-4 h-4 text-chart-2" />
                  <span className="text-xs text-muted-foreground font-mono font-semibold">VALUE</span>
                </div>
                <div className="text-3xl font-bold font-mono text-chart-2">
                  ${totalValue.toFixed(0)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">Total exposure</div>
              </div>
            </div>

            <div className={`${glassPanel()} p-4 rounded-xl relative overflow-hidden`}>
              <div className={`absolute top-0 right-0 w-24 h-24 ${totalPnL >= 0 ? 'bg-chart-2/10' : 'bg-red-400/10'} rounded-full blur-3xl`} />
              <div className="relative z-10">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className={`w-4 h-4 ${totalPnL >= 0 ? 'text-chart-2' : 'text-red-400'}`} />
                  <span className="text-xs text-muted-foreground font-mono font-semibold">UNREALIZED</span>
                </div>
                <div className={`text-3xl font-bold font-mono ${totalPnL >= 0 ? 'text-chart-2' : 'text-red-400'}`}>
                  {totalPnL >= 0 ? '+' : ''}{totalPnL.toFixed(2)}
                </div>
                <div className="text-xs text-muted-foreground mt-1">Total P&L</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Positions List */}
      <div className="flex-1 overflow-hidden bg-linear-to-br from-background/50 via-card/30 to-background/50 p-6">
        {positions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full">
            <div className={`${glassPanel()} p-8 rounded-2xl mb-4 relative overflow-hidden`}>
              <div className="absolute inset-0 bg-linear-to-br from-primary/5 to-transparent" />
              <Target className="w-16 h-16 text-muted-foreground/30 relative z-10" />
            </div>
            <div className="text-muted-foreground font-mono text-sm font-semibold mb-1">
              No Active Positions
            </div>
            <div className="text-muted-foreground/50 font-mono text-xs flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5" />
              Awaiting market opportunities...
            </div>
          </div>
        ) : (
          <div className="space-y-3 overflow-auto h-full custom-scrollbar pr-2">
            {positions.map((position, i) => {
              const currentPrice = mockCurrentPrices[position.symbol] || position.entry_price
              const pnl = calculatePnL(position)
              const pnlPercent = calculatePnLPercent(position)
              const isProfit = pnl >= 0

              return (
                <div
                  key={i}
                  className={`${glassPanelHover()} p-5 rounded-xl relative overflow-hidden group transition-all duration-300 hover:scale-[1.02]`}
                >
                  {/* Animated gradient background */}
                  <div className={`absolute inset-0 bg-linear-to-r ${isProfit ? 'from-chart-2/5 to-transparent' : 'from-red-400/5 to-transparent'} opacity-0 group-hover:opacity-100 transition-opacity`} />
                  
                  {/* Glow effect */}
                  <div className={`absolute top-0 right-0 w-32 h-32 ${isProfit ? 'bg-chart-2/10' : 'bg-red-400/10'} rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity`} />

                  <div className="relative z-10">
                    {/* Header Row */}
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className={`${glassPanel()} px-4 py-2 rounded-lg`}>
                          <div className="text-xl font-bold font-mono">{position.symbol}</div>
                        </div>
                        <div className="bg-primary/20 text-primary px-3 py-1 rounded-md text-xs font-mono font-bold flex items-center gap-1.5">
                          <ArrowUpRight className="w-3 h-3" />
                          {position.side}
                        </div>
                      </div>

                      <div className="text-right">
                        <div className={`text-2xl font-bold font-mono ${isProfit ? 'text-chart-2' : 'text-red-400'}`}>
                          {isProfit ? '+' : ''}{pnl.toFixed(2)}
                        </div>
                        <div className={`text-xs font-mono font-semibold ${isProfit ? 'text-chart-2/70' : 'text-red-400/70'}`}>
                          {isProfit ? '+' : ''}{pnlPercent.toFixed(2)}%
                        </div>
                      </div>
                    </div>

                    {/* Stats Grid */}
                    <div className="grid grid-cols-4 gap-3">
                      <div className={`${glassPanel()} p-3 rounded-lg`}>
                        <div className="flex items-center gap-1.5 mb-1">
                          <Layers3 className="w-3 h-3 text-muted-foreground" />
                          <span className="text-[10px] text-muted-foreground font-mono font-semibold">QTY</span>
                        </div>
                        <div className="text-base font-bold font-mono">{position.quantity.toLocaleString()}</div>
                      </div>

                      <div className={`${glassPanel()} p-3 rounded-lg`}>
                        <div className="flex items-center gap-1.5 mb-1">
                          <DollarSign className="w-3 h-3 text-muted-foreground" />
                          <span className="text-[10px] text-muted-foreground font-mono font-semibold">ENTRY</span>
                        </div>
                        <div className="text-base font-bold font-mono">${position.entry_price.toFixed(2)}</div>
                      </div>

                      <div className={`${glassPanel()} p-3 rounded-lg`}>
                        <div className="flex items-center gap-1.5 mb-1">
                          <Activity className="w-3 h-3 text-primary" />
                          <span className="text-[10px] text-muted-foreground font-mono font-semibold">CURRENT</span>
                        </div>
                        <div className="text-base font-bold font-mono text-primary">${currentPrice.toFixed(2)}</div>
                      </div>

                      <div className={`${glassPanel()} p-3 rounded-lg`}>
                        <div className="flex items-center gap-1.5 mb-1">
                          <Percent className="w-3 h-3 text-muted-foreground" />
                          <span className="text-[10px] text-muted-foreground font-mono font-semibold">VALUE</span>
                        </div>
                        <div className="text-base font-bold font-mono">${(currentPrice * position.quantity).toFixed(0)}</div>
                      </div>
                    </div>

                    {/* Progress bar for P&L */}
                    <div className="mt-4">
                      <div className="h-1.5 bg-border/30 rounded-full overflow-hidden">
                        <div
                          className={`h-full transition-all duration-500 ${isProfit ? 'bg-linear-to-r from-chart-2/50 to-chart-2' : 'bg-linear-to-r from-red-400/50 to-red-400'}`}
                          style={{ width: `${Math.min(Math.abs(pnlPercent) * 10, 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Hover indicator */}
                  <div className="absolute right-4 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <ChevronRight className="w-5 h-5 text-primary" />
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 3px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      `}</style>
    </div>
  )
}