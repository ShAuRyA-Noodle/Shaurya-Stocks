export function glassPanel(className?: string) {
  return `bg-card/40 backdrop-blur-3xl border border-border/50 shadow-[0_0_0_1px_rgba(0,240,255,0.1),0_8px_32px_rgba(0,0,0,0.5)] ${className || ""}`
}

export function glassPanelHover(className?: string) {
  return `bg-card/40 backdrop-blur-3xl border border-border/50 shadow-[0_0_0_1px_rgba(0,240,255,0.1),0_8px_32px_rgba(0,0,0,0.5)] transition-all duration-300 hover:border-primary/50 hover:shadow-[0_0_0_1px_rgba(0,240,255,0.3),0_12px_48px_rgba(0,0,0,0.7),0_0_24px_rgba(0,240,255,0.15)] hover:-translate-y-0.5 ${className || ""}`
}

export function neonGlowCyan(className?: string) {
  return `shadow-[0_0_10px_rgba(0,240,255,0.3),0_0_20px_rgba(0,240,255,0.2),0_0_30px_rgba(0,240,255,0.1)] ${className || ""}`
}

export function neonGlowGreen(className?: string) {
  return `shadow-[0_0_10px_rgba(57,255,20,0.3),0_0_20px_rgba(57,255,20,0.2),0_0_30px_rgba(57,255,20,0.1)] ${className || ""}`
}

export function neonGlowRed(className?: string) {
  return `shadow-[0_0_10px_rgba(255,0,60,0.3),0_0_20px_rgba(255,0,60,0.2),0_0_30px_rgba(255,0,60,0.1)] ${className || ""}`
}
