"use client"

import { useEffect, useRef } from "react"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

const STATS = [
  { value: 8, suffix: "", label: "Sprints delivered" },
  { value: 67, suffix: "", label: "Unit tests · green" },
  { value: 11, suffix: "", label: "Real provider feeds" },
  { value: 100, suffix: "%", label: "Type-checked, mypy --strict" },
  { value: 0, suffix: "", label: "Synthetic data paths" },
]

export function StatsScroll() {
  const rootRef = useRef<HTMLElement>(null)

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const root = rootRef.current
    if (!root) return

    const ctx = gsap.context(() => {
      const nums = gsap.utils.toArray<HTMLElement>(".stat-num")
      nums.forEach((el) => {
        const target = Number(el.dataset.target || "0")
        const suffix = el.dataset.suffix || ""
        if (reduced) {
          el.textContent = `${target}${suffix}`
          return
        }
        const o = { v: 0 }
        el.textContent = `0${suffix}`
        ScrollTrigger.create({
          trigger: el,
          start: "top 85%",
          once: true,
          onEnter: () =>
            gsap.to(o, {
              v: target,
              duration: 1.6,
              ease: "power3.out",
              onUpdate: () => {
                el.textContent = `${Math.round(o.v)}${suffix}`
              },
            }),
        })
      })

      if (!reduced) {
        gsap.fromTo(
          ".stat-card",
          { y: 40, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: 0.8,
            ease: "power3.out",
            stagger: 0.08,
            scrollTrigger: { trigger: root, start: "top 70%" },
          },
        )
      }
    }, root)

    return () => ctx.revert()
  }, [])

  return (
    <section
      ref={rootRef}
      className="relative py-32 px-6 bg-background border-t border-border/40"
    >
      <div className="container mx-auto max-w-7xl">
        <div className="flex items-end justify-between flex-wrap gap-6 mb-16">
          <div>
            <div className="text-xs font-mono tracking-[0.3em] uppercase text-primary mb-3">
              By the numbers
            </div>
            <h2 className="text-3xl md:text-5xl font-semibold tracking-[-0.02em]">
              The shape of the build.
            </h2>
          </div>
          <p className="text-sm text-muted-foreground max-w-sm">
            Measured from the commit log, not the pitch deck.
          </p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {STATS.map((s) => (
            <div
              key={s.label}
              className="stat-card rounded-2xl border border-border/60 bg-card/40 backdrop-blur-xl p-6 md:p-8 hover:border-primary/50 transition-colors"
            >
              <div
                className="stat-num text-4xl md:text-5xl font-semibold tracking-[-0.03em] text-primary tabular-nums"
                data-target={s.value}
                data-suffix={s.suffix}
              >
                {s.value}
                {s.suffix}
              </div>
              <div className="mt-3 text-xs font-mono uppercase tracking-[0.18em] text-muted-foreground">
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
