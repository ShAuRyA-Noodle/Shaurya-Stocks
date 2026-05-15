import { ScrollHero } from "@/components/hero/scroll-hero"
import { PinnedFeatures } from "@/components/sections/pinned-features"
import { HorizontalScroll } from "@/components/sections/horizontal-scroll"
import { Manifesto } from "@/components/sections/manifesto"
import { Marquee } from "@/components/sections/marquee"
import { StatsScroll } from "@/components/sections/stats-scroll"
import { LiveSignals } from "@/components/sections/live-signals"
import { FooterScene } from "@/components/sections/footer-scene"
import { loadStaticSignals } from "@/lib/oracle/load-artifacts"

export default function Page() {
  // Load real ML predictions from static artifact (quant ml predict output).
  // Generated from 2026 LightGBM model trained on real Alpaca 2018-2026 data.
  // Used as fallback when the live API is offline.
  const staticSignals = loadStaticSignals()

  return (
    <main id="oracle-main" className="relative">
      <ScrollHero />
      <Marquee />
      <PinnedFeatures />
      <HorizontalScroll />
      <Manifesto />
      <StatsScroll />
      <LiveSignals staticSignals={staticSignals} />
      <div id="build" />
      <FooterScene />
    </main>
  )
}
