"use client"

import { BarChart3, Activity, MessageSquare, Volume2 } from "lucide-react"
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { glassPanel } from "@/lib/cn-utils"

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

export function SignalDetailView({ signal }: { signal: Signal }) {
  const featureData = [
    { name: "RSI", value: signal.features.rsi, icon: Activity, color: "rgb(0, 240, 255)" },
    { name: "MACD", value: Math.abs(signal.features.macd) * 50, icon: BarChart3, color: "rgb(57, 255, 20)" },
    { name: "Sentiment", value: signal.features.sentiment * 100, icon: MessageSquare, color: "rgb(255, 165, 0)" },
    { name: "Volume", value: signal.features.volume * 100, icon: Volume2, color: "rgb(255, 0, 60)" },
  ]

  const chartData = featureData.map((f) => ({
    name: f.name,
    value: f.value,
    fill: f.color,
  }))

  return (
    <div className="space-y-6">
      {/* Feature Importance - Waterfall Chart */}
      <div>
        <h4 className="text-sm font-mono font-semibold mb-4 text-muted-foreground uppercase">
          Feature Importance Analysis
        </h4>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData}>
            <XAxis
              dataKey="name"
              stroke="rgba(255,255,255,0.3)"
              style={{ fontSize: "11px", fontFamily: "monospace" }}
            />
            <YAxis stroke="rgba(255,255,255,0.3)" style={{ fontSize: "11px", fontFamily: "monospace" }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(8, 8, 8, 0.95)",
                border: "1px solid rgba(0, 240, 255, 0.2)",
                borderRadius: "8px",
                fontSize: "12px",
                fontFamily: "monospace",
              }}
            />
            <Bar dataKey="value" radius={[8, 8, 0, 0]} animationDuration={1000} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Feature Grid */}
      <div className="grid grid-cols-2 gap-4">
        {featureData.map((feature) => (
          <div key={feature.name} className={`${glassPanel()} p-4 rounded-xl`}>
            <div className="flex items-center gap-2 mb-3">
              <feature.icon className="w-4 h-4" style={{ color: feature.color }} />
              <span className="text-sm font-mono font-semibold">{feature.name}</span>
            </div>
            <div className="text-2xl font-bold font-mono" style={{ color: feature.color }}>
              {feature.value.toFixed(1)}
            </div>
          </div>
        ))}
      </div>

      {/* Risk/Reward */}
      <div className={`${glassPanel()} p-6 rounded-xl`}>
        <h4 className="text-sm font-mono font-semibold mb-4 text-muted-foreground uppercase">Risk/Reward Profile</h4>
        <div className="space-y-3 font-mono">
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Potential Gain</span>
            <span className="text-lg font-bold text-chart-2">
              ${Math.abs(signal.target - signal.entry).toFixed(2)} (
              {(((signal.target - signal.entry) / signal.entry) * 100).toFixed(1)}%)
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-muted-foreground">Potential Loss</span>
            <span className="text-lg font-bold text-chart-3">
              ${Math.abs(signal.stopLoss - signal.entry).toFixed(2)} (
              {(((signal.stopLoss - signal.entry) / signal.entry) * 100).toFixed(1)}%)
            </span>
          </div>
          <div className="pt-3 border-t border-border/30 flex items-center justify-between">
            <span className="text-muted-foreground font-semibold">Risk/Reward Ratio</span>
            <span className="text-xl font-bold text-primary">
              1:{(Math.abs(signal.target - signal.entry) / Math.abs(signal.stopLoss - signal.entry)).toFixed(2)}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
