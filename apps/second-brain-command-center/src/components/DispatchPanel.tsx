/**
 * DispatchPanel — Phase 2A Dispatch Intent UI.
 *
 * Non-negotiable boundary: pressing 派发 only COMPOSES a read-only intent.
 * It never starts a process, never activates RDC, never writes system truth.
 * The button press is INTENT; authority belongs to canonical repository state.
 *
 * Rendered in plain language + a graphical authorization checklist + a
 * red/amber/green light, never raw JSON alone.
 */
import { useState } from 'react'
import { Card, Pill, Empty, sha } from './ui'
import { IconWarn, IconShield, IconChevron } from './Icons'
import { api } from '../api'
import type { DispatchIntent, DispatchVerdict } from '../types'
import type { Tone } from '../semantics'

const VERDICT_META: Record<DispatchVerdict, { zh: string; tone: Tone; light: string }> = {
  ADMISSIBLE: { zh: '可以进入下一步（等人确认）', tone: 'ok', light: '绿' },
  BLOCKED_MISSING_AUTHORITY: { zh: '缺授权，暂不能开工', tone: 'bad', light: '红' },
  BLOCKED_STATE_CONFLICT: { zh: '授权冲突/已撤销，暂不能开工', tone: 'bad', light: '红' },
  BLOCKED_STALE_BASE: { zh: '授权过期或基准已动，暂不能开工', tone: 'bad', light: '红' },
  UPGRADE_TO_OWNER: { zh: '需要老板决策', tone: 'warn', light: '黄' },
}

const AUTHORITY_STATE_ZH: Record<string, string> = {
  CURRENT: '授权当前有效',
  UNKNOWN: '授权状态不明（fail-closed）',
  STALE: '授权已过期',
  REVOKED: '授权已撤销',
}

export function DispatchPanel({
  tasks,
}: {
  tasks: { task_id: string; project_id?: string | null; executor?: string | null }[]
}) {
  const [taskId, setTaskId] = useState('')
  const [intent, setIntent] = useState<DispatchIntent | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function onDispatch() {
    const tid = taskId.trim()
    if (!tid) { setErr('先选一个任务'); return }
    setBusy(true); setErr(null)
    try {
      const project = tasks.find((t) => t.task_id === tid)?.project_id ?? 'SECOND_BRAIN'
      const res = await api.dispatchIntent(project, tid)
      setIntent(res.intent)
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
      setIntent(null)
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card>
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: 8 }}>
        <h3 style={{ margin: 0, fontSize: 14 }}>派发 · Dispatch</h3>
        <span className="muted" style={{ fontSize: 11.5 }}>
          只生成「派发意图」，不启动任何进程
        </span>
      </div>

      <div className="row" style={{ gap: 8, marginTop: 12, flexWrap: 'wrap' }}>
        <select
          className="input"
          style={{ flex: '1 1 260px', minHeight: 40 }}
          value={taskId}
          onChange={(e) => setTaskId(e.target.value)}
        >
          <option value="">— 选一个任务 —</option>
          {tasks.map((t) => (
            <option key={t.task_id} value={t.task_id}>
              {t.task_id}{t.executor ? `  ·  ${t.executor}` : ''}
            </option>
          ))}
        </select>
        <button
          className="btn btn-primary"
          style={{ minHeight: 40, minWidth: 120 }}
          onClick={onDispatch}
          disabled={busy || !taskId}
        >
          {busy ? '生成中…' : '派发'}
        </button>
      </div>

      {err && (
        <div className="banner banner-warn" style={{ marginTop: 12 }}>
          <IconWarn size={16} />
          <div>{err}</div>
        </div>
      )}

      {intent && <IntentView intent={intent} />}
    </Card>
  )
}

function IntentView({ intent }: { intent: DispatchIntent }) {
  const [showRaw, setShowRaw] = useState(false)
  const vm = VERDICT_META[intent.verdict]
  const okCount = intent.readonly_authority_check.filter((c) => c.present).length
  const totalCount = intent.readonly_authority_check.length

  return (
    <div style={{ marginTop: 16 }}>
      {/* 人话一句话 */}
      <div className={`plain-answer plain-${vm.tone}`} style={{ marginBottom: 12 }}>
        <IconShield size={18} />
        <span>{intent.plain_answer}</span>
      </div>

      {/* 红黄绿灯 + 关键标识 */}
      <div className="traffic-row" style={{ marginBottom: 12, flexWrap: 'wrap' }}>
        <Pill tone={vm.tone}>{vm.light} · {vm.zh}</Pill>
        <Pill tone="neutral">授权 {okCount}/{totalCount}</Pill>
        <Pill tone="neutral">{AUTHORITY_STATE_ZH[intent.authority_state] ?? intent.authority_state}</Pill>
        <Pill tone="ok">未启动任何进程</Pill>
      </div>

      {/* 授权清单 */}
      <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>授权清单（缺哪项一目了然）</div>
      <div className="auth-checklist">
        {intent.readonly_authority_check.map((c) => (
          <div key={c.input_id} className={`auth-row ${c.present ? 'auth-ok' : 'auth-miss'}`}>
            <span className="auth-mark" aria-hidden>
              {c.present ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <path d="M20 6 9 17l-5-5" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <path d="M18 6 6 18M6 6l12 12" />
                </svg>
              )}
            </span>
            <span className="auth-label">{c.label_zh}</span>
            <span className="muted auth-detail">{c.detail}</span>
          </div>
        ))}
      </div>

      {/* Critic 预筛 */}
      <div className="muted" style={{ fontSize: 12, marginTop: 12 }}>
        Critic 预筛：{intent.critic_pre_screen.enabled
          ? `已评分 ${intent.critic_pre_screen.confidence ?? '—'}`
          : '尚未接线，默认交人工'}
        {intent.critic_pre_screen.note ? `（${intent.critic_pre_screen.note}）` : ''}
      </div>

      {/* 技术标识（默认折叠） */}
      <button className="btn btn-ghost" style={{ marginTop: 12 }} onClick={() => setShowRaw((v) => !v)}>
        <IconChevron size={14} /> {showRaw ? '收起技术标识' : '展开技术标识'}
      </button>
      {showRaw && (
        <div className="kv-rows" style={{ marginTop: 8 }}>
          <div className="kv-row"><span className="kv-k">意图 ID</span><span className="mono kv-v">{sha(intent.dispatch_intent_id, 22)}</span></div>
          <div className="kv-row"><span className="kv-k">任务</span><span className="mono kv-v">{intent.task_id}</span></div>
          <div className="kv-row"><span className="kv-k">下一道门</span><span className="mono kv-v">{intent.next_gate}</span></div>
          <div className="kv-row"><span className="kv-k">执行者 / 载体</span><span className="mono kv-v">{intent.executor ?? '—'} / {intent.carrier ?? '—'}</span></div>
          <div className="kv-row"><span className="kv-k">起始进程</span><span className="mono kv-v">{String(intent.starts_any_process)}</span></div>
        </div>
      )}
    </div>
  )
}

export function DispatchPanelEmpty() {
  return <Empty>暂时读不到可派发的任务</Empty>
}
