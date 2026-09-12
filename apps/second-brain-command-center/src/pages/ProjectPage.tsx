import { Fragment, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, SectionTitle, Badge, Provenance, ProvenancePanel, KeyVal, Empty, Pill, sha } from '../components/ui'
import { IconChevron, IconWarn, IconGit } from '../components/Icons'
import { useProject, useTasks } from '../hooks'
import { projectStateLabel, taskStateLabel, toneVar } from '../semantics'
import type { Meta } from '../types'

export default function ProjectPage() {
  const { projectId = '' } = useParams()
  const nav = useNavigate()
  const proj = useProject(projectId)
  const tasks = useTasks()
  const [prov, setProv] = useState<Meta | null>(null)

  if (proj.loading) return <div className="loading">正在读取项目 {projectId} …</div>
  if (proj.error) return (
    <div className="error-box">
      无法读取项目：{proj.error}
      <div style={{ marginTop: 8 }}><button className="btn" onClick={() => nav('/')}>返回首页</button></div>
    </div>
  )
  const p = proj.data
  if (!p) return <Empty>项目不存在</Empty>

  const label = projectStateLabel[p.state]
  const myTasks = (tasks.data ?? []).filter((t) => t.project_id === p.project_id)

  return (
    <div>
      <SectionTitle right={
        <button className="btn" onClick={proj.reload}>↻ 刷新本页</button>
      }>
        <span className="row" style={{ gap: 10 }}>
          {p.display_name}
          <Badge label={label} />
        </span>
      </SectionTitle>

      <div className="grid-2">
        <Card>
          <h3 style={{ marginTop: 0, fontSize: 14 }}>项目目标 · Mission</h3>
          <p style={{ color: 'var(--text-1)' }}>{p.mission || '（暂无 mission）'}</p>
          <div className="pc-rows">
            <KeyVal k="阶段" v={p.phase || '—'} mono />
            <KeyVal k="期望状态" v={p.desired_state || '—'} mono />
            <KeyVal k="观测状态" v={p.observed_state || '—'} mono />
            <KeyVal k="成熟度" v={p.lifecycle || '—'} mono />
            <KeyVal k="施工者" v={p.active_executor ? <Pill tone="accent">{p.active_executor}</Pill> : '—'} />
            <KeyVal k="下一步门" v={p.next_gate || '—'} mono />
            {p.trading_authorized === false && <KeyVal k="交易权限" v={<Pill tone="ok">NO_TRADE（研究只读）</Pill>} />}
          </div>
          <div style={{ marginTop: 12 }}><Provenance meta={p.meta} onOpen={setProv} /></div>
        </Card>

        <Card>
          <h3 style={{ marginTop: 0, fontSize: 14 }}>仓库与权威 · Repositories</h3>
          <div className="pc-rows">
            <KeyVal k="协调仓库" v={<span className="mono" style={{ fontSize: 11.5 }}>{p.authority_repo || '—'}</span>} />
            {p.domain_repo && <KeyVal k="领域仓库" v={<span className="mono" style={{ fontSize: 11.5 }}>{p.domain_repo}</span>} />}
            {p.issue != null && <KeyVal k="Issue" v={<span className="mono">#{p.issue}</span>} />}
            {p.pr != null && <KeyVal k="PR" v={<span className="mono">#{p.pr}</span>} />}
          </div>
          <div className="banner banner-info" style={{ marginTop: 12 }}>
            <IconGit size={15} />
            <div className="muted">
              {p.domain_repo
                ? '控制平面与领域仓库分离：本页只投影，不复制领域真源。'
                : '控制平面与执行真源同仓。'}
            </div>
          </div>
        </Card>
      </div>

      {p.collision_domains.length > 0 && (
        <>
          <SectionTitle>碰撞域 · Collision Domains（来自项目适配器）</SectionTitle>
          <div className="tag-list">
            {p.collision_domains.map((c) => <Pill key={c} tone="neutral">{c}</Pill>)}
          </div>
        </>
      )}

      {p.hard_boundaries.length > 0 && (
        <>
          <SectionTitle>硬边界 · Hard Boundaries</SectionTitle>
          <ul style={{ color: 'var(--text-1)', fontSize: 12.5, lineHeight: 1.9 }}>
            {p.hard_boundaries.map((b) => <li key={b}><span className="mono">{b}</span></li>)}
          </ul>
        </>
      )}

      <SectionTitle>本项目任务 · Tasks</SectionTitle>
      {myTasks.length ? (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>任务</th><th>执行者</th><th>状态</th><th>模型</th><th>Issue/PR</th><th>门</th></tr></thead>
            <tbody>
              {myTasks.map((t) => (
                <tr key={t.task_id}>
                  <td className="mono" style={{ fontSize: 11 }}>{t.task_id}</td>
                  <td>{t.executor}</td>
                  <td><Badge label={taskStateLabel[t.state]} /></td>
                  <td className="mono" style={{ fontSize: 11 }}>{t.model || '—'}</td>
                  <td className="mono">{t.issue ? `#${t.issue}` : '—'}{t.pr ? ` / #${t.pr}` : ''}</td>
                  <td className="mono" style={{ fontSize: 11 }}>{t.next_gate || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <Empty>本项目当前无关联活跃任务</Empty>}

      {p.relationships.length > 0 && (
        <>
          <SectionTitle>关系 · Relationships（跨项目/工具接口）</SectionTitle>
          <div className="grid-2">
            {p.relationships.map((r, i) => (
              <Card key={i}>
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <Pill tone="review">{String(r.kind)}</Pill>
                </div>
                <div className="kv" style={{ marginTop: 10, gridTemplateColumns: '110px 1fr' }}>
                  {Object.entries(r).filter(([k]) => k !== 'kind').map(([k, v]) => (
                    <Fragment key={k}>
                      <dt>{k}</dt>
                      <dd className="mono" style={{ fontSize: 11 }}>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</dd>
                    </Fragment>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </>
      )}

      <div className="banner banner-info" style={{ marginTop: 24 }}>
        <IconChevron size={15} />
        <div>
          <b>candidate ≠ canonical ≠ active</b> ·
          <span className="muted"> 本项目适配器状态：{p.adapter_status || '—'}。仅当独立验收并 canonical 后才视为系统真源。</span>
        </div>
      </div>

      {prov && <ProvenancePanel meta={prov} onClose={() => setProv(null)} />}
    </div>
  )
}
