import { ScrollHero } from "@/components/hero/scroll-hero"
import { PinnedFeatures } from "@/components/sections/pinned-features"
import { HorizontalScroll } from "@/components/sections/horizontal-scroll"
import { Manifesto } from "@/components/sections/manifesto"
import { Marquee } from "@/components/sections/marquee"
import { StatsScroll } from "@/components/sections/stats-scroll"
import { LiveSignals } from "@/components/sections/live-signals"
import { FooterScene } from "@/components/sections/footer-scene"

export default function Page() {
  return (
    <main id="oracle-main" className="relative">
      <ScrollHero />
      <Marquee />
      <PinnedFeatures />
      <HorizontalScroll />
      <Manifesto />
      <StatsScroll />
      <LiveSignals />
      <div id="build" />
      <FooterScene />
    </main>
  )
}
