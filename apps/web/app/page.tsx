import { HeroSection } from "@/components/hero-section"
import { CommandDock } from "@/components/command-dock"
import { CommandPalette } from "@/components/command-palette"
import { Dashboard } from "@/components/dashboard"
import { TradingTerminal } from "@/components/trading-terminal"

export default function Page() {
  return (
    <main className="relative">
      <HeroSection />
      <Dashboard />
      <TradingTerminal />
      <CommandDock />
      <CommandPalette />
    </main>
  )
}
