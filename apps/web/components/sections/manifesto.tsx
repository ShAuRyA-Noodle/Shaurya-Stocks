"use client"

import { useEffect, useRef } from "react"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"
import SplitType from "split-type"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

const LINES = [
  "No fake data.",
  "No synthetic paths.",
  "Real providers. Real markets.",
  "Verified by deflated Sharpe.",
  "Or it does not ship.",
]

export function Manifesto() {
  const rootRef = useRef<HTMLElement>(null)
  const linesRef = useRef<HTMLParagraphElement[]>([])

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const root = rootRef.current
    if (!root) return

    const splits: SplitType[] = []
    const ctx = gsap.context(() => {
      linesRef.current.forEach((el) => {
        if (!el) return
        const split = new SplitType(el, { types: "words,chars", tagName: "span" })
        splits.push(split)
        if (reduced) {
          gsap.set(split.chars, { opacity: 1 })
          return
        }
        gsap.fromTo(
          split.chars,
          { opacity: 0.08, filter: "blur(4px)", y: 18 },
          {
            opacity: 1,
            filter: "blur(0px)",
            y: 0,
            stagger: 0.018,
            ease: "power2.out",
            duration: 0.6,
            scrollTrigger: {
              trigger: el,
              start: "top 85%",
              end: "top 35%",
              scrub: 0.5,
            },
          },
        )
      })
    }, root)

    return () => {
      ctx.revert()
      splits.forEach((s) => s.revert())
    }
  }, [])

  return (
    <section
      ref={rootRef}
      className="relative py-[22vh] px-6 bg-background overflow-hidden"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,240,255,0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(0,240,255,0.4) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          maskImage: "radial-gradient(60% 60% at 50% 50%, #000 0%, transparent 80%)",
        }}
      />
      <div className="container mx-auto max-w-5xl">
        <div className="text-xs font-mono tracking-[0.3em] uppercase text-primary mb-10">
          The Rule
        </div>
        {LINES.map((t, i) => (
          <p
            key={i}
            ref={(el) => {
              if (el) linesRef.current[i] = el
            }}
            className="text-[clamp(1.9rem,6vw,5.5rem)] font-semibold leading-[1.05] tracking-[-0.025em] mb-4 text-foreground"
          >
            {t}
          </p>
        ))}
      </div>
    </section>
  )
}
