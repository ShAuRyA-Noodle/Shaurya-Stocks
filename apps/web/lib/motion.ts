"use client"

import { useEffect } from "react"

export function useReducedMotion() {
  if (typeof window === "undefined") return false
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
}

export function usePageVisibility(onChange: (visible: boolean) => void) {
  useEffect(() => {
    const handler = () => onChange(document.visibilityState === "visible")
    document.addEventListener("visibilitychange", handler)
    return () => document.removeEventListener("visibilitychange", handler)
  }, [onChange])
}
