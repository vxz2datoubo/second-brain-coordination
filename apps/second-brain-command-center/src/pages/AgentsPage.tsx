import { Card, SectionTitle, Badge, Empty, Pill, Provenance } from '../components/ui'
import { IconAgent, IconWarn } from '../components/Icons'
import { useAgents } from '../hooks'
import { livenessLabel, toneVar } from '../semantics'

export default function AgentsPage() {
  const agents = useAgents()

  return (
    <div>
      <SectionTitle>施工者 · Agents / Workers</SectionTitle>

      <div className="banner banner-warn">
        <IconWarn size={16} />
        <div>
          <b>绝不从 PID 或心跳判定“正在施工”。</b>
          <span className="muted"> 活跃状态必须基于任务级证据（route 状态、model turn、tool calls、文件 diff、测试变化、checkpoint）。下面展示的 liveness 来自 ACTIVE-* 真源的任务状态，并显式标注推断依据。</span>
        </div>
      </div>

      {agents.loading && <div className="loading">读取施工者状态…</div>}
      {agents.error && <div className="error-box">{agents.error}</div>}
      {agents.data && agents.data.length === 0 && <Empty>当前无施工者路线</Empty>}

      <div className="grid-2">
        {agents.data?.map((a) => {
          const label = livenessLabel[a.liveness]
          const tone = toneVar[label.tone]
          return (
            <Card key={a.agent_id}>
              <div className="row" style={{ justifyContent: 'space-between' }}>
                <div className="row" style={{ gap: 8 }}>
                  <span className="pc-icon" style={{ width: 32, height: 32, color: tone.fg, background: tone.bg }}>
                    <IconAgent size={18} />
                  </span>
                  <b>{a.agent_id}</b>
                </div>
                <Badge label={label} />
              </div>
              <div className="kv" style={{ marginTop: 12, gridTemplateColumns: '88px 1fr' }}>
                <dt>角色</dt><dd>{a.role || '—'}</dd>
                <dt>任务</dt><dd className="mono" style={{ fontSize: 11 }}>{a.task_id || '—'}</dd>
                <dt>模型</dt><dd className="mono">{a.model || '—'}</dd>
                <dt>载具</dt><dd className="mono">{a.carrier || '—'}</dd>
                <dt>分支</dt><dd className="mono" style={{ fontSize: 11 }}>{a.branch || '—'}</dd>
                <dt>判定依据</dt><dd className="muted">{a.liveness_reason || '—'}</dd>
              </div>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
