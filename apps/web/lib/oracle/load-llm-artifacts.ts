/**
 * Server-only: load LLM pipeline artifacts (regime, briefing, sentiment, catalysts)
 * from .oracle-artifacts. All optional — missing files render empty states.
 */

import { existsSync, readFileSync } from "node:fs"
import { join } from "node:path"

const ARTIFACT_ROOTS: readonly string[] = [
  join(process.cwd(), ".oracle-artifacts"),
  join(process.cwd(), "..", "api", "examples", "backtest", "artifacts"),
]

function readJson<T>(filename: string): T | null {
  for (const root of ARTIFACT_ROOTS) {
    const p = join(root, filename)
    if (!existsSync(p)) continue
    try {
      return JSON.parse(readFileSync(p, "utf8")) as T
    } catch {
      // fall through
    }
  }
  return null
}

function readCsv(filename: string): string[][] | null {
  for (const root of ARTIFACT_ROOTS) {
    const p = join(root, filename)
    if (!existsSync(p)) continue
    try {
      const raw = readFileSync(p, "utf8").trim()
      if (!raw) return null
      return raw.split(/\r?\n/).map((line) => line.split(","))
    } catch {
      // fall through
    }
  }
  return null
}

export interface RegimeArtifact {
  date: string
  regime: "risk_on" | "risk_off" | "neutral"
  confidence: number
  rationale: string
  model: string
  n_headlines: number
}

export interface BriefingArtifact {
  date: string
  headline: string
  narrative: string
  model: string
  n_picks: number
  regime_used: string
}

export interface CatalystRow {
  symbol: string
  date: string
  catalyst_type: string
  severity: "low" | "medium" | "high"
  summary: string
  model: string
}

export interface SentimentRow {
  symbol: string
  date: string
  sentiment_mean: number
  sentiment_count: number
  sentiment_max_abs: number
}

export interface LlmArtifacts {
  regime: RegimeArtifact | null
  briefing: BriefingArtifact | null
  catalysts: readonly CatalystRow[]
  sentiment: readonly SentimentRow[]
}

export function loadLlmArtifacts(): LlmArtifacts {
  const regime = readJson<RegimeArtifact>("regime.json")
  const briefing = readJson<BriefingArtifact>("briefing.json")

  const catalystsRaw = readCsv("catalysts.csv")
  const catalysts: CatalystRow[] = []
  if (catalystsRaw && catalystsRaw.length > 1) {
    const header = catalystsRaw[0] ?? []
    const idx = (col: string) => header.indexOf(col)
    const iSym = idx("symbol")
    const iDate = idx("date")
    const iType = idx("catalyst_type")
    const iSev = idx("severity")
    const iSum = idx("summary")
    const iModel = idx("model")
    for (let i = 1; i < catalystsRaw.length; i += 1) {
      const r = catalystsRaw[i] ?? []
      catalysts.push({
        symbol: r[iSym] ?? "",
        date: r[iDate] ?? "",
        catalyst_type: r[iType] ?? "none",
        severity: ((r[iSev] ?? "low") as "low" | "medium" | "high"),
        summary: r[iSum] ?? "",
        model: r[iModel] ?? "",
      })
    }
  }

  const sentimentRaw = readCsv("sentiment.csv")
  const sentiment: SentimentRow[] = []
  if (sentimentRaw && sentimentRaw.length > 1) {
    const header = sentimentRaw[0] ?? []
    const idx = (col: string) => header.indexOf(col)
    const iSym = idx("symbol")
    const iDate = idx("date")
    const iMean = idx("sentiment_mean")
    const iCount = idx("sentiment_count")
    const iMax = idx("sentiment_max_abs")
    for (let i = 1; i < sentimentRaw.length; i += 1) {
      const r = sentimentRaw[i] ?? []
      sentiment.push({
        symbol: r[iSym] ?? "",
        date: r[iDate] ?? "",
        sentiment_mean: Number(r[iMean] ?? 0),
        sentiment_count: Number(r[iCount] ?? 0),
        sentiment_max_abs: Number(r[iMax] ?? 0),
      })
    }
  }

  return { regime, briefing, catalysts, sentiment }
}
