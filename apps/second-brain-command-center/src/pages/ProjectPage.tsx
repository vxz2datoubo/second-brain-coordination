import { Fragment, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card, SectionTitle, Badge, Provenance, ProvenancePanel, KeyVal, Empty, Pill, sha,
  PlainAnswer, Tile, TrafficRow,
} from '../components/ui'
import { IconChevron, IconWarn, IconGit, IconAgent, IconTask, IconShield } from '../components/Icons'
import { useProject, useTasks, useAgents } from '../hooks'
import { projectStateLabel, taskStateLabel, livenessLabel, toneVar } from '../semantics'
import type { Meta } from '../types'

/** One-glance "what's this project doing right now" panel, in plain Chinese. */
function ProjectPulse({
  state, phase, executor, nextGate, blocker, tradingAuth, issue, pr,
}: {
  state: keyof typeof projectStateLabel
  phase?: string | null
  executor?: string | null
  nextGate?: string | null
  blocker?: string | null
  tradingAuth?: boolean | null
  issue?: number | string | null
  pr?: number | string | null
}) {
  const label = projectStateLabel[state]
  const tone = label.tone
  let sentence: React.ReactNode
  if (state === 'ACTIVE') {
    sentence = (
      <>
        <b>这个项目正在推进中</b>{executor ? <>，当前由 <b>{executor}</b> 负责</> : null}
        {nextGate ? <>，下一步要过「{nextGate}」这道门</> : null}。
      </>
    )
  } else if (state === 'PAUSED') {
    sentence = <><b>这个项目当前暂停了</b>，没有正在进行的施工。</>
  } else if (state === 'BLOCKED') {
    sentence = <><b>这个项目卡住了</b>{blocker ? <>：{blocker}</> : null}。</>
  } else {
    sentence = <>当前状态：<b>{label.zh}</b>。</>
  }
  return (
    <div className="stack" style={{ gap: 12 }}>
      <PlainAnswer tone={tone} icon={<IconGit size={18} />}>{sentence}</PlainAnswer>
      <div className="tile-row">
        <Tile label="项目状态" value={label.zh} sub={label.en} tone={tone} />
        <Tile label="当前阶段" value={phase || '—'} tone="neutral" />
        <Tile label="负责人" value={executor || '暂无'} sub={executor ? '正在施工' : '无活跃施工者'} tone={executor ? 'accent' : 'neutral'} icon={<IconAgent size={14} />} />
        <Tile label="下一步门" value={nextGate || '—'} tone="review" icon={<IconTask size={14} />} />
      </div>
      <TrafficRow items={[
        { label: '交易权限', tone: tradingAuth === false ? 'ok' : 'neutral', value: tradingAuth === false ? '只读研究' : '—' },
        { label: 'Issue', tone: issue != null ? 'accent' : 'neutral', value: issue != null ? `#${issue}` : '—' },
        { label: 'PR', tone: pr != null ? 'accent' : 'neutral', value: pr != null ? `#${pr}` : '—' },
      ]} />
    </div>
  )
}

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
        <button className="btn" onClick={proj.reload}>刷新本页</button>
      }>
        <span className="row" style={{ gap: 10 }}>
          {p.display_name}
          <Badge label={label} />
        </span>
      </SectionTitle>

      {/* 人话版：一眼看清这个项目在干嘛 */}
      <ProjectPulse
        state={p.state} phase={p.phase} executor={p.active_executor}
        nextGate={p.next_gate} blocker={p.blocker}
        tradingAuth={p.trading_authorized} issue={p.issue} pr={p.pr}
      />

      <SectionTitle>详细资料</SectionTitle>
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
