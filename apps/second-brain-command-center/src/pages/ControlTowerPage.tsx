import { useState } from 'react'
import { Card, SectionTitle, Badge, Provenance, ProvenancePanel, Empty, Pill, sha } from '../components/ui'
import { IconWarn, IconTower } from '../components/Icons'
import { useControlTower } from '../hooks'
import { toneVar } from '../semantics'
import type { Meta } from '../types'

export default function ControlTowerPage() {
  const ct = useControlTower()
  const [prov, setProv] = useState<Meta | null>(null)

  if (ct.loading) return <div className="loading">正在读取控制塔…</div>
  if (ct.error) return <div className="error-box">控制塔不可用：{ct.error}</div>
  const d = ct.data
  if (!d) return <Empty>无控制塔数据</Empty>

  const order = ['READY', 'DISPATCHED', 'RUNNING', 'REVIEW', 'CANONICALIZATION', 'BLOCKED', 'STALLED', 'OUTCOME_UNKNOWN', 'OWNER_GATE', 'DONE', 'PAUSED', 'PLANNED']

  return (
    <div>
      <SectionTitle right={
        <span className="row" style={{ gap: 10 }}>
          {d.projection_as_of && <span className="muted">投影 as_of {d.projection_as_of}</span>}
          <Provenance meta={ct.meta ?? ({} as Meta)} onOpen={setProv} />
        </span>
      }>控制塔 · Control Tower</SectionTitle>

      <div className="banner banner-info">
        <IconTower size={16} />
        <div>
          <b>控制塔是执行权威，不是本页。</b>
          <span className="muted"> 本页只投影当前 route / claim / lane / 碰撞状态。执行真源以 canonical ACTIVE-* route、Work Claim、Release Gate 与 fresh witness 为准。</span>
        </div>
      </div>

      <SectionTitle>状态分布 · State Distribution</SectionTitle>
      <div className="ct-strip">
        {order.map((k) => {
          const v = d.counts[k] ?? 0
          return (
            <div key={k} className="ct-cell" style={{ opacity: v === 0 ? 0.45 : 1 }}>
              <div className="ct-count" style={{ color: v === 0 ? 'var(--text-3)' : 'var(--text-0)' }}>{v}</div>
              <div className="ct-label">{k}</div>
            </div>
          )
        })}
      </div>

      <SectionTitle>程序泳道 · Program Lanes</SectionTitle>
      {d.lanes.length ? (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Lane</th><th>期望</th><th>观测</th><th>阶段</th><th>执行者</th><th>下一门</th><th>交易</th></tr></thead>
            <tbody>
              {d.lanes.map((l, i) => (
                <tr key={i}>
                  <td className="mono" style={{ fontSize: 11 }}>{String(l.lane_id)}</td>
                  <td><Pill tone="neutral">{String(l.desired_state)}</Pill></td>
                  <td className="mono" style={{ fontSize: 11 }}>{String(l.observed_state)}</td>
                  <td className="mono" style={{ fontSize: 11 }}>{String(l.phase ?? '—')}</td>
                  <td>{l.executor ? <Pill tone="accent">{String(l.executor)}</Pill> : '—'}</td>
                  <td className="mono" style={{ fontSize: 11 }}>{String(l.next_gate ?? '—')}</td>
                  <td>{l.trading_authorized === false ? <Pill tone="ok">NO_TRADE</Pill> : String(l.trading_authorized ?? '—')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <Empty>无泳道</Empty>}

      <SectionTitle>执行路线 · Routes</SectionTitle>
      {d.routes.length ? (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Agent</th><th>task_id</th><th>epoch</th><th>状态</th><th>可执行</th><th>Issue / PR</th></tr></thead>
            <tbody>
              {d.routes.map((r, i) => (
                <tr key={i}>
                  <td>{String(r.agent)}</td>
                  <td className="mono" style={{ fontSize: 11 }}>{String(r.task_id)}</td>
                  <td className="mono">{r.epoch != null ? String(r.epoch) : '—'}</td>
                  <td className="mono" style={{ fontSize: 11 }}>{String(r.status)}</td>
                  <td>{r.execution_allowed ? <Pill tone="ok">YES</Pill> : <Pill tone="neutral">NO</Pill>}</td>
                  <td className="mono">{r.issue ? `#${r.issue}` : '—'}{r.pr ? ` / #${r.pr}` : ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <Empty>无执行路线</Empty>}

      <div className="banner banner-warn" style={{ marginTop: 20 }}>
        <IconWarn size={16} />
        <div>
          <b>派发（Dispatch）尚未启用。</b>
          <span className="muted"> Phase 1 为只读。点击派发需经控制塔校验 route / claim / lease / collision / reservation，属 Phase 2；自动启动属 Phase 3（需 Host Broker canary 证明）。</span>
        </div>
      </div>

      {prov && <ProvenancePanel meta={prov} onClose={() => setProv(null)} />}
    </div>
  )
}
