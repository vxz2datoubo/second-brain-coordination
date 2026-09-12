import { useState } from 'react'
import {
  Card, SectionTitle, Badge, Provenance, ProvenancePanel, Empty, Pill, sha,
  PlainAnswer, BarChart, TrafficRow,
} from '../components/ui'
import { IconWarn, IconTower } from '../components/Icons'
import { useControlTower } from '../hooks'
import { taskStateLabel, toneVar } from '../semantics'
import type { Meta, TaskState } from '../types'

export default function ControlTowerPage() {
  const ct = useControlTower()
  const [prov, setProv] = useState<Meta | null>(null)

  if (ct.loading) return <div className="loading">正在读取控制塔…</div>
  if (ct.error) return <div className="error-box">控制塔不可用：{ct.error}</div>
  const d = ct.data
  if (!d) return <Empty>无控制塔数据</Empty>

  const order: TaskState[] = ['READY', 'DISPATCHED', 'RUNNING', 'REVIEW', 'CANONICALIZATION', 'BLOCKED', 'STALLED', 'OUTCOME_UNKNOWN', 'OWNER_GATE', 'DONE', 'PAUSED', 'PLANNED']

  const total = Object.values(d.counts).reduce((a, b) => a + (b ?? 0), 0)
  const running = (d.counts.RUNNING ?? 0) + (d.counts.DISPATCHED ?? 0)
  const waitingYou = (d.counts.OWNER_GATE ?? 0) + (d.counts.BLOCKED ?? 0) + (d.counts.OUTCOME_UNKNOWN ?? 0)
  const barRows = order
    .filter((k) => (d.counts[k] ?? 0) > 0)
    .map((k) => ({ label: taskStateLabel[k]?.zh ?? k, value: d.counts[k] ?? 0, tone: taskStateLabel[k]?.tone ?? ('neutral' as const) }))
    .sort((a, b) => b.value - a.value)

  return (
    <div>
      <SectionTitle right={
        <span className="row" style={{ gap: 10 }}>
          {d.projection_as_of && <span className="muted">数据时点 {d.projection_as_of}</span>}
          <Provenance meta={ct.meta ?? ({} as Meta)} onOpen={setProv} />
        </span>
      }>控制塔 · Control Tower</SectionTitle>

      {/* 人话版结论 */}
      <PlainAnswer tone={waitingYou > 0 ? 'warn' : running > 0 ? 'accent' : 'ok'} icon={<IconTower size={18} />}>
        {waitingYou > 0
          ? <><b>有 {waitingYou} 个任务在等人处理</b>，{running} 个在跑，当前共 {total} 个任务。</>
          : <><b>没有卡住的任务，{running} 个任务正在跑</b>，当前共 {total} 个任务。</>}
        <span className="muted"> 控制塔才是执行权威，本页只是它的一张快照。</span>
      </PlainAnswer>

      <div className="grid-2" style={{ marginTop: 16 }}>
        <Card>
          <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>任务状态分布（看得懂版）</h3>
          <BarChart rows={barRows} emptyHint="当前没有活跃任务" />
        </Card>
        <Card>
          <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>一眼看重点</h3>
          <TrafficRow items={[
            { label: '执行中', tone: running > 0 ? 'ok' : 'neutral', value: running },
            { label: '等你决定', tone: waitingYou > 0 ? 'warn' : 'ok', value: waitingYou },
            { label: '等待验算', tone: (d.counts.REVIEW ?? 0) > 0 ? 'review' : 'neutral', value: d.counts.REVIEW ?? 0 },
            { label: '已入正史', tone: 'neutral', value: d.counts.DONE ?? 0 },
          ]} />
          <div className="muted" style={{ fontSize: 11.5, marginTop: 12 }}>
            绿色=正常，紫色=等验算，黄色=需你留意，红色=要处理。
          </div>
        </Card>
      </div>

      <SectionTitle>状态明细（原始英文状态，供对照）</SectionTitle>
      <div className="ct-strip">
        {order.map((k) => {
          const v = d.counts[k] ?? 0
          const lab = taskStateLabel[k]
          return (
            <div key={k} className="ct-cell" style={{ opacity: v === 0 ? 0.45 : 1 }}>
              <div className="ct-count" style={{ color: v === 0 ? 'var(--text-3)' : toneVar[lab?.tone ?? 'neutral'].fg }}>{v}</div>
              <div className="ct-label">{lab?.zh ?? k}</div>
              <div className="ct-label mono" style={{ fontSize: 10, opacity: 0.7 }}>{lab?.en ?? k}</div>
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
