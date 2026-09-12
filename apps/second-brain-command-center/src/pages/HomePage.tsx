import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, SectionTitle, Badge, Provenance, ProvenancePanel, sha, KeyVal, Empty, Pill } from '../components/ui'
import { ICONS, IconChevron, IconWarn, IconShield } from '../components/Icons'
import { useProjects, useControlTower, useSystem, useTasks } from '../hooks'
import { projectStateLabel, taskStateLabel, PROJECT_ICON, toneVar } from '../semantics'
import type { Meta, ProjectSummary } from '../types'

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

      {/* ---- 今天要处理 / priorities from real state ---- */}
      <SectionTitle right={<span className="muted">数据来自真实项目注册表与控制塔</span>}>
        当前系统概览
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
