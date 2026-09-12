/**
 * Shared UI primitives. All styles inline / locally scoped via a small
 * className convention in app.css. No external UI library.
 */
import type { ReactNode } from 'react'
import { toneVar, type Label, type Tone } from '../semantics'
import { IconSource, IconWarn } from './Icons'
import type { Meta, Freshness } from '../types'
import { freshnessLabel } from '../semantics'

/* ---------------- Status badge (label + tone, never color-only) --------- */
export function Badge({ label }: { label: Label }) {
  const t = toneVar[label.tone]
  return (
    <span className="badge" style={{ color: t.fg, background: t.bg, borderColor: t.fg }} title={label.en}>
      <span className="badge-dot" style={{ background: t.fg }} aria-hidden />
      <span className="badge-zh">{label.zh}</span>
      <span className="badge-en">{label.en}</span>
    </span>
  )
}

export function Pill({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  const t = toneVar[tone]
  return <span className="pill" style={{ color: t.fg, background: t.bg }}>{children}</span>
}

/* ---------------- Card -------------------------------------------------- */
export function Card({
  children, className = '', onClick, ariaLabel,
}: { children: ReactNode; className?: string; onClick?: () => void; ariaLabel?: string }) {
  return (
    <div
      className={`card ${onClick ? 'card-clickable' : ''} ${className}`}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={ariaLabel}
      onKeyDown={onClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onClick() } } : undefined}
    >
      {children}
    </div>
  )
}

export function SectionTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <div className="section-title">
      <h2>{children}</h2>
      {right}
    </div>
  )
}

/* ---------------- Freshness chip --------------------------------------- */
export function FreshnessChip({ f, observedAt }: { f: Freshness; observedAt?: string }) {
  const label = freshnessLabel[f]
  const t = toneVar[label.tone]
  return (
    <span className="freshness" style={{ color: t.fg }} title={observedAt ? `observed: ${observedAt}` : undefined}>
      <span className="freshness-dot" style={{ background: t.fg }} aria-hidden />
      {label.zh}
    </span>
  )
}

/* ---------------- Provenance drawer ------------------------------------ */
export function Provenance({ meta, onOpen }: { meta: Meta; onOpen?: (m: Meta) => void }) {
  const degraded = meta.projection_status !== 'COMPLETE' || meta.warnings.length > 0
  return (
    <button
      className="provenance-btn"
      onClick={() => onOpen?.(meta)}
      title={`来源 · ${meta.authority}`}
      aria-label="查看数据来源"
    >
      <IconSource size={14} />
      <span>{meta.trust}</span>
      <FreshnessChip f={meta.freshness} observedAt={meta.observed_at} />
      {degraded && <IconWarn size={13} />}
    </button>
  )
}

/* ---------------- Provenance panel content ----------------------------- */
export function ProvenancePanel({ meta, onClose }: { meta: Meta; onClose: () => void }) {
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()} aria-label="数据来源详情">
        <header className="drawer-head">
          <div>
            <b>数据来源 · Provenance</b>
            <div className="muted">UI 状态不是系统真源，以下为其真实来源</div>
          </div>
          <button className="btn-icon" onClick={onClose} aria-label="关闭">✕</button>
        </header>
        <dl className="kv">
          <dt>观测时间</dt><dd className="mono">{meta.observed_at}</dd>
          <dt>权威来源</dt><dd className="mono">{meta.authority}</dd>
          <dt>信任等级</dt><dd>{meta.trust}</dd>
          <dt>新鲜度</dt><dd>{meta.freshness}</dd>
          <dt>投影状态</dt><dd>{meta.projection_status}</dd>
        </dl>
        <h4>来源引用</h4>
        {meta.sources.length === 0 && <div className="muted">（无来源引用）</div>}
        <ul className="src-list">
          {meta.sources.map((s, i) => (
            <li key={i}>
              <span className="src-kind">{s.kind}</span>
              {s.repo && <span className="mono">{s.repo}</span>}
              {s.ref && <span className="mono src-sha">{s.ref.slice(0, 10)}</span>}
              {s.path && <div className="mono muted src-path">{s.path}</div>}
              {s.detail && <div className="muted">{s.detail}</div>}
              {s.url && <a href={s.url} target="_blank" rel="noreferrer">{s.url}</a>}
            </li>
          ))}
        </ul>
        {meta.warnings.length > 0 && (
          <>
            <h4 className="warn-title">警告</h4>
            <ul className="warn-list">
              {meta.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </>
        )}
      </aside>
    </div>
  )
}

/* ---------------- Misc ------------------------------------------------- */
export function sha(s?: string | null, n = 8): string {
  if (!s) return '—'
  return s.length > n ? s.slice(0, n) : s
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>
}

export function KeyVal({ k, v, mono }: { k: string; v: ReactNode; mono?: boolean }) {
  return (
    <div className="keyval">
      <span className="keyval-k">{k}</span>
      <span className={mono ? 'keyval-v mono' : 'keyval-v'}>{v ?? '—'}</span>
    </div>
  )
}

/* ======================================================================
 * Plain-language report primitives
 * ----------------------------------------------------------------------
 * Owner feedback: "报告能不能用人话，简单易懂的，能用图像表格表示优先用图像表格"
 * Rule of thumb these enforce: lead with a ONE-LINE plain answer, then show
 * counts as big colour tiles, then proportions as bars. Text detail is
 * secondary and collapsible. Colour is ALWAYS paired with a Chinese label
 * (never colour-only), per the status-semantics iron rule.
 * ==================================================================== */

/** A one-line, jargon-free headline answer to "so what's the situation?" */
export function PlainAnswer({ tone = 'accent', icon, children }: {
  tone?: Tone; icon?: ReactNode; children: ReactNode
}) {
  const t = toneVar[tone]
  return (
    <div className="plain-answer" style={{ background: t.bg, borderColor: t.fg }}>
      {icon && <span style={{ color: t.fg, flex: 'none', marginTop: 1 }}>{icon}</span>}
      <div>{children}</div>
    </div>
  )
}

/** A big number tile: colour stripe + plain Chinese label + value. */
export function Tile({ label, value, sub, tone = 'neutral', icon }: {
  label: string; value: ReactNode; sub?: ReactNode; tone?: Tone; icon?: ReactNode
}) {
  const t = toneVar[tone]
  return (
    <div className="tile" style={{ borderLeftColor: t.fg }}>
      <div className="tile-label">
        {icon && <span style={{ color: t.fg, display: 'inline-flex' }}>{icon}</span>}
        {label}
      </div>
      <div className="tile-value" style={{ color: t.fg }}>{value}</div>
      {sub != null && <div className="tile-sub">{sub}</div>}
    </div>
  )
}

/** Horizontal bar chart, pure CSS (no external chart lib) — one row per item. */
export function BarChart({ rows, emptyHint }: {
  rows: { label: string; value: number; tone?: Tone }[]
  emptyHint?: string
}) {
  const max = Math.max(1, ...rows.map((r) => r.value))
  if (!rows.length) return <div className="muted">{emptyHint ?? '暂无数据'}</div>
  return (
    <div>
      {rows.map((r) => {
        const t = toneVar[r.tone ?? 'accent']
        return (
          <div className="bar-row" key={r.label}>
            <span title={r.label}>{r.label}</span>
            <span className="bar-track">
              <span className="bar-fill" style={{ width: `${(r.value / max) * 100}%`, background: t.fg }} />
            </span>
            <span className="bar-count">{r.value}</span>
          </div>
        )
      })}
    </div>
  )
}

/** Traffic-light chips: one glance tells you what needs attention. */
export function TrafficRow({ items }: {
  items: { label: string; tone: Tone; value?: ReactNode }[]
}) {
  return (
    <div className="traffic">
      {items.map((it) => {
        const t = toneVar[it.tone]
        return (
          <span className="traffic-item" key={it.label}>
            <span className="traffic-dot" style={{ background: t.fg }} aria-hidden />
            <span>{it.label}</span>
            {it.value != null && <b style={{ color: t.fg, fontVariantNumeric: 'tabular-nums' }}>{it.value}</b>}
          </span>
        )
      })}
    </div>
  )
}
