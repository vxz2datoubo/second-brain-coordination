import { useState } from 'react'
import { Card, SectionTitle, Badge, Provenance, ProvenancePanel, Empty, Pill } from '../components/ui'
import { IconTask } from '../components/Icons'
import { useTasks } from '../hooks'
import { taskStateLabel, toneVar } from '../semantics'
import type { Meta, TaskView } from '../types'

function TaskDetail({ t, onProv }: { t: TaskView; onProv: (m: Meta) => void }) {
  return (
    <Card>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <Badge label={taskStateLabel[t.state]} />
        <Provenance meta={t.meta} onOpen={onProv} />
      </div>
      <h3 style={{ margin: '10px 0 6px', fontSize: 14 }} className="mono">{t.task_id}</h3>
      <div className="kv" style={{ gridTemplateColumns: '96px 1fr' }}>
        <dt>执行者</dt><dd>{t.executor ? <Pill tone="accent">{t.executor}</Pill> : '—'}</dd>
        <dt>载具</dt><dd className="mono">{t.carrier || '—'}</dd>
        <dt>模型</dt><dd className="mono">{t.model || '—'}</dd>
        <dt>epoch</dt><dd className="mono">{t.route_epoch ?? '—'}</dd>
        <dt>Issue / PR</dt><dd className="mono">{t.issue ? `#${t.issue}` : '—'}{t.pr ? ` / #${t.pr}` : ''}</dd>
        <dt>分支</dt><dd className="mono" style={{ fontSize: 11 }}>{t.branch || '—'}</dd>
        {t.exact_head && <><dt>exact head</dt><dd className="mono" style={{ fontSize: 11 }}>{t.exact_head.slice(0, 12)}</dd></>}
        {t.next_gate && <><dt>下一门</dt><dd className="mono" style={{ fontSize: 11 }}>{t.next_gate}</dd></>}
        {t.blocker && <><dt>阻塞</dt><dd style={{ color: 'var(--bad)' }}>{t.blocker}</dd></>}
        <dt>可执行</dt><dd>{t.execution_allowed ? <Pill tone="ok">YES</Pill> : <Pill tone="neutral">NO</Pill>}</dd>
        <dt>原始状态</dt><dd className="mono" style={{ fontSize: 11 }}>{t.raw_status || '—'}</dd>
      </div>
    </Card>
  )
}

function MissionCard({ t }: { t: TaskView }) {
  return (
    <Card>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <b style={{ fontSize: 14 }}>{t.executor} 正在做的事</b>
        <Badge label={taskStateLabel[t.state]} />
      </div>
      <div className="kv" style={{ marginTop: 12, gridTemplateColumns: '88px 1fr' }}>
        <dt>任务</dt><dd className="mono" style={{ fontSize: 12 }}>{t.task_id}</dd>
        <dt>为什么做</dt><dd>{t.why || '（由任务 mode_label 提供）'}</dd>
        <dt>谁在做</dt><dd>{t.executor}</dd>
        <dt>模型</dt><dd className="mono">{t.model || '—'}</dd>
        <dt>现在</dt><dd>{t.state}</dd>
        <dt>下一步</dt><dd className="mono" style={{ fontSize: 11 }}>{t.next_gate || '—'}</dd>
      </div>
    </Card>
  )
}

export default function TasksPage() {
  const tasks = useTasks()
  const [prov, setProv] = useState<Meta | null>(null)
  const [view, setView] = useState<'kanban' | 'table'>('kanban')

  const groups = ['READY', 'DISPATCHED', 'RUNNING', 'REVIEW', 'BLOCKED', 'PAUSED', 'DONE', 'PLANNED', 'OUTCOME_UNKNOWN']

  return (
    <div>
      <SectionTitle right={
        <div className="row" style={{ gap: 6 }}>
          <button className={`btn ${view === 'kanban' ? 'btn-primary' : ''}`} onClick={() => setView('kanban')}>看板</button>
          <button className={`btn ${view === 'table' ? 'btn-primary' : ''}`} onClick={() => setView('table')}>表格</button>
        </div>
      }>任务 · Tasks</SectionTitle>

      {tasks.loading && <div className="loading">读取任务…</div>}
      {tasks.error && <div className="error-box">{tasks.error}</div>}
      {tasks.data && tasks.data.length === 0 && <Empty>当前无活跃任务（来自 ACTIVE-* 真源）</Empty>}

      {tasks.data && view === 'kanban' && (
        <>
          <SectionTitle>推荐视角 · Mission 卡片</SectionTitle>
          <div className="grid-2">
            {tasks.data.map((t) => <MissionCard key={t.task_id} t={t} />)}
          </div>
          <SectionTitle>全部任务</SectionTitle>
          <div className="grid-2">
            {tasks.data.map((t) => <TaskDetail key={t.task_id} t={t} onProv={setProv} />)}
          </div>
        </>
      )}

      {tasks.data && view === 'table' && (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>状态</th><th>执行者</th><th>task_id</th><th>模型</th><th>Issue/PR</th><th>下一门</th></tr></thead>
            <tbody>
              {tasks.data.map((t) => (
                <tr key={t.task_id}>
                  <td><Badge label={taskStateLabel[t.state]} /></td>
                  <td>{t.executor}</td>
                  <td className="mono" style={{ fontSize: 11 }}>{t.task_id}</td>
                  <td className="mono" style={{ fontSize: 11 }}>{t.model || '—'}</td>
                  <td className="mono">{t.issue ? `#${t.issue}` : '—'}{t.pr ? ` / #${t.pr}` : ''}</td>
                  <td className="mono" style={{ fontSize: 11 }}>{t.next_gate || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="banner banner-info" style={{ marginTop: 20 }}>
        <IconTask size={16} />
        <div className="muted">
          任务状态严格来自 ACTIVE-* 真源与项目泳道。<b>IDEA → MISSION → AUTHORIZED TASK</b> 是三个不同阶段，本页只展示已授权的任务。
        </div>
      </div>

      {prov && <ProvenancePanel meta={prov} onClose={() => setProv(null)} />}
    </div>
  )
}
