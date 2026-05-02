"use client"

import { useState } from "react"
import { Check, Copy } from "lucide-react"

import type { BacktestManifest } from "@/lib/oracle/types"

interface ReproBlockProps {
  readonly manifest: BacktestManifest
}

interface Field {
  readonly label: string
  readonly full: string
  readonly truncated: string
}

function buildFields(manifest: BacktestManifest): readonly Field[] {
  return [
    {
      label: "code_sha",
      full: manifest.code_sha,
      truncated: manifest.code_sha.slice(0, 7),
    },
    {
      label: "config_hash",
      full: manifest.config_hash,
      truncated: `${manifest.config_hash.slice(0, 16)}…`,
    },
    {
      label: "data_fingerprint",
      full: manifest.data_fingerprint,
      truncated: `${manifest.data_fingerprint.slice(0, 16)}…`,
    },
  ]
}

function CopyRow({ field }: { field: Field }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    if (typeof navigator === "undefined" || !navigator.clipboard) return
    try {
      await navigator.clipboard.writeText(field.full)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1400)
    } catch {
      // Clipboard may be denied; fail silent — the value is also shown on hover.
    }
  }

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={field.full}
      aria-label={`Copy ${field.label} (${field.full}) to clipboard`}
      className="group w-full text-left rounded-xl border border-border/60 bg-card/40 backdrop-blur-xl px-5 py-4 transition-colors hover:border-primary/50 focus:outline-none focus-visible:border-primary"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="text-[10px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
          {field.label}
        </span>
        <span className="inline-flex items-center gap-1 text-[10px] font-mono uppercase tracking-[0.18em] text-muted-foreground/70 group-hover:text-primary transition-colors">
          {copied ? (
            <>
              <Check className="w-3 h-3" />
              Copied
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              Copy
            </>
          )}
        </span>
      </div>
      <div className="mt-2 font-mono text-sm md:text-base text-primary tabular-nums break-all">
        {field.truncated}
      </div>
    </button>
  )
}

export function ReproBlock({ manifest }: ReproBlockProps) {
  const fields = buildFields(manifest)
  const pkgCount = Object.keys(manifest.package_versions).length
  const created = new Date(manifest.created_at)
  const createdIso = manifest.created_at

  return (
    <section
      id="reproducibility"
      className="relative px-6 py-20 md:py-28 border-t border-border/40"
      aria-labelledby="oracle-repro-title"
    >
      <div className="container mx-auto max-w-7xl">
        <div className="flex items-end justify-between flex-wrap gap-6 mb-12">
          <div>
            <div className="text-[11px] font-mono tracking-[0.3em] uppercase text-primary mb-3">
              Reproducibility
            </div>
            <h2
              id="oracle-repro-title"
              className="text-3xl md:text-5xl font-semibold tracking-[-0.02em]"
            >
              The manifest. Click to copy.
            </h2>
          </div>
          <p className="text-sm text-muted-foreground max-w-md">
            <span className="text-foreground">No manifest, no publish.</span>{" "}
            Same SHA + same data fingerprint reproduces these numbers exactly.
            Source:{" "}
            <code className="font-mono text-primary">manifest.json</code>.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 md:gap-4">
          {fields.map((f) => (
            <CopyRow key={f.label} field={f} />
          ))}
        </div>

        <dl className="mt-6 grid grid-cols-1 sm:grid-cols-3 gap-3 md:gap-4 text-sm">
          <div className="rounded-xl border border-border/40 bg-card/30 px-5 py-4">
            <dt className="text-[10px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
              Python
            </dt>
            <dd className="mt-2 font-mono text-primary">
              {manifest.python_version}
            </dd>
          </div>
          <div className="rounded-xl border border-border/40 bg-card/30 px-5 py-4">
            <dt className="text-[10px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
              Pinned packages
            </dt>
            <dd className="mt-2 font-mono text-primary">{pkgCount}</dd>
          </div>
          <div className="rounded-xl border border-border/40 bg-card/30 px-5 py-4">
            <dt className="text-[10px] font-mono uppercase tracking-[0.22em] text-muted-foreground">
              Run created
            </dt>
            <dd className="mt-2 font-mono text-primary">
              <time dateTime={createdIso}>
                {Number.isFinite(created.getTime())
                  ? created.toISOString().slice(0, 19).replace("T", " ") + "Z"
                  : createdIso}
              </time>
            </dd>
          </div>
        </dl>
      </div>
    </section>
  )
}
