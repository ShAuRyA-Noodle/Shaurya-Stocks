"use client"

import { useState } from "react"
import { Terminal, Send, Check, AlertCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { glassPanel, glassPanelHover, neonGlowCyan, neonGlowGreen } from "@/lib/cn-utils"

interface ParsedOrder {
  action: "BUY" | "SELL"
  quantity: string
  symbol: string
  condition?: string
}

export function TradingTerminal() {
  const [input, setInput] = useState("")
  const [parsedOrder, setParsedOrder] = useState<ParsedOrder | null>(null)
  const [executing, setExecuting] = useState(false)
  const [executed, setExecuted] = useState(false)

  const handleParse = () => {
    // Simple NLP parsing (in production this would be AI-powered)
    const text = input.toLowerCase()
    let order: ParsedOrder | null = null

    if (text.includes("buy") || text.includes("long")) {
      const match = text.match(/(\d+k?)\s+([a-z]+)/i)
      if (match) {
        order = {
          action: "BUY",
          quantity: match[1],
          symbol: match[2].toUpperCase(),
          condition: text.includes("if") ? text.split("if")[1].trim() : undefined,
        }
      }
    } else if (text.includes("sell") || text.includes("short")) {
      const match = text.match(/(\d+k?)\s+([a-z]+)/i)
      if (match) {
        order = {
          action: "SELL",
          quantity: match[1],
          symbol: match[2].toUpperCase(),
          condition: text.includes("if") ? text.split("if")[1].trim() : undefined,
        }
      }
    }

    setParsedOrder(order)
  }

  const handleExecute = async () => {
    setExecuting(true)
    // Simulate order execution
    await new Promise((resolve) => setTimeout(resolve, 2000))
    setExecuting(false)
    setExecuted(true)

    setTimeout(() => {
      setExecuted(false)
      setInput("")
      setParsedOrder(null)
    }, 3000)
  }

  return (
    <section className="relative py-24 px-6">
      <div className="container mx-auto max-w-4xl">
        {/* Header */}
        <div className="mb-12 text-center">
          <h2 className="text-4xl md:text-5xl font-bold text-gradient-cyan mb-4">Execution Terminal</h2>
          <p className="text-muted-foreground text-lg">Natural language order placement with AI parsing</p>
        </div>

        {/* Terminal Interface */}
        <div className={`${glassPanel()} ${neonGlowCyan()} rounded-2xl overflow-hidden`}>
          {/* Terminal Header */}
          <div className="border-b border-border/50 px-6 py-4 flex items-center gap-2 bg-card/30">
            <Terminal className="w-5 h-5 text-primary" />
            <span className="font-mono text-sm font-semibold">AI Trading Assistant</span>
            <div className="ml-auto flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-chart-2 animate-pulse" />
              <span className="text-xs font-mono text-muted-foreground">LIVE</span>
            </div>
          </div>

          {/* Input Area */}
          <div className="p-6">
            <div className="flex gap-3 mb-4">
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && input && !parsedOrder) handleParse()
                }}
                placeholder='Try: "Buy 10k AAPL if it drops below 180"'
                className="flex-1 bg-background/50 border-border/50 focus-visible:border-primary/50 font-mono text-lg h-14"
                disabled={executing || executed}
              />
              <Button
                onClick={handleParse}
                disabled={!input || !!parsedOrder || executing || executed}
                size="lg"
                className={`${glassPanelHover()} ${neonGlowCyan()} bg-primary text-primary-foreground hover:bg-primary/90 px-6`}
              >
                Parse
              </Button>
            </div>

            {/* Parsed Order Preview */}
            {parsedOrder && !executed && (
              <div
                className={`${glassPanel()} p-6 rounded-xl space-y-4 animate-in fade-in slide-in-from-bottom-4 duration-500`}
              >
                <div className="flex items-center gap-2 text-primary font-mono font-semibold mb-4">
                  <AlertCircle className="w-5 h-5" />
                  <span>Order Preview - Confirm Execution</span>
                </div>

                {/* Order Details */}
                <div className={`${glassPanel()} p-4 rounded-lg bg-background/50 font-mono space-y-3`}>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground text-sm">Action</span>
                    <span
                      className={`font-bold text-lg ${parsedOrder.action === "BUY" ? "text-chart-2" : "text-chart-3"}`}
                    >
                      {parsedOrder.action}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground text-sm">Symbol</span>
                    <span className="font-bold text-lg text-primary">{parsedOrder.symbol}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground text-sm">Quantity</span>
                    <span className="font-bold text-lg">{parsedOrder.quantity}</span>
                  </div>
                  {parsedOrder.condition && (
                    <div className="pt-3 border-t border-border/30">
                      <span className="text-muted-foreground text-sm block mb-1">Condition</span>
                      <span className="text-sm text-chart-4">{parsedOrder.condition}</span>
                    </div>
                  )}
                </div>

                {/* Execution Logic Preview */}
                <div className={`${glassPanel()} p-4 rounded-lg bg-primary/5 border border-primary/20`}>
                  <div className="text-xs font-mono text-muted-foreground mb-2 uppercase">Execution Logic</div>
                  <pre className="text-sm font-mono text-foreground overflow-x-auto">
                    <code>{`if (${parsedOrder.symbol}.price ${parsedOrder.condition ? `${parsedOrder.condition}` : "MARKET"}) {
  execute(${parsedOrder.action}, ${parsedOrder.quantity}, ${parsedOrder.symbol});
}`}</code>
                  </pre>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 pt-2">
                  <Button
                    onClick={handleExecute}
                    disabled={executing}
                    className={`flex-1 bg-chart-2 text-black hover:bg-chart-2/90 font-semibold ${neonGlowGreen()} h-12`}
                  >
                    {executing ? (
                      <>
                        <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin mr-2" />
                        Executing...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4 mr-2" />
                        Confirm & Execute
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={() => {
                      setParsedOrder(null)
                      setInput("")
                    }}
                    variant="outline"
                    disabled={executing}
                    className={`${glassPanelHover()} border-chart-3/30 hover:border-chart-3/60`}
                  >
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {/* Success Message */}
            {executed && (
              <div
                className={`${glassPanel()} p-6 rounded-xl animate-in fade-in slide-in-from-bottom-4 duration-500 bg-chart-2/10 border-chart-2/30`}
              >
                <div className="flex items-center gap-3 text-chart-2">
                  <div className="w-12 h-12 rounded-full bg-chart-2/20 flex items-center justify-center">
                    <Check className="w-6 h-6" />
                  </div>
                  <div>
                    <div className="font-bold text-lg">Order Executed Successfully</div>
                    <div className="text-sm text-muted-foreground font-mono">
                      {parsedOrder?.action} {parsedOrder?.quantity} {parsedOrder?.symbol}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Example Commands */}
          <div className="border-t border-border/50 px-6 py-4 bg-card/30">
            <div className="text-xs font-mono text-muted-foreground mb-3 uppercase">Example Commands</div>
            <div className="flex flex-wrap gap-2">
              {["Buy 5k TSLA", "Sell 10k AAPL if price > 180", "Long 2k NVDA at market"].map((example) => (
                <button
                  key={example}
                  onClick={() => setInput(example)}
                  className={`${glassPanel()} px-3 py-1.5 rounded-lg text-xs font-mono hover:border-primary/40 transition-colors`}
                  disabled={executing || executed}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
