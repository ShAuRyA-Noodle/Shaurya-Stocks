"use client"

import { useEffect, useRef } from "react"
import Lenis from "lenis"
import { gsap } from "gsap"
import { ScrollTrigger } from "gsap/ScrollTrigger"

if (typeof window !== "undefined") {
  gsap.registerPlugin(ScrollTrigger)
}

export function SmoothScroll({ children }: { children: React.ReactNode }) {
  const lenisRef = useRef<Lenis | null>(null)

  useEffect(() => {
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (prefersReduced) return

    const lenis = new Lenis({
      duration: 1.15,
      easing: (t: number) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      wheelMultiplier: 1,
      touchMultiplier: 1.4,
      syncTouch: true,
      syncTouchLerp: 0.09,
    })
    lenisRef.current = lenis

    lenis.on("scroll", ScrollTrigger.update)

    const tickerFn = (time: number) => lenis.raf(time * 1000)
    gsap.ticker.add(tickerFn)
    gsap.ticker.lagSmoothing(0)

    return () => {
      gsap.ticker.remove(tickerFn)
      lenis.destroy()
      lenisRef.current = null
    }
  }, [])

  return <>{children}</>
}
