"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

import {
  formatDateLong,
  formatDateTick,
  formatUsd,
  formatUsdShort,
  parseIsoDate,
} from "@/lib/oracle/format"
import type { EquityPoint } from "@/lib/oracle/types"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

interface EquityCurveProps {
  readonly points: readonly EquityPoint[]
  readonly initialCapital: number
}

const VIEW_W = 1000
const VIEW_H = 360
const PAD_LEFT = 72
const PAD_RIGHT = 24
const PAD_TOP = 24
const PAD_BOTTOM = 44
const N_X_TICKS = 6
const N_Y_TICKS = 5

interface Scaled {
  readonly x: number
  readonly y: number
  readonly point: EquityPoint
}

interface ChartGeom {
  readonly scaled: readonly Scaled[]
  readonly path: string
  readonly area: string
  readonly yTicks: readonly { readonly y: number; readonly value: number }[]
  readonly xTicks: readonly { readonly x: number; readonly point: EquityPoint }[]
  readonly innerW: number
  readonly innerH: number
  readonly minE: number
  readonly maxE: number
}

function buildGeom(points: readonly EquityPoint[]): ChartGeom {
  const innerW = VIEW_W - PAD_LEFT - PAD_RIGHT
  const innerH = VIEW_H - PAD_TOP - PAD_BOTTOM

  const ts = points.map((p) => parseIsoDate(p.date).getTime())
  const minT = ts[0] ?? 0
  const maxT = ts[ts.length - 1] ?? 1
  const spanT = Math.max(1, maxT - minT)

  const equities = points.map((p) => p.equity)
  const minE = Math.min(...equities)
  const maxE = Math.max(...equities)
  // Pad the y-range slightly so the curve doesn't ride the edges.
  const pad = (maxE - minE) * 0.08
  const lo = minE - pad
  const hi = maxE + pad
  const spanE = Math.max(1, hi - lo)

  const scaled: Scaled[] = points.map((p, i) => {
    const t = ts[i] ?? minT
    const x = PAD_LEFT + ((t - minT) / spanT) * innerW
    const y = PAD_TOP + (1 - (p.equity - lo) / spanE) * innerH
    return { x, y, point: p }
  })

  // Polyline path
  const path = scaled
    .map((s, i) => `${i === 0 ? "M" : "L"}${s.x.toFixed(2)},${s.y.toFixed(2)}`)
    .join(" ")

  // Area fill from baseline (bottom of inner chart) closing back to start.
  const baseY = PAD_TOP + innerH
  const first = scaled[0]
  const last = scaled[scaled.length - 1]
  const area = first && last
    ? `${path} L${last.x.toFixed(2)},${baseY.toFixed(2)} L${first.x.toFixed(2)},${baseY.toFixed(2)} Z`
    : ""

  // Y ticks at evenly spaced equity values.
  const yTicks = Array.from({ length: N_Y_TICKS }, (_, i) => {
    const frac = i / (N_Y_TICKS - 1)
    const value = lo + spanE * (1 - frac)
    const y = PAD_TOP + frac * innerH
    return { y, value }
  })

  // X ticks evenly spaced across the index, snapped to actual data points
  // so labels always correspond to a real rebalance date.
  const xTicks: { x: number; point: EquityPoint }[] = []
  if (points.length > 0) {
    for (let i = 0; i < N_X_TICKS; i += 1) {
      const idx = Math.round((i * (points.length - 1)) / (N_X_TICKS - 1))
      const s = scaled[idx]
      if (s) xTicks.push({ x: s.x, point: s.point })
    }
  }

  return { scaled, path, area, yTicks, xTicks, innerW, innerH, minE, maxE }
}

export function EquityCurve({ points, initialCapital }: EquityCurveProps) {
  const rootRef = useRef<HTMLElement>(null)
  const pathRef = useRef<SVGPathElement>(null)
  const areaRef = useRef<SVGPathElement>(null)
  const [hover, setHover] = useState<Scaled | null>(null)
  const [chartW, setChartW] = useState<number>(VIEW_W)
  const containerRef = useRef<HTMLDivElement>(null)

  const geom = useMemo(() => buildGeom(points), [points])

  // Track container width to compute hover-snap accurately and to derive
  // a responsive font size for ticks.
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (entry) setChartW(entry.contentRect.width)
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // Stroke draw-in via dasharray on scroll.
  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const root = rootRef.current
    const path = pathRef.current
    const area = areaRef.current
    if (!root || !path) return

    if (reduced) {
      path.style.strokeDasharray = "none"
      path.style.strokeDashoffset = "0"
      if (area) area.style.opacity = "1"
      return
    }

    const len = path.getTotalLength()
    path.style.strokeDasharray = `${len}`
    path.style.strokeDashoffset = `${len}`
    if (area) area.style.opacity = "0"

    const ctx = gsap.context(() => {
      gsap.to(path, {
        strokeDashoffset: 0,
        duration: 2.0,
        ease: "power2.out",
        scrollTrigger: { trigger: root, start: "top 75%", once: true },
      })
      if (area) {
        gsap.to(area, {
          opacity: 1,
          duration: 1.4,
          ease: "power2.out",
          delay: 0.4,
          scrollTrigger: { trigger: root, start: "top 75%", once: true },
        })
      }
    }, root)

    return () => ctx.revert()
  }, [geom])

  const scaleX = chartW / VIEW_W

  function handleMove(e: React.MouseEvent<SVGSVGElement>) {
    const rect = e.currentTarget.getBoundingClientRect()
    const px = (e.clientX - rect.left) / rect.width * VIEW_W
    let nearest: Scaled | null = null
    let bestDx = Number.POSITIVE_INFINITY
    for (const s of geom.scaled) {
      const dx = Math.abs(s.x - px)
      if (dx < bestDx) {
        bestDx = dx
        nearest = s
      }
    }
    setHover(nearest)
  }

  const first = points[0]
  const last = points[points.length - 1]
  const totalReturn = first && last ? last.equity / first.equity - 1 : 0

  return (
    <section
      ref={rootRef}
      id="equity"
      className="relative px-6 py-20 md:py-28 border-t border-border/40"
      aria-labelledby="oracle-equity-title"
    >
      <div className="container mx-auto max-w-7xl">
        <div className="flex items-end justify-between flex-wrap gap-6 mb-10">
          <div>
            <div className="text-[11px] font-mono tracking-[0.3em] uppercase text-primary mb-3">
              Equity curve
            </div>
            <h2
              id="oracle-equity-title"
              className="text-3xl md:text-5xl font-semibold tracking-[-0.02em]"
            >
              From {formatUsd(initialCapital)} to {last ? formatUsd(last.equity) : "—"}.
            </h2>
          </div>
          <p className="text-sm text-muted-foreground max-w-sm">
            {points.length} monthly rebalance points · total return{" "}
            <span className="text-primary tabular-nums">
              {(totalReturn * 100).toFixed(2)}%
            </span>{" "}
            · source:{" "}
            <code className="font-mono text-primary">equity_curve.csv</code>.
          </p>
        </div>

        <div
          ref={containerRef}
          className="relative rounded-2xl border border-border/60 bg-card/30 backdrop-blur-xl p-3 md:p-6"
        >
          <svg
            role="img"
            aria-label={`Equity curve from ${first ? formatDateLong(first.date) : ""} to ${last ? formatDateLong(last.date) : ""}, starting at ${formatUsd(initialCapital)} and ending at ${last ? formatUsd(last.equity) : ""}.`}
            viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
            preserveAspectRatio="none"
            className="block w-full h-[260px] sm:h-[320px] md:h-[400px] select-none"
            onMouseMove={handleMove}
            onMouseLeave={() => setHover(null)}
          >
            {/* Y gridlines + labels */}
            <g>
              {geom.yTicks.map((t) => (
                <g key={`y-${t.y.toFixed(2)}`}>
                  <line
                    x1={PAD_LEFT}
                    x2={VIEW_W - PAD_RIGHT}
                    y1={t.y}
                    y2={t.y}
                    stroke="rgba(25,130,196,0.18)"
                    strokeWidth={1}
                    strokeDasharray="2 4"
                  />
                  <text
                    x={PAD_LEFT - 10}
                    y={t.y + 4}
                    textAnchor="end"
                    className="fill-[oklch(0.5_0_0)] font-mono"
                    style={{ fontSize: 11 }}
                  >
                    {formatUsdShort(t.value)}
                  </text>
                </g>
              ))}
            </g>

            {/* X tick labels */}
            <g>
              {geom.xTicks.map((t) => (
                <g key={`x-${t.x.toFixed(2)}`}>
                  <line
                    x1={t.x}
                    x2={t.x}
                    y1={VIEW_H - PAD_BOTTOM}
                    y2={VIEW_H - PAD_BOTTOM + 5}
                    stroke="rgba(25,130,196,0.35)"
                    strokeWidth={1}
                  />
                  <text
                    x={t.x}
                    y={VIEW_H - PAD_BOTTOM + 22}
                    textAnchor="middle"
                    className="fill-[oklch(0.5_0_0)] font-mono"
                    style={{ fontSize: 11 }}
                  >
                    {formatDateTick(t.point.date)}
                  </text>
                </g>
              ))}
            </g>

            {/* Area fill */}
            <defs>
              <linearGradient id="equity-area" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="rgba(25,130,196,0.42)" />
                <stop offset="100%" stopColor="rgba(25,130,196,0)" />
              </linearGradient>
            </defs>
            <path
              ref={areaRef}
              d={geom.area}
              fill="url(#equity-area)"
              style={{ opacity: 1 }}
            />

            {/* Initial-capital baseline */}
            {(() => {
              const lo = geom.scaled.length > 0 ? geom.minE : 0
              const hi = geom.scaled.length > 0 ? geom.maxE : 1
              const pad = (hi - lo) * 0.08
              const span = Math.max(1, hi + pad - (lo - pad))
              const baselineY =
                PAD_TOP +
                (1 - (initialCapital - (lo - pad)) / span) * geom.innerH
              if (
                baselineY < PAD_TOP ||
                baselineY > PAD_TOP + geom.innerH
              )
                return null
              return (
                <g>
                  <line
                    x1={PAD_LEFT}
                    x2={VIEW_W - PAD_RIGHT}
                    y1={baselineY}
                    y2={baselineY}
                    stroke="rgba(255,255,255,0.18)"
                    strokeDasharray="3 5"
                    strokeWidth={1}
                  />
                  <text
                    x={VIEW_W - PAD_RIGHT - 8}
                    y={baselineY - 6}
                    textAnchor="end"
                    className="fill-[oklch(0.65_0_0)] font-mono"
                    style={{ fontSize: 10 }}
                  >
                    Initial · {formatUsdShort(initialCapital)}
                  </text>
                </g>
              )
            })()}

            {/* Equity polyline */}
            <path
              ref={pathRef}
              d={geom.path}
              fill="none"
              stroke="#1982C4"
              strokeWidth={2.5}
              strokeLinejoin="round"
              strokeLinecap="round"
              style={{
                filter: "drop-shadow(0 0 8px rgba(25,130,196,0.6))",
              }}
            />

            {/* Hover crosshair + dot */}
            {hover && (
              <g>
                <line
                  x1={hover.x}
                  x2={hover.x}
                  y1={PAD_TOP}
                  y2={VIEW_H - PAD_BOTTOM}
                  stroke="rgba(25,130,196,0.5)"
                  strokeWidth={1}
                />
                <circle
                  cx={hover.x}
                  cy={hover.y}
                  r={5}
                  fill="oklch(0.012 0 0)"
                  stroke="#1982C4"
                  strokeWidth={2.5}
                />
              </g>
            )}
          </svg>

          {/* Tooltip overlay (HTML, positioned in container coords) */}
          {hover && (
            <div
              className="pointer-events-none absolute rounded-lg border border-primary/40 bg-background/90 backdrop-blur-md px-3 py-2 text-xs font-mono"
              style={{
                left: Math.min(
                  Math.max(hover.x * scaleX + 12, 12),
                  chartW - 180,
                ),
                top: Math.max(hover.y * (chartW / VIEW_W) - 8, 12),
              }}
            >
              <div className="text-muted-foreground tracking-[0.18em] uppercase text-[10px]">
                {formatDateLong(hover.point.date)}
              </div>
              <div className="mt-1 text-primary text-base tabular-nums">
                {formatUsd(hover.point.equity)}
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
