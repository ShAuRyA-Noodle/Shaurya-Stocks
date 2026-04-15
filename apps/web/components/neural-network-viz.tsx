"use client"

import { useEffect, useRef, useState } from "react"
import { Brain, Shield, TrendingUp, Activity, Zap, AlertTriangle, Target, ChevronRight } from "lucide-react"
import { glassPanel, glassPanelHover } from "@/lib/cn-utils"

interface SignalComponent {
  name: string
  value: number
  weight: number
  active: boolean
}

interface DecisionState {
  decision: "BUY" | "HOLD" | "SELL"
  confidence: number
  riskState: "LOW" | "MEDIUM" | "HIGH" | "EXTREME"
  capitalDeployed: number
  signals: SignalComponent[]
}
export function NeuralNetworkViz() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [decisionState, setDecisionState] = useState<DecisionState>({
    decision: "HOLD",
    confidence: 53,
    riskState: "HIGH",
    capitalDeployed: 0,
    signals: [
      { name: "TS Momentum", value: 0.21, weight: 0.25, active: true },
      { name: "CS Alpha Rank", value: 0.34, weight: 0.20, active: true },
      { name: "Volatility Filter", value: -0.48, weight: 0.25, active: true },
      { name: "Regime Filter", value: -0.12, weight: 0.15, active: true },
      { name: "Volume Confirm", value: 0.08, weight: 0.15, active: false },
    ],
  })

  const [pulseIntensity, setPulseIntensity] = useState(0)

  useEffect(() => {
    // Simulate live signal updates
    const interval = setInterval(() => {
      setDecisionState((prev) => {
        const newSignals = prev.signals.map((signal) => ({
          ...signal,
          value: signal.value + (Math.random() - 0.5) * 0.1,
          active: Math.abs(signal.value) > 0.15,
        }))

        const ensembleScore = newSignals.reduce((sum, s) => sum + s.value * s.weight, 0)
        const confidence = Math.min(95, Math.max(30, 50 + Math.abs(ensembleScore) * 100))

        let decision: "BUY" | "HOLD" | "SELL" = "HOLD"
        if (ensembleScore > 0.25 && confidence > 65) decision = "BUY"
        else if (ensembleScore < -0.25 && confidence > 65) decision = "SELL"

        const volatilitySignal = newSignals.find((s) => s.name === "Volatility Filter")
        let riskState: "LOW" | "MEDIUM" | "HIGH" | "EXTREME" = "MEDIUM"
        if (volatilitySignal) {
          if (Math.abs(volatilitySignal.value) > 0.6) riskState = "EXTREME"
          else if (Math.abs(volatilitySignal.value) > 0.4) riskState = "HIGH"
          else if (Math.abs(volatilitySignal.value) > 0.2) riskState = "MEDIUM"
          else riskState = "LOW"
        }

        return {
          ...prev,
          signals: newSignals,
          decision,
          confidence: Math.round(confidence),
          riskState,
          capitalDeployed: decision === "HOLD" ? 0 : Math.round(confidence * 0.8),
        }
      })
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    const updateSize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio
      canvas.height = canvas.offsetHeight * window.devicePixelRatio
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
    }
    updateSize()

    const width = canvas.offsetWidth
    const height = canvas.offsetHeight
    const centerX = width / 2
    const centerY = height / 2
    const radius = Math.min(width, height) * 0.35

    let animationFrame: number
    let time = 0

    const animate = () => {
      ctx.clearRect(0, 0, width, height)
      time += 0.02

      // Draw connection lines from center to signals
      decisionState.signals.forEach((signal, index) => {
        const angle = (index / decisionState.signals.length) * Math.PI * 2 - Math.PI / 2
        const nodeX = centerX + Math.cos(angle) * radius
        const nodeY = centerY + Math.sin(angle) * radius

        if (signal.active) {
          // Animated flowing particles
          const flowProgress = (time * 2 + index) % 1
          const particleX = centerX + (nodeX - centerX) * flowProgress
          const particleY = centerY + (nodeY - centerY) * flowProgress

          // Draw connection line
          ctx.beginPath()
          ctx.moveTo(centerX, centerY)
          ctx.lineTo(nodeX, nodeY)
          const intensity = Math.abs(signal.value)
          ctx.strokeStyle = signal.value > 0 
            ? `rgba(0, 240, 255, ${intensity * 0.5})` 
            : `rgba(255, 100, 100, ${intensity * 0.5})`
          ctx.lineWidth = 2 + intensity * 3
          ctx.stroke()

          // Draw flowing particle
          const gradient = ctx.createRadialGradient(particleX, particleY, 0, particleX, particleY, 8)
          gradient.addColorStop(0, signal.value > 0 ? "rgba(0, 240, 255, 0.8)" : "rgba(255, 100, 100, 0.8)")
          gradient.addColorStop(1, "transparent")
          ctx.fillStyle = gradient
          ctx.beginPath()
          ctx.arc(particleX, particleY, 8, 0, Math.PI * 2)
          ctx.fill()
        } else {
          // Inactive connection
          ctx.beginPath()
          ctx.moveTo(centerX, centerY)
          ctx.lineTo(nodeX, nodeY)
          ctx.strokeStyle = "rgba(255, 255, 255, 0.05)"
          ctx.lineWidth = 1
          ctx.stroke()
        }

        // Draw signal node
        const nodeRadius = signal.active ? 12 : 8
        const pulseScale = signal.active ? 1 + Math.sin(time * 3 + index) * 0.2 : 1

        // Glow effect
        if (signal.active) {
          const glowGradient = ctx.createRadialGradient(nodeX, nodeY, 0, nodeX, nodeY, nodeRadius * 3)
          glowGradient.addColorStop(0, signal.value > 0 ? "rgba(0, 240, 255, 0.4)" : "rgba(255, 100, 100, 0.4)")
          glowGradient.addColorStop(1, "transparent")
          ctx.fillStyle = glowGradient
          ctx.beginPath()
          ctx.arc(nodeX, nodeY, nodeRadius * 3 * pulseScale, 0, Math.PI * 2)
          ctx.fill()
        }

        // Node circle
        ctx.beginPath()
        ctx.arc(nodeX, nodeY, nodeRadius * pulseScale, 0, Math.PI * 2)
        ctx.fillStyle = signal.active
          ? signal.value > 0
            ? "rgba(0, 240, 255, 0.9)"
            : "rgba(255, 100, 100, 0.9)"
          : "rgba(255, 255, 255, 0.2)"
        ctx.fill()

        // Inner highlight
        if (signal.active) {
          ctx.beginPath()
          ctx.arc(nodeX, nodeY, nodeRadius * pulseScale * 0.4, 0, Math.PI * 2)
          ctx.fillStyle = "rgba(255, 255, 255, 0.8)"
          ctx.fill()
        }
      })

      // Draw center decision node
      const centerPulse = 1 + Math.sin(time * 2) * 0.1
      const centerRadius = 30

      // Outer glow
      const centerGlow = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, centerRadius * 4)
      const glowColor = decisionState.decision === "BUY" 
        ? "rgba(0, 240, 255, 0.3)" 
        : decisionState.decision === "SELL"
        ? "rgba(255, 100, 100, 0.3)"
        : "rgba(150, 150, 150, 0.2)"
      centerGlow.addColorStop(0, glowColor)
      centerGlow.addColorStop(1, "transparent")
      ctx.fillStyle = centerGlow
      ctx.beginPath()
      ctx.arc(centerX, centerY, centerRadius * 4 * centerPulse, 0, Math.PI * 2)
      ctx.fill()

      // Center circle
      ctx.beginPath()
      ctx.arc(centerX, centerY, centerRadius * centerPulse, 0, Math.PI * 2)
      const fillColor = decisionState.decision === "BUY"
        ? "rgba(0, 240, 255, 0.2)"
        : decisionState.decision === "SELL"
        ? "rgba(255, 100, 100, 0.2)"
        : "rgba(150, 150, 150, 0.15)"
      ctx.fillStyle = fillColor
      ctx.fill()
      ctx.strokeStyle = decisionState.decision === "BUY"
        ? "rgba(0, 240, 255, 0.8)"
        : decisionState.decision === "SELL"
        ? "rgba(255, 100, 100, 0.8)"
        : "rgba(200, 200, 200, 0.6)"
      ctx.lineWidth = 3
      ctx.stroke()

      animationFrame = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      cancelAnimationFrame(animationFrame)
    }
  }, [decisionState])

  const getRiskColor = (state: string) => {
    switch (state) {
      case "LOW": return "text-chart-2"
      case "MEDIUM": return "text-yellow-400"
      case "HIGH": return "text-orange-400"
      case "EXTREME": return "text-red-400"
      default: return "text-muted-foreground"
    }
  }

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case "BUY": return "text-chart-2"
      case "SELL": return "text-red-400"
      default: return "text-muted-foreground"
    }
  }

  return (
    <div className={`${glassPanelHover()} h-full rounded-2xl overflow-hidden flex flex-col`}>
      {/* Header */}
      <div className="p-6 border-b border-border/50">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Brain className="w-5 h-5 text-primary" />
            Alpha Decision Engine
          </h3>
          <div className={`${glassPanel()} px-3 py-1.5 rounded-lg flex items-center gap-2`}>
            <div className="relative">
              <Activity className="w-3.5 h-3.5 text-primary" />
              <div className="absolute inset-0 bg-primary rounded-full blur animate-pulse" />
            </div>
            <span className="text-xs font-mono text-primary font-semibold">LIVE ENSEMBLE</span>
          </div>
        </div>
      </div>

      {/* Main Visualization */}
      <div className="flex-1 relative bg-linear-to-br from-background via-card to-background">
        <canvas ref={canvasRef} className="w-full h-full" style={{ minHeight: "400px" }} />

        {/* Center Decision Display */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center pointer-events-none">
          <div className={`${glassPanel()} px-6 py-4 rounded-xl`}>
            <div className="text-xs text-muted-foreground font-mono mb-1">FINAL DECISION</div>
            <div className={`text-4xl font-bold font-mono mb-2 ${getDecisionColor(decisionState.decision)}`}>
              {decisionState.decision}
            </div>
            <div className="text-xs text-muted-foreground font-mono">
              Confidence: <span className="text-primary font-bold">{decisionState.confidence}%</span>
            </div>
          </div>
        </div>

        {/* Signal Labels */}
        {decisionState.signals.map((signal, index) => {
          const angle = (index / decisionState.signals.length) * Math.PI * 2 - Math.PI / 2
          const labelRadius = Math.min(
            canvasRef.current?.offsetWidth || 500,
            canvasRef.current?.offsetHeight || 500
          ) * 0.42
          const x = 50 + (Math.cos(angle) * labelRadius * 100) / (canvasRef.current?.offsetWidth || 500)
          const y = 50 + (Math.sin(angle) * labelRadius * 100) / (canvasRef.current?.offsetHeight || 500)

          return (
            <div
              key={signal.name}
              className={`absolute ${glassPanel()} px-3 py-2 rounded-lg transition-all duration-300 ${
                signal.active ? "opacity-100" : "opacity-40"
              }`}
              style={{
                left: `${x}%`,
                top: `${y}%`,
                transform: "translate(-50%, -50%)",
              }}
            >
              <div className="text-[10px] text-muted-foreground font-mono font-semibold mb-0.5">
                {signal.name}
              </div>
              <div
                className={`text-sm font-bold font-mono ${
                  signal.value > 0 ? "text-chart-2" : "text-red-400"
                }`}
              >
                {signal.value > 0 ? "+" : ""}
                {signal.value.toFixed(2)}
              </div>
              <div className="text-[9px] text-muted-foreground font-mono">
                w: {signal.weight.toFixed(2)}
              </div>
            </div>
          )
        })}

        {/* Bottom Stats Panel */}
        <div className="absolute bottom-4 left-4 right-4 flex gap-3">
          <div className={`${glassPanel()} flex-1 px-4 py-3 rounded-lg`}>
            <div className="flex items-center gap-2 mb-1">
              <Shield className={`w-4 h-4 ${getRiskColor(decisionState.riskState)}`} />
              <span className="text-xs text-muted-foreground font-mono font-semibold">RISK STATE</span>
            </div>
            <div className={`text-xl font-bold font-mono ${getRiskColor(decisionState.riskState)}`}>
              {decisionState.riskState}
            </div>
          </div>

          <div className={`${glassPanel()} flex-1 px-4 py-3 rounded-lg`}>
            <div className="flex items-center gap-2 mb-1">
              <Target className="w-4 h-4 text-primary" />
              <span className="text-xs text-muted-foreground font-mono font-semibold">CAPITAL DEPLOYED</span>
            </div>
            <div className="text-xl font-bold font-mono text-primary">
              {decisionState.capitalDeployed}%
            </div>
          </div>

          <div className={`${glassPanel()} flex-1 px-4 py-3 rounded-lg`}>
            <div className="flex items-center gap-2 mb-1">
              <Zap className="w-4 h-4 text-chart-2" />
              <span className="text-xs text-muted-foreground font-mono font-semibold">ACTIVE SIGNALS</span>
            </div>
            <div className="text-xl font-bold font-mono text-chart-2">
              {decisionState.signals.filter((s) => s.active).length}/{decisionState.signals.length}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}