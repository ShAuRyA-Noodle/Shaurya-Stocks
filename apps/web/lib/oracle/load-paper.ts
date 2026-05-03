/**
 * Server-only: load the optional paper-trading snapshot.
 *
 * The snapshot is written by `quant paper status --json-out` and synced
 * into apps/web/.oracle-artifacts/ by the prebuild script. Absence is a
 * valid state — the page renders a "not connected" panel rather than
 * fabricating any account number.
 */

import { existsSync, readFileSync } from "node:fs"
import { join } from "node:path"

import type { PaperStatusSnapshot } from "./types"

const ARTIFACT_ROOTS: readonly string[] = [
  join(process.cwd(), ".oracle-artifacts"),
  join(process.cwd(), "..", "api", "examples", "backtest", "artifacts"),
]

export function loadOraclePaperSnapshot(): PaperStatusSnapshot | null {
  for (const root of ARTIFACT_ROOTS) {
    const candidate = join(root, "paper-status.json")
    if (!existsSync(candidate)) continue
    try {
      const parsed = JSON.parse(readFileSync(candidate, "utf8")) as PaperStatusSnapshot
      if (
        typeof parsed.account?.equity === "string" &&
        Array.isArray(parsed.positions)
      ) {
        return parsed
      }
    } catch {
      // fall through; next root
    }
  }
  return null
}
