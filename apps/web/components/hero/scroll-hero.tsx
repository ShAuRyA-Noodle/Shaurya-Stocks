"use client"

import { useEffect, useRef } from "react"
import Link from "next/link"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"
import { ArrowRight, Sparkles } from "lucide-react"
import SplitType from "split-type"
import { glassPanel } from "@/lib/cn-utils"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

export function ScrollHero() {
  const rootRef = useRef<HTMLElement>(null)
  const headlineRef = useRef<HTMLHeadingElement>(null)
  const subRef = useRef<HTMLParagraphElement>(null)
  const auraRef = useRef<HTMLDivElement>(null)
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    const root = rootRef.current
    const headline = headlineRef.current
    const sub = subRef.current
    if (!root || !headline || !sub) return

    const split = new SplitType(headline, { types: "chars,words", tagName: "span" })
    const subSplit = new SplitType(sub, { types: "lines", tagName: "span" })

    const ctx = gsap.context(() => {
      gsap.set(split.chars, { yPercent: 110, rotateX: -60, opacity: 0 })
      gsap.set(subSplit.lines, { y: 32, opacity: 0 })

      const intro = gsap.timeline({ defaults: { ease: "expo.out" } })
      intro.to(split.chars, {
        yPercent: 0,
        rotateX: 0,
        opacity: 1,
        duration: 1.2,
        stagger: 0.028,
      })
      intro.to(
        subSplit.lines,
        { y: 0, opacity: 1, duration: 0.9, stagger: 0.08 },
        "-=0.7",
      )
      intro.from(
        ".hero-cta",
        { y: 18, opacity: 0, duration: 0.7, stagger: 0.08 },
        "-=0.5",
      )
      intro.from(".hero-badge", { y: -16, opacity: 0, duration: 0.6 }, 0.1)

      if (!reduced) {
        // Parallax scrub — headline drifts up, aura blooms, grid recedes.
        gsap.to(headline, {
          yPercent: -28,
          scale: 0.92,
          filter: "blur(1px)",
          ease: "none",
          scrollTrigger: {
            trigger: root,
            start: "top top",
            end: "bottom top",
            scrub: 0.6,
          },
        })
        gsap.to(sub, {
          yPercent: -40,
          opacity: 0.35,
          ease: "none",
          scrollTrigger: {
            trigger: root,
            start: "top top",
            end: "bottom top",
            scrub: 0.6,
          },
        })
        if (auraRef.current) {
          gsap.to(auraRef.current, {
            scale: 1.35,
            opacity: 0.35,
            ease: "none",
            scrollTrigger: {
              trigger: root,
              start: "top top",
              end: "bottom top",
              scrub: true,
            },
          })
        }
        if (gridRef.current) {
          gsap.to(gridRef.current, {
            yPercent: 18,
            opacity: 0.25,
            ease: "none",
            scrollTrigger: {
              trigger: root,
              start: "top top",
              end: "bottom top",
              scrub: true,
            },
          })
        }
      }
    }, root)

    // Mouse-parallax aura (GPU transform only, no layout).
    let raf = 0
    let tx = 0
    let ty = 0
    const onMouse = (e: MouseEvent) => {
      const cx = window.innerWidth / 2
      const cy = window.innerHeight / 2
      tx = (e.clientX - cx) / cx
      ty = (e.clientY - cy) / cy
      if (!raf) {
        raf = requestAnimationFrame(() => {
          raf = 0
          if (auraRef.current) {
            auraRef.current.style.transform = `translate3d(${tx * 24}px, ${ty * 24}px, 0)`
          }
          if (gridRef.current) {
            gridRef.current.style.transform = `translate3d(${tx * -12}px, ${ty * -12}px, 0) perspective(800px) rotateX(60deg)`
          }
        })
      }
    }
    window.addEventListener("mousemove", onMouse, { passive: true })

    return () => {
      window.removeEventListener("mousemove", onMouse)
      if (raf) cancelAnimationFrame(raf)
      ctx.revert()
      split.revert()
      subSplit.revert()
    }
  }, [])

  return (
    <section
      ref={rootRef}
      className="relative min-h-[110vh] flex items-center justify-center overflow-hidden isolate"
    >
      {/* Deep radial aura */}
      <div
        ref={auraRef}
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 will-change-transform"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 42%, rgba(0,240,255,0.22) 0%, rgba(0,240,255,0.04) 40%, transparent 70%)",
        }}
      />

      {/* Receding horizon grid */}
      <div
        ref={gridRef}
        aria-hidden
        className="pointer-events-none absolute inset-x-0 bottom-[-20vh] h-[80vh] -z-10 will-change-transform opacity-50"
        style={{
          background:
            "linear-gradient(transparent 0%, rgba(0,240,255,0.12) 100%), " +
            "repeating-linear-gradient(0deg, transparent 0 39px, rgba(0,240,255,0.22) 39px 40px), " +
            "repeating-linear-gradient(90deg, transparent 0 39px, rgba(0,240,255,0.22) 39px 40px)",
          transform: "perspective(800px) rotateX(60deg)",
          transformOrigin: "50% 100%",
          maskImage:
            "linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,1) 55%, transparent 100%)",
        }}
      />

      {/* Floating orbs */}
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        <span className="absolute top-1/4 left-1/5 w-56 h-56 rounded-full blur-3xl opacity-30 bg-[var(--color-primary)] animate-pulse-glow" />
        <span className="absolute bottom-1/4 right-1/5 w-72 h-72 rounded-full blur-3xl opacity-25 bg-[var(--color-profit)] animate-pulse-glow" />
      </div>

      {/* Content */}
      <div className="relative z-10 container mx-auto px-6 text-center pt-20">
        <div
          className={`hero-badge inline-flex items-center gap-2 ${glassPanel()} px-4 py-2 rounded-full mb-10`}
        >
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="text-xs md:text-sm font-mono tracking-[0.2em] uppercase text-primary">
            Real-time · AI · Walk-forward verified
          </span>
        </div>

        <h1
          ref={headlineRef}
          className="text-[clamp(3.5rem,12vw,10rem)] font-bold tracking-[-0.035em] leading-[0.85] text-gradient-cyan will-change-transform [perspective:1000px]"
          style={{ textShadow: "0 0 60px rgba(0,240,255,0.25)" }}
        >
          ORACLE
        </h1>

        <p
          ref={subRef}
          className="mt-8 text-base md:text-2xl text-muted-foreground max-w-3xl mx-auto leading-relaxed font-light"
        >
          The definitive AI-driven quantitative trading terminal.
          Neural ensemble predictions meet institutional-grade execution.
          Built on real market data. Verified by deflated Sharpe.
        </p>

        <div className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="#terminal"
            className="hero-cta group inline-flex items-center gap-2 rounded-full bg-primary text-primary-foreground px-8 py-4 text-base font-semibold shadow-[0_0_40px_rgba(0,240,255,0.35)] hover:shadow-[0_0_80px_rgba(0,240,255,0.55)] transition-shadow"
          >
            Enter Terminal
            <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-1" />
          </Link>
          <Link
            href="#philosophy"
            className="hero-cta inline-flex items-center gap-2 rounded-full border border-primary/30 hover:border-primary/70 px-8 py-4 text-base font-semibold transition-colors"
          >
            The Method
          </Link>
        </div>

        {/* Scroll cue */}
        <div className="hero-cta absolute bottom-10 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 text-xs font-mono uppercase tracking-[0.3em] text-muted-foreground">
          <span>Scroll</span>
          <span className="relative block w-px h-14 bg-gradient-to-b from-primary/80 to-transparent overflow-hidden">
            <span className="absolute inset-x-0 top-0 h-4 bg-primary animate-[scroll-dot_2.4s_ease-in-out_infinite]" />
          </span>
        </div>
      </div>

      {/* Fade to next section */}
      <div className="pointer-events-none absolute bottom-0 inset-x-0 h-48 bg-gradient-to-b from-transparent to-background" />
    </section>
  )
}
