"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { ArrowRight, Sparkles } from "lucide-react"
import { glassPanel, glassPanelHover, neonGlowCyan } from "@/lib/cn-utils"

export function HeroSection() {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [signalsCount, setSignalsCount] = useState(1247892)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext("2d")
    if (!ctx) return

    // Set canvas size
    const updateSize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }
    updateSize()
    window.addEventListener("resize", updateSize)

    // Particle system for "Data Galaxy"
    interface Particle {
      x: number
      y: number
      z: number
      vx: number
      vy: number
      vz: number
      size: number
      color: string
      alpha: number
    }

    const particles: Particle[] = []
    const particleCount = 800
    const colors = ["#00F0FF", "#39FF14", "#FF003C", "#FFA500"]

    // Initialize particles
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: (Math.random() - 0.5) * canvas.width * 2,
        y: (Math.random() - 0.5) * canvas.height * 2,
        z: Math.random() * 1000,
        vx: (Math.random() - 0.5) * 0.5,
        vy: (Math.random() - 0.5) * 0.5,
        vz: (Math.random() - 0.5) * 2,
        size: Math.random() * 2 + 1,
        color: colors[Math.floor(Math.random() * colors.length)],
        alpha: Math.random() * 0.5 + 0.3,
      })
    }

    let animationFrame: number
    let mouseX = 0
    let mouseY = 0

    const handleMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX
      mouseY = e.clientY
    }
    window.addEventListener("mousemove", handleMouseMove)

    // Animation loop
    const animate = () => {
      ctx.fillStyle = "rgba(3, 3, 4, 0.1)"
      ctx.fillRect(0, 0, canvas.width, canvas.height)

      particles.forEach((particle) => {
        // Update position
        particle.x += particle.vx
        particle.y += particle.vy
        particle.z += particle.vz

        // Mouse interaction - particles attracted to cursor
        const dx = mouseX - particle.x
        const dy = mouseY - particle.y
        const distance = Math.sqrt(dx * dx + dy * dy)
        if (distance < 150) {
          particle.x += dx * 0.002
          particle.y += dy * 0.002
        }

        // Reset particles that go off screen
        if (particle.z > 1000 || particle.z < 0) {
          particle.z = 0
          particle.x = (Math.random() - 0.5) * canvas.width * 2
          particle.y = (Math.random() - 0.5) * canvas.height * 2
        }

        if (Math.abs(particle.x) > canvas.width || Math.abs(particle.y) > canvas.height) {
          particle.x = (Math.random() - 0.5) * canvas.width * 2
          particle.y = (Math.random() - 0.5) * canvas.height * 2
        }

        // 3D projection
        const scale = 1000 / (1000 + particle.z)
        const x2d = particle.x * scale + canvas.width / 2
        const y2d = particle.y * scale + canvas.height / 2
        const size = particle.size * scale

        // Draw particle with glow
        ctx.beginPath()
        ctx.arc(x2d, y2d, size, 0, Math.PI * 2)
        ctx.fillStyle = particle.color
        ctx.globalAlpha = particle.alpha * scale
        ctx.fill()

        // Add glow effect
        const gradient = ctx.createRadialGradient(x2d, y2d, 0, x2d, y2d, size * 3)
        gradient.addColorStop(0, particle.color)
        gradient.addColorStop(1, "transparent")
        ctx.fillStyle = gradient
        ctx.globalAlpha = particle.alpha * scale * 0.3
        ctx.fill()
        ctx.globalAlpha = 1
      })

      animationFrame = requestAnimationFrame(animate)
    }
    animate()

    return () => {
      window.removeEventListener("resize", updateSize)
      window.removeEventListener("mousemove", handleMouseMove)
      cancelAnimationFrame(animationFrame)
    }
  }, [])

  // Animate signals counter
  useEffect(() => {
    const interval = setInterval(() => {
      setSignalsCount((prev) => prev + Math.floor(Math.random() * 5 + 1))
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Data Galaxy Background */}
      <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" style={{ background: "rgb(3, 3, 4)" }} />

      {/* Content */}
      <div className="relative z-10 container mx-auto px-6 text-center">
        {/* Floating badge */}
        <div
          className={`inline-flex items-center gap-2 ${glassPanel()} px-4 py-2 rounded-full mb-8 animate-pulse-glow`}
        >
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="text-sm font-mono text-primary">Real-Time AI Trading Intelligence</span>
        </div>

        {/* Headline with masked video effect simulation */}
        <h1 className="text-7xl md:text-9xl font-bold tracking-tighter mb-6 leading-none">
          <span className="block text-gradient-cyan animate-pulse-glow">ORACLE</span>
        </h1>

        <p className="text-xl md:text-2xl text-muted-foreground max-w-3xl mx-auto mb-12 leading-relaxed">
          The definitive AI-driven quantitative trading terminal.{" "}
          <span className="text-foreground font-semibold">Neural ensemble predictions</span> meet{" "}
          <span className="text-foreground font-semibold">institutional-grade execution</span>.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16">
          <Button
            size="lg"
            className={`${glassPanelHover()} ${neonGlowCyan()} bg-primary text-primary-foreground hover:bg-primary/90 px-8 py-6 text-lg font-semibold group`}
          >
            Enter Terminal
            <ArrowRight className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Button>
          <Button
            size="lg"
            variant="outline"
            className={`${glassPanelHover()} px-8 py-6 text-lg border-primary/30 hover:border-primary/60 bg-transparent`}
          >
            Watch Demo
          </Button>
        </div>

        {/* Live Stats - Odometer style */}
        <div className={`${glassPanel()} inline-flex flex-col items-center px-8 py-6 rounded-xl`}>
          <div className="text-sm font-mono text-muted-foreground mb-2 uppercase tracking-wider">
            Real-Time Signals Generated
          </div>
          <div className="text-4xl font-mono font-bold text-primary tabular-nums">{signalsCount.toLocaleString()}</div>
        </div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-background to-transparent pointer-events-none" />
    </section>
  )
}
