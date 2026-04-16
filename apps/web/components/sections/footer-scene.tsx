"use client"

import { useEffect, useRef } from "react"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"
import SplitType from "split-type"
import { Github, Globe, Mail } from "lucide-react"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

export function FooterScene() {
  const rootRef = useRef<HTMLElement>(null)
  const bigRef = useRef<HTMLHeadingElement>(null)
  const ctaRef = useRef<HTMLAnchorElement>(null)

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const root = rootRef.current
    const big = bigRef.current
    if (!root || !big) return

    const split = new SplitType(big, { types: "chars", tagName: "span" })

    const ctx = gsap.context(() => {
      if (!reduced) {
        gsap.fromTo(
          split.chars,
          { yPercent: 110, rotate: -8 },
          {
            yPercent: 0,
            rotate: 0,
            duration: 1.1,
            ease: "expo.out",
            stagger: 0.02,
            scrollTrigger: { trigger: root, start: "top 70%" },
          },
        )
      }

      // Magnetic CTA
      const cta = ctaRef.current
      if (cta && !reduced) {
        const handleMove = (e: MouseEvent) => {
          const rect = cta.getBoundingClientRect()
          const x = e.clientX - rect.left - rect.width / 2
          const y = e.clientY - rect.top - rect.height / 2
          gsap.to(cta, { x: x * 0.2, y: y * 0.2, duration: 0.4, ease: "power3.out" })
        }
        const handleLeave = () =>
          gsap.to(cta, { x: 0, y: 0, duration: 0.6, ease: "elastic.out(1,0.4)" })
        cta.addEventListener("mousemove", handleMove)
        cta.addEventListener("mouseleave", handleLeave)
      }
    }, root)

    return () => {
      ctx.revert()
      split.revert()
    }
  }, [])

  return (
    <section
      ref={rootRef}
      className="relative py-40 px-6 overflow-hidden border-t border-border/40"
    >
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(80% 60% at 50% 100%, rgba(0,240,255,0.18), transparent 70%)",
        }}
      />
      <div className="container mx-auto max-w-6xl text-center relative">
        <div className="text-xs font-mono tracking-[0.3em] uppercase text-primary mb-6">
          Enter
        </div>
        <h2
          ref={bigRef}
          className="text-[clamp(3rem,13vw,11rem)] font-semibold leading-[0.9] tracking-[-0.035em] text-primary [perspective:1000px] overflow-hidden"
          style={{
            textShadow:
              "0 0 60px rgba(0,240,255,0.35), 0 0 120px rgba(0,240,255,0.18)",
          }}
        >
          RUN THE ORACLE
        </h2>
        <a
          ref={ctaRef}
          href="#terminal"
          className="inline-flex items-center gap-2 mt-10 rounded-full bg-primary text-primary-foreground px-10 py-5 text-base font-semibold shadow-[0_0_40px_rgba(0,240,255,0.35)] hover:shadow-[0_0_100px_rgba(0,240,255,0.5)] transition-shadow will-change-transform"
        >
          Launch Terminal →
        </a>

        <div className="mt-24 grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          <div className="rounded-2xl border border-border/60 bg-card/40 backdrop-blur-xl p-6">
            <Globe className="w-5 h-5 text-primary mb-3" />
            <div className="text-sm font-mono text-muted-foreground">
              Self-hostable. Stateless API. Postgres 16 + Redis.
            </div>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/40 backdrop-blur-xl p-6">
            <Github className="w-5 h-5 text-primary mb-3" />
            <div className="text-sm font-mono text-muted-foreground">
              <a
                href="https://github.com/ShAuRyA-Noodle/Shaurya-Stocks"
                className="hover:text-primary"
              >
                ShAuRyA-Noodle / Shaurya-Stocks
              </a>
            </div>
          </div>
          <div className="rounded-2xl border border-border/60 bg-card/40 backdrop-blur-xl p-6">
            <Mail className="w-5 h-5 text-primary mb-3" />
            <div className="text-sm font-mono text-muted-foreground">
              Built by Shaurya · no fake data · brutal honesty by default.
            </div>
          </div>
        </div>

        <div className="mt-16 flex items-center justify-between text-[11px] font-mono uppercase tracking-[0.25em] text-muted-foreground">
          <span>© 2026 Oracle</span>
          <span>Deflated Sharpe verified · PBO monitored</span>
        </div>
      </div>
    </section>
  )
}
