"use client"

import { useEffect, useRef } from "react"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

const WORDS = [
  "DEFLATED SHARPE",
  "CSCV · PBO",
  "WALK-FORWARD",
  "KILL-SWITCH",
  "REAL DATA ONLY",
  "PROMETHEUS",
  "ALPACA IEX",
  "REDIS PUB/SUB",
  "SSE STREAMING",
  "LIGHTGBM",
  "POSTGRES 16",
  "FASTAPI",
]

export function Marquee() {
  const rootRef = useRef<HTMLDivElement>(null)
  const aRef = useRef<HTMLDivElement>(null)
  const bRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (reduced) return
    const ctx = gsap.context(() => {
      // Two tracks in opposite directions; velocity biased by scroll direction.
      const tweens = [
        gsap.to(aRef.current, { xPercent: -50, ease: "none", duration: 40, repeat: -1 }),
        gsap.to(bRef.current, { xPercent: 50, ease: "none", duration: 50, repeat: -1 }),
      ]

      const st = ScrollTrigger.create({
        trigger: rootRef.current,
        start: "top bottom",
        end: "bottom top",
        onUpdate(self) {
          const v = self.getVelocity() / 2500
          const ts = 1 + Math.min(Math.abs(v), 3)
          tweens.forEach((t, i) => {
            const dir = self.direction === 1 ? 1 : -1
            t.timeScale((i === 0 ? -1 : 1) * dir * ts)
          })
        },
      })

      return () => {
        st.kill()
        tweens.forEach((t) => t.kill())
      }
    }, rootRef)

    return () => ctx.revert()
  }, [])

  const row = (ref: React.RefObject<HTMLDivElement | null>, dup = 0) => (
    <div
      ref={ref}
      className="flex whitespace-nowrap will-change-transform"
      style={dup ? { transform: "translateX(-50%)" } : undefined}
    >
      {[0, 1].map((k) => (
        <div key={k} className="flex shrink-0">
          {WORDS.map((w, i) => (
            <span
              key={`${k}-${i}`}
              className="px-10 py-2 text-[clamp(2rem,7vw,5.5rem)] font-semibold tracking-[-0.02em] text-foreground/80"
            >
              {w}
              <span className="mx-8 text-primary">•</span>
            </span>
          ))}
        </div>
      ))}
    </div>
  )

  return (
    <div
      ref={rootRef}
      className="relative overflow-hidden border-y border-border/60 py-6 bg-background"
      style={{
        maskImage:
          "linear-gradient(to right, transparent, #000 8%, #000 92%, transparent)",
      }}
    >
      {row(aRef)}
      <div className="h-2" />
      {row(bRef, 1)}
    </div>
  )
}
