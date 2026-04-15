"use client"

import { useEffect, useState } from "react"
import { TrendingUp, TrendingDown, Activity, Clock, DollarSign, Layers } from "lucide-react"
import { glassPanel, glassPanelHover } from "@/lib/cn-utils"
import { apiGet } from "@/lib/api"

interface Trade {
  timestamp: string
  symbol: string
  side: "BUY" | "SELL"
  quantity: number
  price: number
  realized_pnl: number
}

export function TradesTable() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [stats, setStats] = useState({
    totalPnL: 0,
    winRate: 0,
    totalTrades: 0,
    avgPnL: 0
  })

  useEffect(() => {
    apiGet("/trades").then((res) => {
      const fetchedTrades = res.trades ?? []
      setTrades(fetchedTrades)

      // Calculate stats
      if (fetchedTrades.length > 0) {
        const totalPnL = fetchedTrades.reduce((sum: number, t: Trade) => sum + t.realized_pnl, 0)
        const winningTrades = fetchedTrades.filter((t: Trade) => t.realized_pnl > 0).length
        const winRate = (winningTrades / fetchedTrades.length) * 100
        const avgPnL = totalPnL / fetchedTrades.length

        setStats({
          totalPnL,
          winRate,
          totalTrades: fetchedTrades.length,
          avgPnL
        })
      }
    })
  }, [])

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      second: '2-digit',
      hour12: false 
    })
  }

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric'
    })
  }

  return (
    <div className={`${glassPanelHover()} rounded-2xl overflow-hidden flex flex-col h-full`}>
      {/* Header with Stats */}
      <div className="p-6 border-b border-border/50">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Activity className="w-5 h-5 text-primary" />
            Trade Execution Log
          </h3>
          <div className={`${glassPanel()} px-3 py-1.5 rounded-lg flex items-center gap-2`}>
            <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
            <span className="text-xs font-mono text-primary font-semibold">LIVE</span>
          </div>
        </div>

        {/* Stats Grid */}
        {trades.length > 0 && (
          <div className="grid grid-cols-4 gap-4">
            <div className={`${glassPanel()} p-3 rounded-lg`}>
              <div className="flex items-center gap-2 mb-1">
                <Layers className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-mono">Total Trades</span>
              </div>
              <div className="text-xl font-bold font-mono">{stats.totalTrades}</div>
            </div>

            <div className={`${glassPanel()} p-3 rounded-lg`}>
              <div className="flex items-center gap-2 mb-1">
                <DollarSign className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-mono">Total PnL</span>
              </div>
              <div className={`text-xl font-bold font-mono ${stats.totalPnL >= 0 ? 'text-chart-2' : 'text-red-400'}`}>
                ${stats.totalPnL.toFixed(2)}
              </div>
            </div>

            <div className={`${glassPanel()} p-3 rounded-lg`}>
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-mono">Win Rate</span>
              </div>
              <div className="text-xl font-bold font-mono text-chart-2">{stats.winRate.toFixed(1)}%</div>
            </div>

            <div className={`${glassPanel()} p-3 rounded-lg`}>
              <div className="flex items-center gap-2 mb-1">
                <Activity className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-xs text-muted-foreground font-mono">Avg PnL</span>
              </div>
              <div className={`text-xl font-bold font-mono ${stats.avgPnL >= 0 ? 'text-chart-2' : 'text-red-400'}`}>
                ${stats.avgPnL.toFixed(2)}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Table */}
      <div className="flex-1 overflow-hidden bg-linear-to-br from-background via-card to-background">
        {trades.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full p-8 text-center">
            <div className={`${glassPanel()} p-6 rounded-2xl mb-4`}>
              <Activity className="w-12 h-12 text-muted-foreground/50 mx-auto mb-2" />
            </div>
            <div className="text-muted-foreground font-mono text-sm">No trades executed yet</div>
            <div className="text-muted-foreground/50 font-mono text-xs mt-1">
              Waiting for trading signals...
            </div>
          </div>
        ) : (
          <div className="overflow-auto h-full custom-scrollbar">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-background/80 backdrop-blur-xl border-b border-border/50">
                <tr className="text-muted-foreground font-mono text-xs">
                  <th className="text-left py-4 px-6 font-semibold">
                    <div className="flex items-center gap-2">
                      <Clock className="w-3.5 h-3.5" />
                      TIMESTAMP
                    </div>
                  </th>
                  <th className="text-left py-4 px-4 font-semibold">SYMBOL</th>
                  <th className="text-center py-4 px-4 font-semibold">SIDE</th>
                  <th className="text-right py-4 px-4 font-semibold">QUANTITY</th>
                  <th className="text-right py-4 px-4 font-semibold">PRICE</th>
                  <th className="text-right py-4 px-6 font-semibold">REALIZED PNL</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade, i) => (
                  <tr 
                    key={i} 
                    className={`border-b border-border/30 hover:bg-accent/5 transition-colors group ${glassPanelHover()}`}
                  >
                    <td className="py-4 px-6">
                      <div className="flex flex-col gap-0.5">
                        <span className="font-mono text-xs text-foreground font-semibold">
                          {formatTime(trade.timestamp)}
                        </span>
                        <span className="font-mono text-[10px] text-muted-foreground">
                          {formatDate(trade.timestamp)}
                        </span>
                      </div>
                    </td>
                    <td className="py-4 px-4">
                      <div className={`${glassPanel()} inline-block px-3 py-1.5 rounded-md`}>
                        <span className="font-mono font-bold text-xs">{trade.symbol}</span>
                      </div>
                    </td>
                    <td className="py-4 px-4 text-center">
                      <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-mono text-xs font-bold ${
                        trade.side === "BUY" 
                          ? "bg-chart-2/20 text-chart-2" 
                          : "bg-red-400/20 text-red-400"
                      }`}>
                        {trade.side === "BUY" ? (
                          <TrendingUp className="w-3.5 h-3.5" />
                        ) : (
                          <TrendingDown className="w-3.5 h-3.5" />
                        )}
                        {trade.side}
                      </div>
                    </td>
                    <td className="py-4 px-4 text-right font-mono font-semibold">
                      {trade.quantity.toLocaleString()}
                    </td>
                    <td className="py-4 px-4 text-right font-mono font-semibold">
                      ${trade.price.toFixed(2)}
                    </td>
                    <td className="py-4 px-6 text-right">
                      <div className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-mono text-xs font-bold ${
                        trade.realized_pnl > 0
                          ? "bg-chart-2/20 text-chart-2"
                          : trade.realized_pnl < 0
                          ? "bg-red-400/20 text-red-400"
                          : "bg-muted/20 text-muted-foreground"
                      }`}>
                        {trade.realized_pnl > 0 && <TrendingUp className="w-3.5 h-3.5" />}
                        {trade.realized_pnl < 0 && <TrendingDown className="w-3.5 h-3.5" />}
                        ${Math.abs(trade.realized_pnl).toFixed(2)}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
          height: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      `}</style>
    </div>
  )
}