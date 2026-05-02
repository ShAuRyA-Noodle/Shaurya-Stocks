/**
 * Formatters for Oracle results page.
 *
 * Locked to en-US Intl.NumberFormat so locale drift can never change the
 * displayed digits between dev/prod/CI. Every number on the page goes
 * through one of these helpers — no inline `toFixed` / template literals.
 */

const LOCALE = "en-US"

const PERCENT_2DP = new Intl.NumberFormat(LOCALE, {
  style: "percent",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const RATIO_2DP = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const RATIO_3DP = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
})

const TURNOVER = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const USD_INT = new Intl.NumberFormat(LOCALE, {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
})

const USD_K = new Intl.NumberFormat(LOCALE, {
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
})

const DATE_LONG = new Intl.DateTimeFormat(LOCALE, {
  year: "numeric",
  month: "short",
  day: "numeric",
  timeZone: "UTC",
})

const DATE_TICK = new Intl.DateTimeFormat(LOCALE, {
  year: "numeric",
  month: "short",
  timeZone: "UTC",
})

const DATE_YEAR = new Intl.DateTimeFormat(LOCALE, {
  year: "numeric",
  timeZone: "UTC",
})

export function formatPercent(fraction: number): string {
  return PERCENT_2DP.format(fraction)
}

export function formatSharpe(value: number): string {
  return RATIO_2DP.format(value)
}

export function formatRatio2(value: number): string {
  return RATIO_2DP.format(value)
}

export function formatRatio3(value: number): string {
  return RATIO_3DP.format(value)
}

export function formatTurnover(value: number): string {
  return `${TURNOVER.format(value)}×`
}

export function formatUsd(value: number): string {
  return USD_INT.format(value)
}

export function formatUsdShort(value: number): string {
  if (Math.abs(value) >= 1_000_000) {
    return `$${USD_K.format(value / 1_000_000)}M`
  }
  if (Math.abs(value) >= 1_000) {
    return `$${USD_K.format(value / 1_000)}K`
  }
  return `$${USD_K.format(value)}`
}

/**
 * Parse an ISO date (YYYY-MM-DD) as a UTC midnight Date so subsequent
 * formatting is timezone-stable across CI/dev/prod.
 */
export function parseIsoDate(iso: string): Date {
  // Date(YYYY-MM-DD) is UTC by spec; this is just a typed wrapper.
  const d = new Date(`${iso}T00:00:00Z`)
  if (Number.isNaN(d.getTime())) {
    throw new Error(`[oracle] invalid ISO date: ${iso}`)
  }
  return d
}

export function formatDateLong(iso: string): string {
  return DATE_LONG.format(parseIsoDate(iso))
}

export function formatDateTick(iso: string): string {
  return DATE_TICK.format(parseIsoDate(iso))
}

export function formatYear(iso: string): string {
  return DATE_YEAR.format(parseIsoDate(iso))
}
