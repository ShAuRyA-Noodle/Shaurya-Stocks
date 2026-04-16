"use client"

import { useEffect, useRef, useState } from "react"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"
import Link from "next/link"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

const LINKS = [
  { href: "#philosophy", label: "Method" },
  { href: "#terminal", label: "Signals" },
  { href: "#build", label: "Build" },
]

export function TopNav() {
  const ref = useRef<HTMLElement>(null)
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const st = ScrollTrigger.create({
      start: 0,
      end: "max",
      onUpdate: (self) => setProgress(self.progress),
    })
    const topTrigger = ScrollTrigger.create({
      start: 40,
      end: 99999,
      onUpdate: (self) => {
        el.dataset.stuck = self.isActive ? "1" : "0"
      },
    })
    return () => {
      st.kill()
      topTrigger.kill()
    }
  }, [])

  return (
    <header
      ref={ref}
      data-stuck="0"
      className="fixed top-0 inset-x-0 z-50 transition-[background,backdrop-filter,border-color] duration-300 data-[stuck=1]:bg-background/60 data-[stuck=1]:backdrop-blur-xl data-[stuck=1]:border-b data-[stuck=1]:border-border/60"
    >
      <div className="container mx-auto max-w-7xl px-6 h-16 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 text-sm font-mono tracking-[0.3em] uppercase text-foreground"
        >
          <span className="relative inline-flex w-2 h-2 rounded-full bg-primary">
            <span className="absolute inset-0 rounded-full bg-primary animate-ping opacity-70" />
          </span>
          Oracle
        </Link>
        <nav className="hidden md:flex items-center gap-8 text-sm font-mono tracking-[0.15em] uppercase text-muted-foreground">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="hover:text-foreground transition-colors"
            >
              {l.label}
            </a>
          ))}
        </nav>
        <Link
          href="#terminal"
          className="rounded-full border border-primary/40 px-4 py-2 text-xs font-mono uppercase tracking-[0.2em] text-primary hover:bg-primary/10 transition-colors"
        >
          Launch →
        </Link>
      </div>
      <div className="relative h-[2px] bg-border/50">
        <div
          className="absolute inset-y-0 left-0 bg-primary origin-left"
          style={{ width: `${progress * 100}%`, willChange: "width" }}
        />
      </div>
    </header>
  )
}
