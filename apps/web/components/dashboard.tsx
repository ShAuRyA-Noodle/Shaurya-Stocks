"use client"

import { MarketOverview } from "@/components/market-overview"
import { NeuralNetworkViz } from "@/components/neural-network-viz"
import { SignalCards } from "@/components/signal-cards"
import { VolatilityMeter } from "@/components/volatility-meter"
import { PerformanceChart } from "@/components/performance-chart"
import { WatchList } from "@/components/watch-list"
import { TradesTable } from "@/components/trades-table"
import { OpenPositions } from "@/components/open-positions"



export function Dashboard() {
  return (
    <section className="relative py-24 px-6">
      <div className="container mx-auto max-w-7xl">
        {/* Section Header */}
        <div className="mb-12">
          <h2 className="text-4xl md:text-5xl font-bold text-gradient-cyan mb-4">Control Center</h2>
          <p className="text-muted-foreground text-lg">
            Real-time market intelligence powered by ensemble neural networks
          </p>
        </div>

        {/* Bento Grid Layout - Masonry style with varying sizes */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 auto-rows-auto">
          {/* Large: Neural Network Visualization (takes 2 columns) */}
          <div className="md:col-span-2 lg:col-span-2 lg:row-span-2">
            <NeuralNetworkViz />
          </div>

          {/* Medium: Volatility Meter */}
          <div className="lg:row-span-1">
            <VolatilityMeter />
          </div>

          {/* Medium: Market Overview */}
          <div className="lg:row-span-1">
            <MarketOverview />
          </div>

          {/* Large: Performance Chart (takes 2 columns) */}
          <div className="md:col-span-2 lg:col-span-2">
            <PerformanceChart />
          </div>
          <div className="md:col-span-2 lg:col-span-3">
            <TradesTable />
          </div>
          <div className="md:col-span-1 lg:col-span-1">
            <OpenPositions />
          </div>


          {/* Medium: Watch List */}
          <div className="lg:row-span-2">
            <WatchList />
          </div>

          {/* Extra Large: Signal Cards (takes full width) */}
          <div className="md:col-span-2 lg:col-span-2">
            <SignalCards />
          </div>
        </div>
      </div>
    </section>
  )
}
