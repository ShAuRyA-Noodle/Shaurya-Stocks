// Vibrant Summer palette: Steel Blue #1982C4 · Yellow Green #8AC926
// Coral #FF595E · Golden Pollen #FFCA3A · Dusty Grape #6A4C93

export function glassPanel(className?: string) {
  return `bg-card/40 backdrop-blur-3xl border border-border/50 shadow-[0_0_0_1px_rgba(25,130,196,0.1),0_8px_32px_rgba(0,0,0,0.5)] ${className || ""}`
}

export function glassPanelHover(className?: string) {
  return `bg-card/40 backdrop-blur-3xl border border-border/50 shadow-[0_0_0_1px_rgba(25,130,196,0.1),0_8px_32px_rgba(0,0,0,0.5)] transition-all duration-300 hover:border-primary/50 hover:shadow-[0_0_0_1px_rgba(25,130,196,0.3),0_12px_48px_rgba(0,0,0,0.7),0_0_24px_rgba(25,130,196,0.15)] hover:-translate-y-0.5 ${className || ""}`
}

export function neonGlowBlue(className?: string) {
  return `shadow-[0_0_10px_rgba(25,130,196,0.4),0_0_20px_rgba(25,130,196,0.25),0_0_40px_rgba(25,130,196,0.12)] ${className || ""}`
}

// Legacy alias kept for backward compat
export const neonGlowCyan = neonGlowBlue

export function neonGlowGreen(className?: string) {
  return `shadow-[0_0_10px_rgba(138,201,38,0.4),0_0_20px_rgba(138,201,38,0.25),0_0_40px_rgba(138,201,38,0.12)] ${className || ""}`
}

export function neonGlowRed(className?: string) {
  return `shadow-[0_0_10px_rgba(255,89,94,0.4),0_0_20px_rgba(255,89,94,0.25),0_0_40px_rgba(255,89,94,0.12)] ${className || ""}`
}

export function neonGlowGrape(className?: string) {
  return `shadow-[0_0_10px_rgba(106,76,147,0.4),0_0_20px_rgba(106,76,147,0.25),0_0_40px_rgba(106,76,147,0.12)] ${className || ""}`
}

export function neonGlowGold(className?: string) {
  return `shadow-[0_0_10px_rgba(255,202,58,0.4),0_0_20px_rgba(255,202,58,0.25),0_0_40px_rgba(255,202,58,0.12)] ${className || ""}`
}
