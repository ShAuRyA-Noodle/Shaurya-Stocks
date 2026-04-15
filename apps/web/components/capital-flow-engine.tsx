"use client"

import { useEffect, useRef, useState } from "react"
import { DollarSign, Shield, TrendingUp, AlertTriangle, Lock, Unlock, Activity, Target } from "lucide-react"
import { glassPanel, glassPanelHover } from "@/lib/cn-utils"

interface CapitalPool {
  total: number
  deployed: number
  idle: number
  atRisk: number
}

interface FlowSignal {
  name: string
  pull: number // Positive = pulling capital, Negative = pushing away
  angle: number
  active: boolean
  riskLevel: "LOW" | "MEDIUM" | "HIGH"
}

export function CapitalFlowEngine() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [capitalPool, setCapitalPool] = useState<CapitalPool>({
    total: 100000,
    deployed: 15000,
    idle: 80000,
    atRisk: 5000,
  })
  
  const [flowSignals, setFlowSignals] = useState<FlowSignal[]>([
    { name: "Momentum Alpha", pull: 0.3, angle: 0, active: true, riskLevel: "LOW" },
    { name: "Mean Reversion", pull: -0.2, angle: Math.PI / 3, active: true, riskLevel: "MEDIUM" },
    { name: "Volatility Spike", pull: -0.6, angle: (2 * Math.PI) / 3, active: true, riskLevel: "HIGH" },
    { name: "Trend Strength", pull: 0.4, angle: Math.PI, active: true, riskLevel: "LOW" },
    { name: "Risk Regime", pull: -0.5, angle: (4 * Math.PI) / 3, active: true, riskLevel: "HIGH" },
    { name: "Market Liquidity", pull: 0.1, angle: (5 * Math.PI) / 3, active: false, riskLevel: "MEDIUM" },
  ])

  const [drawdownPressure, setDrawdownPressure] = useState(12)
  const [protectionLevel, setProtectionLevel] = useState(85)

  // Capital-flow state will stream from the backend /portfolio/flow endpoint
  // once it lands. Until then, the component renders its static initial state
  // rather than fabricating drift.

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
    const baseRadius = Math.min(width, height) * 0.15

    let animationFrame: number
    let time = 0
    let particles: Array<{
      x: number
      y: number
      vx: number
      vy: number
      life: number
      isPulling: boolean
    }> = []

    const animate = () => {
      ctx.clearRect(0, 0, width, height)
      time += 0.02

      // Create particles for capital flow (time-gated rather than random)
      if (Math.floor(time * 5) % 3 === 0) {
        flowSignals.forEach((signal, idx) => {
          if (signal.active) {
            const signalRadius = baseRadius * 2.5
            const signalX = centerX + Math.cos(signal.angle) * signalRadius
            const signalY = centerY + Math.sin(signal.angle) * signalRadius

            if (signal.pull > 0) {
              // Capital flowing FROM center TO signal (deployment)
              particles.push({
                x: centerX,
                y: centerY,
                vx: (signalX - centerX) * 0.02,
                vy: (signalY - centerY) * 0.02,
                life: 1,
                isPulling: true,
              })
            } else {
              // Risk pushing capital BACK to center (protection)
              particles.push({
                x: signalX,
                y: signalY,
                vx: (centerX - signalX) * 0.02,
                vy: (centerY - signalY) * 0.02,
                life: 1,
                isPulling: false,
              })
            }
          }
        })
      }

      // Update and draw particles
      particles = particles.filter((p) => {
        p.x += p.vx
        p.y += p.vy
        p.life -= 0.02

        if (p.life > 0) {
          ctx.beginPath()
          ctx.arc(p.x, p.y, 3, 0, Math.PI * 2)
          ctx.fillStyle = p.isPulling
            ? `rgba(0, 240, 255, ${p.life * 0.8})`
            : `rgba(255, 200, 100, ${p.life * 0.8})`
          ctx.fill()

          // Glow
          const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, 10)
          gradient.addColorStop(0, p.isPulling ? `rgba(0, 240, 255, ${p.life * 0.3})` : `rgba(255, 200, 100, ${p.life * 0.3})`)
          gradient.addColorStop(1, "transparent")
          ctx.fillStyle = gradient
          ctx.beginPath()
          ctx.arc(p.x, p.y, 10, 0, Math.PI * 2)
          ctx.fill()

          return true
        }
        return false
      })

      // Draw flow lines and signal nodes
      flowSignals.forEach((signal, idx) => {
        const signalRadius = baseRadius * 2.5
        const nodeX = centerX + Math.cos(signal.angle) * signalRadius
        const nodeY = centerY + Math.sin(signal.angle) * signalRadius

        // Draw connection line
        if (signal.active) {
          ctx.beginPath()
          ctx.moveTo(centerX, centerY)
          ctx.lineTo(nodeX, nodeY)
          
          const intensity = Math.abs(signal.pull)
          if (signal.pull > 0) {
            // Pulling capital (deployment)
            ctx.strokeStyle = `rgba(0, 240, 255, ${intensity * 0.6})`
            ctx.lineWidth = 2 + intensity * 4
          } else {
            // Pushing capital (protection)
            ctx.strokeStyle = `rgba(255, 150, 100, ${intensity * 0.6})`
            ctx.lineWidth = 2 + intensity * 3
          }
          ctx.stroke()

          // Animated flow direction arrows
          const arrowCount = 3
          for (let i = 0; i < arrowCount; i++) {
            const arrowProgress = ((time * 2 + i / arrowCount) % 1)
            const arrowX = centerX + (nodeX - centerX) * arrowProgress
            const arrowY = centerY + (nodeY - centerY) * arrowProgress
            
            const arrowAngle = signal.pull > 0 ? signal.angle : signal.angle + Math.PI
            const arrowSize = 8

            ctx.save()
            ctx.translate(arrowX, arrowY)
            ctx.rotate(arrowAngle)
            ctx.beginPath()
            ctx.moveTo(arrowSize, 0)
            ctx.lineTo(-arrowSize / 2, arrowSize / 2)
            ctx.lineTo(-arrowSize / 2, -arrowSize / 2)
            ctx.closePath()
            ctx.fillStyle = signal.pull > 0 
              ? `rgba(0, 240, 255, ${intensity * arrowProgress})` 
              : `rgba(255, 150, 100, ${intensity * arrowProgress})`
            ctx.fill()
            ctx.restore()
          }
        } else {
          // Inactive line
          ctx.beginPath()
          ctx.moveTo(centerX, centerY)
          ctx.lineTo(nodeX, nodeY)
          ctx.strokeStyle = "rgba(255, 255, 255, 0.05)"
          ctx.lineWidth = 1
          ctx.stroke()
        }

        // Draw signal node
        const nodeRadius = signal.active ? 14 : 8
        const pulseScale = signal.active ? 1 + Math.sin(time * 3 + idx) * 0.15 : 1

        // Node glow
        if (signal.active) {
          const glowGradient = ctx.createRadialGradient(nodeX, nodeY, 0, nodeX, nodeY, nodeRadius * 3)
          const glowColor = signal.pull > 0 ? "0, 240, 255" : "255, 150, 100"
          glowGradient.addColorStop(0, `rgba(${glowColor}, ${Math.abs(signal.pull) * 0.4})`)
          glowGradient.addColorStop(1, "transparent")
          ctx.fillStyle = glowGradient
          ctx.beginPath()
          ctx.arc(nodeX, nodeY, nodeRadius * 3 * pulseScale, 0, Math.PI * 2)
          ctx.fill()
        }

        // Node circle
        ctx.beginPath()
        ctx.arc(nodeX, nodeY, nodeRadius * pulseScale, 0, Math.PI * 2)
        
        if (signal.active) {
          if (signal.pull > 0) {
            ctx.fillStyle = `rgba(0, 240, 255, 0.9)`
          } else {
            ctx.fillStyle = `rgba(255, 150, 100, 0.9)`
          }
        } else {
          ctx.fillStyle = "rgba(255, 255, 255, 0.2)"
        }
        ctx.fill()

        // Inner highlight
        if (signal.active) {
          ctx.beginPath()
          ctx.arc(nodeX, nodeY, nodeRadius * pulseScale * 0.4, 0, Math.PI * 2)
          ctx.fillStyle = "rgba(255, 255, 255, 0.9)"
          ctx.fill()
        }
      })

      // Draw center capital pool
      const poolPulse = 1 + Math.sin(time * 1.5) * 0.08
      const poolRadius = baseRadius * poolPulse

      // Protection shield ring
      ctx.beginPath()
      ctx.arc(centerX, centerY, poolRadius * 2, 0, Math.PI * 2)
      ctx.strokeStyle = `rgba(100, 255, 150, ${protectionLevel * 0.004})`
      ctx.lineWidth = 6
      ctx.stroke()

      // Outer glow
      const outerGlow = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, poolRadius * 3)
      outerGlow.addColorStop(0, "rgba(100, 200, 255, 0.2)")
      outerGlow.addColorStop(1, "transparent")
      ctx.fillStyle = outerGlow
      ctx.beginPath()
      ctx.arc(centerX, centerY, poolRadius * 3, 0, Math.PI * 2)
      ctx.fill()

      // Main pool circle
      const poolGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, poolRadius)
      poolGradient.addColorStop(0, "rgba(0, 200, 255, 0.3)")
      poolGradient.addColorStop(0.7, "rgba(0, 150, 255, 0.2)")
      poolGradient.addColorStop(1, "rgba(0, 100, 200, 0.1)")
      ctx.fillStyle = poolGradient
      ctx.beginPath()
      ctx.arc(centerX, centerY, poolRadius, 0, Math.PI * 2)
      ctx.fill()

      // Pool border
      ctx.beginPath()
      ctx.arc(centerX, centerY, poolRadius, 0, Math.PI * 2)
      ctx.strokeStyle = "rgba(0, 240, 255, 0.8)"
      ctx.lineWidth = 3
      ctx.stroke()

      // Inner core
      ctx.beginPath()
      ctx.arc(centerX, centerY, poolRadius * 0.3, 0, Math.PI * 2)
      ctx.fillStyle = "rgba(255, 255, 255, 0.9)"
      ctx.fill()

      animationFrame = requestAnimationFrame(animate)
    }

    animate()

    return () => {
      cancelAnimationFrame(animationFrame)
    }
  }, [flowSignals, protectionLevel])

  return (
    <div className={`${glassPanelHover()} h-full rounded-2xl overflow-hidden flex flex-col`}>
      {/* Header */}
      <div className="p-6 border-b border-border/50">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <DollarSign className="w-5 h-5 text-primary" />
            Capital Flow Engine
          </h3>
          <div className={`${glassPanel()} px-3 py-1.5 rounded-lg flex items-center gap-2`}>
            <div className="relative">
              <Activity className="w-3.5 h-3.5 text-chart-2" />
              <div className="absolute inset-0 bg-chart-2 rounded-full blur animate-pulse" />
            </div>
            <span className="text-xs font-mono text-chart-2 font-semibold">CAPITAL TRACKING</span>
          </div>
        </div>

        {/* Capital Metrics */}
        <div className="grid grid-cols-4 gap-3">
          <div className={`${glassPanel()} p-4 rounded-xl relative overflow-hidden`}>
            <div className="absolute top-0 right-0 w-20 h-20 bg-primary/10 rounded-full blur-2xl" />
            <div className="relative z-10">
              <div className="flex items-center gap-2 mb-2">
                <Target className="w-4 h-4 text-primary" />
                <span className="text-xs text-muted-foreground font-mono font-semibold">TOTAL CAPITAL</span>
              </div>
              <div className="text-2xl font-bold font-mono text-primary">
                ${(capitalPool.total / 1000).toFixed(0)}K
              </div>
            </div>
          </div>

          <div className={`${glassPanel()} p-4 rounded-xl relative overflow-hidden`}>
            <div className="absolute top-0 right-0 w-20 h-20 bg-chart-2/10 rounded-full blur-2xl" />
            <div className="relative z-10">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="w-4 h-4 text-chart-2" />
                <span className="text-xs text-muted-foreground font-mono font-semibold">DEPLOYED</span>
              </div>
              <div className="text-2xl font-bold font-mono text-chart-2">
                ${(capitalPool.deployed / 1000).toFixed(1)}K
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {((capitalPool.deployed / capitalPool.total) * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          <div className={`${glassPanel()} p-4 rounded-xl relative overflow-hidden`}>
            <div className="absolute top-0 right-0 w-20 h-20 bg-green-400/10 rounded-full blur-2xl" />
            <div className="relative z-10">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="w-4 h-4 text-green-400" />
                <span className="text-xs text-muted-foreground font-mono font-semibold">IDLE (SAFE)</span>
              </div>
              <div className="text-2xl font-bold font-mono text-green-400">
                ${(capitalPool.idle / 1000).toFixed(1)}K
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {((capitalPool.idle / capitalPool.total) * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          <div className={`${glassPanel()} p-4 rounded-xl relative overflow-hidden`}>
            <div className="absolute top-0 right-0 w-20 h-20 bg-orange-400/10 rounded-full blur-2xl" />
            <div className="relative z-10">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-orange-400" />
                <span className="text-xs text-muted-foreground font-mono font-semibold">AT RISK</span>
              </div>
              <div className="text-2xl font-bold font-mono text-orange-400">
                ${(capitalPool.atRisk / 1000).toFixed(1)}K
              </div>
              <div className="text-xs text-muted-foreground mt-1">
                {((capitalPool.atRisk / capitalPool.total) * 100).toFixed(1)}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Canvas Visualization */}
      <div className="flex-1 relative bg-linear-to-br from-background via-card to-background">
        <canvas ref={canvasRef} className="w-full h-full" style={{ minHeight: "400px" }} />

        {/* Center Label */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-center pointer-events-none">
          <div className={`${glassPanel()} px-6 py-4 rounded-xl`}>
            <div className="text-xs text-muted-foreground font-mono mb-1">CAPITAL POOL</div>
            <div className="text-3xl font-bold font-mono text-primary mb-1">
              ${(capitalPool.total / 1000).toFixed(0)}K
            </div>
            <div className="flex items-center justify-center gap-2 text-xs font-mono">
              {capitalPool.idle > capitalPool.deployed ? (
                <>
                  <Lock className="w-3.5 h-3.5 text-green-400" />
                  <span className="text-green-400 font-semibold">PROTECTED</span>
                </>
              ) : (
                <>
                  <Unlock className="w-3.5 h-3.5 text-orange-400" />
                  <span className="text-orange-400 font-semibold">EXPOSED</span>
                </>
              )}
            </div>
          </div>
        </div>

        {/* Signal Labels */}
        {flowSignals.map((signal, index) => {
          const labelRadius = Math.min(
            canvasRef.current?.offsetWidth || 500,
            canvasRef.current?.offsetHeight || 500
          ) * 0.38
          const x = 50 + (Math.cos(signal.angle) * labelRadius * 100) / (canvasRef.current?.offsetWidth || 500)
          const y = 50 + (Math.sin(signal.angle) * labelRadius * 100) / (canvasRef.current?.offsetHeight || 500)

          return (
            <div
              key={signal.name}
              className={`absolute ${glassPanel()} px-3 py-2 rounded-lg transition-all duration-300 ${
                signal.active ? "opacity-100" : "opacity-30"
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
              <div className="flex items-center gap-1.5">
                {signal.pull > 0 ? (
                  <TrendingUp className="w-3 h-3 text-chart-2" />
                ) : (
                  <Shield className="w-3 h-3 text-orange-400" />
                )}
                <span
                  className={`text-sm font-bold font-mono ${
                    signal.pull > 0 ? "text-chart-2" : "text-orange-400"
                  }`}
                >
                  {signal.pull > 0 ? "PULL" : "PUSH"}
                </span>
              </div>
              <div className="text-[9px] text-muted-foreground font-mono mt-0.5">
                {Math.abs(signal.pull * 100).toFixed(0)}%
              </div>
            </div>
          )
        })}

        {/* Bottom Status Bars */}
        <div className="absolute bottom-4 left-4 right-4 space-y-2">
          <div className={`${glassPanel()} px-4 py-3 rounded-lg`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-orange-400" />
                <span className="text-xs text-muted-foreground font-mono font-semibold">DRAWDOWN PRESSURE</span>
              </div>
              <span className="text-sm font-bold font-mono text-orange-400">{drawdownPressure.toFixed(0)}%</span>
            </div>
            <div className="h-2 bg-border/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-linear-to-r from-orange-400/50 to-orange-400 transition-all duration-500"
                style={{ width: `${drawdownPressure}%` }}
              />
            </div>
          </div>

          <div className={`${glassPanel()} px-4 py-3 rounded-lg`}>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-green-400" />
                <span className="text-xs text-muted-foreground font-mono font-semibold">CAPITAL PROTECTION</span>
              </div>
              <span className="text-sm font-bold font-mono text-green-400">{protectionLevel.toFixed(0)}%</span>
            </div>
            <div className="h-2 bg-border/30 rounded-full overflow-hidden">
              <div
                className="h-full bg-linear-to-r from-green-400/50 to-green-400 transition-all duration-500"
                style={{ width: `${protectionLevel}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}