"use client"

import type React from "react"

import { useEffect, useState } from "react"
import { Search, TrendingUp, BarChart3, Settings, Zap, DollarSign } from "lucide-react"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { glassPanel } from "@/lib/cn-utils"

interface CommandItem {
  id: string
  title: string
  category: string
  icon: React.ReactNode
  action: () => void
}

export function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState("")

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((open) => !open)
      }
    }
    document.addEventListener("keydown", down)
    return () => document.removeEventListener("keydown", down)
  }, [])

  const commands: CommandItem[] = [
    {
      id: "aapl",
      title: "AAPL - Apple Inc.",
      category: "Stocks",
      icon: <TrendingUp className="w-4 h-4 text-chart-2" />,
      action: () => console.log("Navigate to AAPL"),
    },
    {
      id: "tsla",
      title: "TSLA - Tesla Inc.",
      category: "Stocks",
      icon: <TrendingUp className="w-4 h-4 text-chart-2" />,
      action: () => console.log("Navigate to TSLA"),
    },
    {
      id: "spy",
      title: "SPY - S&P 500 ETF",
      category: "Stocks",
      icon: <TrendingUp className="w-4 h-4 text-chart-2" />,
      action: () => console.log("Navigate to SPY"),
    },
    {
      id: "neural-network",
      title: "Neural Network Performance",
      category: "Models",
      icon: <Zap className="w-4 h-4 text-primary" />,
      action: () => console.log("View neural network"),
    },
    {
      id: "signals",
      title: "Active Signals",
      category: "Dashboard",
      icon: <BarChart3 className="w-4 h-4 text-chart-4" />,
      action: () => console.log("View signals"),
    },
    {
      id: "portfolio",
      title: "Portfolio Overview",
      category: "Dashboard",
      icon: <DollarSign className="w-4 h-4 text-chart-2" />,
      action: () => console.log("View portfolio"),
    },
    {
      id: "settings",
      title: "System Settings",
      category: "Settings",
      icon: <Settings className="w-4 h-4 text-muted-foreground" />,
      action: () => console.log("Open settings"),
    },
  ]

  const filteredCommands = commands.filter(
    (cmd) =>
      cmd.title.toLowerCase().includes(search.toLowerCase()) ||
      cmd.category.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className={`${glassPanel()} border-primary/20 p-0 max-w-2xl overflow-hidden`}>
        {/* Search Input */}
        <div className="flex items-center border-b border-border/50 px-4 py-3">
          <Search className="w-5 h-5 text-muted-foreground mr-3" />
          <Input
            placeholder="Search stocks, models, or navigate..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-lg placeholder:text-muted-foreground"
            autoFocus
          />
          <kbd className={`ml-auto ${glassPanel()} px-2 py-1 text-xs font-mono rounded`}>ESC</kbd>
        </div>

        {/* Command List */}
        <div className="max-h-96 overflow-y-auto p-2">
          {filteredCommands.length === 0 ? (
            <div className="py-12 text-center text-muted-foreground">No results found.</div>
          ) : (
            <div className="space-y-1">
              {filteredCommands.map((cmd) => (
                <button
                  key={cmd.id}
                  onClick={() => {
                    cmd.action()
                    setOpen(false)
                  }}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-accent/50 transition-colors text-left group"
                >
                  <div
                    className={`flex items-center justify-center w-8 h-8 rounded-md ${glassPanel()} group-hover:shadow-[0_0_10px_rgba(0,240,255,0.3),0_0_20px_rgba(0,240,255,0.2)] transition-all`}
                  >
                    {cmd.icon}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-foreground group-hover:text-primary transition-colors">
                      {cmd.title}
                    </div>
                    <div className="text-xs text-muted-foreground font-mono">{cmd.category}</div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer hint */}
        <div className="border-t border-border/50 px-4 py-3 flex items-center justify-between bg-card/30">
          <div className="flex items-center gap-2 text-xs text-muted-foreground font-mono">
            <kbd className={`${glassPanel()} px-1.5 py-0.5 rounded`}>↑↓</kbd>
            <span>Navigate</span>
            <kbd className={`${glassPanel()} px-1.5 py-0.5 rounded`}>↵</kbd>
            <span>Select</span>
          </div>
          <div className="text-xs text-muted-foreground font-mono">Cmd+K to toggle</div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
