"use client"

import type React from "react"

import { BarChart3, TrendingUp, Zap, Settings, PieChart, Sparkles } from "lucide-react"
import { Button } from "@/components/ui/button"
import { glassPanel, neonGlowCyan } from "@/lib/cn-utils"

export function CommandDock() {
  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50">
      <div className={`${glassPanel()} ${neonGlowCyan()} px-3 py-2 rounded-2xl flex items-center gap-2`}>
        <DockButton icon={<BarChart3 className="w-5 h-5" />} label="Dashboard" active />
        <DockButton icon={<TrendingUp className="w-5 h-5" />} label="Signals" />
        <DockButton icon={<Zap className="w-5 h-5" />} label="Neural Net" />
        <DockButton icon={<PieChart className="w-5 h-5" />} label="Portfolio" />
        <div className="w-px h-8 bg-border/50 mx-1" />
        <DockButton icon={<Sparkles className="w-5 h-5" />} label="AI Assist" />
        <DockButton icon={<Settings className="w-5 h-5" />} label="Settings" />
      </div>
    </div>
  )
}

function DockButton({
  icon,
  label,
  active = false,
}: {
  icon: React.ReactNode
  label: string
  active?: boolean
}) {
  return (
    <Button
      variant="ghost"
      size="icon"
      className={`relative group h-12 w-12 rounded-xl transition-all duration-300 hover:scale-110 ${
        active ? `bg-primary/20 text-primary ${neonGlowCyan()}` : "text-muted-foreground hover:text-foreground"
      }`}
      title={label}
    >
      {icon}
      <span
        className={`absolute -top-10 left-1/2 -translate-x-1/2 ${glassPanel()} px-2 py-1 rounded text-xs font-mono whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none`}
      >
        {label}
      </span>
    </Button>
  )
}
