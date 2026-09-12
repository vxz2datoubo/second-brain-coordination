import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card, SectionTitle, Badge, Provenance, ProvenancePanel, sha, KeyVal, Empty, Pill,
  PlainAnswer, Tile, BarChart, TrafficRow,
} from '../components/ui'
import { ICONS, IconChevron, IconWarn, IconShield, IconTower, IconGit, IconAgent } from '../components/Icons'
import { useProjects, useControlTower, useSystem, useTasks, useAgents } from '../hooks'
import { projectStateLabel, taskStateLabel, PROJECT_ICON, toneVar } from '../semantics'
import type { Meta, ProjectSummary, TaskState } from '../types'

function ProjectCard({ p, onOpen, onProv }: {
  p: ProjectSummary; onOpen: () => void; onProv: (m: Meta) => void
}) {
  const label = projectStateLabel[p.state]
  const Icon = ICONS[PROJECT_ICON[p.project_id] ?? 'brain'] ?? ICONS.brain
  const t = toneVar[label.tone]
  return (
    <Card onClick={onOpen} ariaLabel={`打开 ${p.display_name}`} className="pc-card">
      <div className="pc-head">
        <div className="pc-icon" style={{ color: t.fg, background: t.bg }}><Icon size={22} /></div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="pc-name">{p.display_name}</div>
          <div className="pc-id">{p.project_id}</div>
        </div>
        <Badge label={label} />
      </div>

      <div className="pc-mission">{p.mission || '（暂无 mission）'}</div>

      <div className="pc-rows">
        <KeyVal k="阶段" v={p.phase || '—'} mono />
        <KeyVal k="施工者" v={p.active_executor ? <Pill tone="accent">{p.active_executor}</Pill> : '—'} />
        <KeyVal k="当前任务" v={<span className="mono" style={{ fontSize: 11.5 }}>{p.current_task || '—'}</span>} />
        <KeyVal k="下一步门" v={<span className="mono" style={{ fontSize: 11.5 }}>{p.next_gate || '—'}</span>} />
        {p.issue != null && <KeyVal k="Issue / PR" v={<span className="mono">#{p.issue}{p.pr ? ` / #${p.pr}` : ''}</span>} />}
        {p.blocker && <KeyVal k="阻塞" v={<span style={{ color: 'var(--bad)' }}>{p.blocker}</span>} />}
      </div>

      <div className="pc-actions">
        <Provenance meta={p.meta} onOpen={onProv} />
        <span className="row" style={{ gap: 4, color: 'var(--text-2)', fontSize: 12 }}>
          进入项目 <IconChevron size={14} />
        </span>
      </div>
    </Card>
  )
}

function ControlTowerStrip() {
  const nav = useNavigate()
  const ct = useControlTower()
  const order = ['READY', 'DISPATCHED', 'RUNNING', 'REVIEW', 'CANONICALIZATION', 'BLOCKED', 'STALLED', 'OUTCOME_UNKNOWN', 'OWNER_GATE', 'DONE', 'PAUSED', 'PLANNED']
  return (
    <div className="ct-strip">
      {ct.loading && <div className="muted">读取控制塔…</div>}
      {ct.error && <Empty>控制塔不可用：{ct.error}</Empty>}
      {ct.data && order.filter((k) => (ct.data!.counts[k] ?? 0) > 0).map((k) => {
        const label = taskStateLabel[k as keyof typeof taskStateLabel]
        const tone = label ? toneVar[label.tone] : toneVar.neutral
        return (
          <button key={k} className="ct-cell" onClick={() => nav('/tasks')} aria-label={`${label?.zh ?? k} 任务`}>
            <div className="ct-count" style={{ color: tone.fg }}>{ct.data!.counts[k]}</div>
            <div className="ct-label">{label?.zh ?? k}</div>
          </button>
        )
      })}
      {ct.data && order.every((k) => (ct.data!.counts[k] ?? 0) === 0) && (
        <div className="muted">当前无活动任务状态</div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ *
 *  SituationReport — the "speak like a human" summary.
 *
 *  Leads with ONE plain sentence answering "现在到底怎么样了？", then
 *  shows the same truth as big colour tiles + a bar chart instead of a
 *  wall of terminology. Detailed/technical views stay further down the
 *  page and behind the provenance drawer.
 * ------------------------------------------------------------------ */
function SituationReport({ onProv }: { onProv: (m: Meta) => void }) {
  const projects = useProjects()
  const tasks = useTasks()
  const agents = useAgents()
  const ct = useControlTower()
  const system = useSystem()

  const loading = projects.loading || tasks.loading || ct.loading
  const ps = projects.data ?? []
  const ts = tasks.data ?? []

  // -- plain counts -------------------------------------------------
  const working = ps.filter((p) => p.state === 'ACTIVE').length
  const paused = ps.filter((p) => p.state === 'PAUSED').length
  const stuck = ps.filter((p) => p.state === 'BLOCKED').length

  const needYou = ts.filter((t) =>
    t.state === 'OWNER_GATE' || t.state === 'BLOCKED' || t.state === 'OUTCOME_UNKNOWN').length
  const inProgress = ts.filter((t) =>
    t.state === 'DISPATCHED' || t.state === 'RUNNING').length
  const waitingGate = ts.filter((t) =>
    t.state === 'REVIEW' || t.state === 'CANONICALIZATION').length

  const activeAgents = (agents.data ?? []).filter((a) => a.liveness === 'AGENT_ACTIVE' || a.liveness === 'MEANINGFUL_PROGRESS').length

  const repo = system.data?.repos?.find((r) => r.repo.includes('second-brain-coordination'))
  const syncOk = repo?.sync_state === 'SYNCED'

  // -- dominant tasks as a bar chart (plain Chinese labels) ---------
  const counts = ct.data?.counts ?? {}
  const barRows = (Object.keys(counts) as TaskState[])
    .filter((k) => (counts[k] ?? 0) > 0)
    .map((k) => ({
      label: taskStateLabel[k]?.zh ?? k,
      value: counts[k] ?? 0,
      tone: taskStateLabel[k]?.tone ?? ('neutral' as const),
    }))
    .sort((a, b) => b.value - a.value)

  if (loading && ps.length === 0) return <div className="loading">正在读取真实状态…</div>

  // -- the one-line answer -----------------------------------------
  let headline: React.ReactNode
  let tone: 'ok' | 'warn' | 'bad' | 'accent' = 'ok'
  if (needYou > 0) {
    tone = 'warn'
    headline = (
      <>
        <b>有 {needYou} 件事在等你拍板</b>，{working} 个项目正在推进
        {inProgress > 0 ? <>，{inProgress} 个任务在跑</> : null}。
        <span className="muted"> 往下看标红/标黄的条目，那些是需要你处理的。</span>
      </>
    )
  } else if (stuck > 0) {
    tone = 'bad'
    headline = (
      <>
        <b>{stuck} 个项目卡住了</b>，{working} 个在正常推进。
        <span className="muted"> 没有等你拍板的事，但卡住的需要看看原因。</span>
      </>
    )
  } else if (working > 0) {
    tone = 'accent'
    headline = (
      <>
        <b>一切正常，{working} 个项目在推进，暂时没有需要你出手的事。</b>
        {inProgress > 0 ? <span className="muted"> 当前 {inProgress} 个任务在处理中。</span> : null}
      </>
    )
  } else {
    headline = <><b>系统当前比较安静</b>，没有项目在推进，也没有待办。</>
  }

  return (
    <div className="stack" style={{ gap: 16 }}>
      <PlainAnswer tone={tone} icon={<IconTower size={18} />}>{headline}</PlainAnswer>

      {/* --- big tiles: the same truth at a glance --- */}
      <div className="tile-row">
        <Tile label="正在推进的项目" value={working} sub={`共 ${ps.length} 个项目`} tone={working > 0 ? 'ok' : 'neutral'} icon={<IconGit size={14} />} />
        <Tile label="正在跑的任务" value={inProgress} sub="已派发 + 执行中" tone={inProgress > 0 ? 'accent' : 'neutral'} />
        <Tile label="等你决定" value={needYou} sub="需你拍板 / 受阻 / 结果不明" tone={needYou > 0 ? 'warn' : 'ok'} />
        <Tile label="在干活的智能体" value={activeAgents} sub="有真实任务证据的" tone={activeAgents > 0 ? 'ok' : 'neutral'} icon={<IconAgent size={14} />} />
      </div>

      <div className="grid-2">
        <Card>
          <h3 style={{ margin: '0 0 4px', fontSize: 14 }}>任务都在什么状态</h3>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
            柱子越长 = 越多任务处于这个状态
          </div>
          <BarChart rows={barRows} emptyHint="当前没有活跃任务" />
        </Card>

        <Card>
          <h3 style={{ margin: '0 0 4px', fontSize: 14 }}>一句话状态灯</h3>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
            绿灯=没事，黄灯=需要注意，红灯=要处理
          </div>
          <TrafficRow items={[
            { label: '项目推进', tone: working > 0 ? 'ok' : 'neutral', value: working },
            { label: '已暂停', tone: paused > 0 ? 'warn' : 'neutral', value: paused },
            { label: '受阻项目', tone: stuck > 0 ? 'bad' : 'ok', value: stuck },
            { label: '等待入库', tone: waitingGate > 0 ? 'review' : 'neutral', value: waitingGate },
            { label: '本地/远端同步', tone: syncOk ? 'ok' : 'warn', value: repo?.sync_state ?? '—' },
          ]} />
          <div style={{ marginTop: 12, display: 'flex', justifyContent: 'flex-end' }}>
            {projects.data?.[0] && <Provenance meta={projects.data[0].meta} onOpen={onProv} />}
          </div>
        </Card>
      </div>
    </div>
  )
}

export default function HomePage({ onRefresh }: { onRefresh: () => void }) {
  const nav = useNavigate()
  const projects = useProjects()
  const system = useSystem()
  const tasks = useTasks()
  const [prov, setProv] = useState<Meta | null>(null)

  const repo = system.data?.repos?.find((r) => r.repo.includes('second-brain-coordination'))
  const syncWarn = repo && repo.sync_state !== 'SYNCED'

  return (
    <div>
      {/* ---- system-level warnings (truthfulness first) ---- */}
      {syncWarn && (
        <div className="banner banner-warn">
          <IconWarn size={16} />
          <div>
            <b>本地与远端未完全同步</b> · 状态 <span className="mono">{repo!.sync_state}</span>
            {repo!.behind > 0 && <> · 远端领先 {repo!.behind} 个提交</>}
            {repo!.ahead > 0 && <> · 本地领先 {repo!.ahead} 个提交</>}
            {repo!.dirty && <> · 有未提交改动</>}。
            <span className="muted"> 0 ahead / 0 behind ≠ 整个系统已同步。</span>
          </div>
        </div>
      )}

      {/* ---- 人话版现状：先给结论，再给图 --- */}
      <SectionTitle right={
        <button className="btn" onClick={onRefresh}>刷新看最新</button>
      }>
        现在怎么样了
      </SectionTitle>
      <SituationReport onProv={setProv} />

      <SectionTitle right={<span className="muted">数据来自真实项目注册表与控制塔 · 点卡片进项目</span>}>
        四个项目
      </SectionTitle>

      {projects.loading && <div className="loading">正在读取项目真源…</div>}
      {projects.error && (
        <div className="error-box">
          无法读取项目：{projects.error}
          <div className="muted" style={{ marginTop: 6 }}>本地仓库与控制塔仍可能可用，请检查后端。</div>
        </div>
      )}

      {projects.data && (
        <>
          <div className="grid-projects">
            {projects.data.map((p) => (
              <ProjectCard key={p.project_id} p={p}
                onOpen={() => nav(`/projects/${p.project_id}`)}
                onProv={setProv} />
            ))}
          </div>
        </>
      )}

      <SectionTitle right={
        <button className="btn" onClick={() => nav('/control-tower')}>查看控制塔详情</button>
      }>控制塔摘要 · Control Tower</SectionTitle>
      <ControlTowerStrip />

      <div className="grid-2" style={{ marginTop: 24 }}>
        <Card>
          <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>仓库同步状态</h3>
          {system.data?.repos?.map((r) => (
            <div key={r.repo} style={{ marginBottom: 14 }}>
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <b className="mono" style={{ fontSize: 12 }}>{r.repo.split('/')[1]}</b>
                <Pill tone={r.sync_state === 'SYNCED' ? 'ok' : r.sync_state === 'DIVERGED' ? 'bad' : 'warn'}>
                  {r.sync_state}
                </Pill>
              </div>
              <div className="kv" style={{ marginTop: 8, gridTemplateColumns: '92px 1fr' }}>
                <dt>本地 main</dt><dd className="mono">{sha(r.local_sha)}</dd>
                <dt>远端 main</dt><dd className="mono">{sha(r.remote_main_sha)}</dd>
                <dt>分支</dt><dd className="mono">{r.branch}</dd>
                <dt>worktrees</dt><dd>{r.worktree_count}{r.dirty ? ` · 脏(${r.untracked} untracked)` : ''}</dd>
              </div>
            </div>
          ))}
          {!system.data && !system.loading && <Empty>仓库状态不可用</Empty>}
        </Card>

        <Card>
          <h3 style={{ margin: '0 0 12px', fontSize: 14 }}>活跃任务路线 · Active Routes</h3>
          {tasks.data?.length ? (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>执行者</th><th>任务</th><th>状态</th><th>Issue</th></tr></thead>
                <tbody>
                  {tasks.data.map((t) => (
                    <tr key={t.task_id}>
                      <td><Pill tone="accent">{t.executor}</Pill></td>
                      <td className="mono" style={{ fontSize: 11 }}>{t.task_id}</td>
                      <td><Badge label={taskStateLabel[t.state]} /></td>
                      <td className="mono">{t.issue != null ? `#${t.issue}` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : <Empty>无活跃任务</Empty>}
        </Card>
      </div>

      <div className="banner banner-info" style={{ marginTop: 20 }}>
        <IconShield size={16} />
        <div>
          <b>只读模式 · Phase 1</b> · 本页面只读取既有真源（GitHub 工程真源 / 控制塔执行权威 / 本地仓库），
          <span className="muted"> UI 状态不是系统真源。派发与自动施工为 Phase 2/3，尚未启用（接口已预留且 fail-closed）。</span>
        </div>
      </div>

      {prov && <ProvenancePanel meta={prov} onClose={() => setProv(null)} />}
    </div>
  )
}
