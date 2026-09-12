import { Card, SectionTitle, Empty, Pill, Provenance, sha } from '../components/ui'
import { useHealth, useSystem } from '../hooks'
import type { HealthComponent } from '../types'

function statusTone(s: HealthComponent['status']): 'ok' | 'warn' | 'bad' | 'neutral' {
  if (s === 'OK') return 'ok'
  if (s === 'DEGRADED') return 'warn'
  if (s === 'UNAVAILABLE') return 'bad'
  return 'neutral'
}

export default function HealthPage() {
  const health = useHealth()
  const system = useSystem()

  return (
    <div>
      <SectionTitle right={<button className="btn" onClick={health.reload}>↻ 刷新</button>}>
        系统健康 · System Health
      </SectionTitle>

      {health.loading && <div className="loading">读取健康状态…</div>}
      {health.error && <div className="error-box">{health.error}</div>}

      {health.data && (
        <>
          <div className="grid-2">
            {health.data.components.map((c) => (
              <Card key={c.component}>
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <b className="mono">{c.component}</b>
                  <Pill tone={statusTone(c.status)}>{c.status}</Pill>
                </div>
                <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>{c.detail || '—'}</div>
                <div className="muted" style={{ marginTop: 4, fontSize: 11 }}>新鲜度 {c.freshness}</div>
              </Card>
            ))}
          </div>

          <SectionTitle>版本 · Versions</SectionTitle>
          <Card>
            <div className="kv" style={{ gridTemplateColumns: '150px 1fr' }}>
              <dt>整体状态</dt><dd><Pill tone={statusTone(health.data.overall === 'OK' ? 'OK' : health.data.overall === 'DEGRADED' ? 'DEGRADED' : 'UNAVAILABLE')}>{health.data.overall}</Pill></dd>
              <dt>前端版本</dt><dd className="mono">{health.data.frontend_version || '—'}</dd>
              <dt>后端版本</dt><dd className="mono">{health.data.backend_version || '—'}</dd>
              <dt>协调仓库 main</dt><dd className="mono">{health.data.coordination_main_sha || '—'}</dd>
            </div>
          </Card>

          <SectionTitle>数据源新鲜度 · Freshness</SectionTitle>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>组件</th><th>状态</th><th>新鲜度</th><th>说明</th></tr></thead>
              <tbody>
                {health.data.components.map((c) => (
                  <tr key={c.component}>
                    <td className="mono">{c.component}</td>
                    <td><Pill tone={statusTone(c.status)}>{c.status}</Pill></td>
                    <td>{c.freshness}</td>
                    <td className="muted" style={{ fontSize: 12 }}>{c.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <SectionTitle>观测指示 · Observability</SectionTitle>
      <Card>
        <div className="kv" style={{ gridTemplateColumns: '170px 1fr' }}>
          <dt>刷新策略</dt><dd>手动刷新优先（避免 GitHub API 与算力浪费）</dd>
          <dt>最后刷新</dt><dd className="mono">{system.data?.last_refresh || '—'}</dd>
          <dt>活跃任务数</dt><dd>{system.data?.active_task_count ?? '—'}</dd>
          <dt>泳道数</dt><dd>{system.data?.lane_count ?? '—'}</dd>
          <dt>GitHub 错误</dt><dd className="mono">{system.data?.github_error || '无'}</dd>
        </div>
      </Card>

      <div className="banner banner-info" style={{ marginTop: 20 }}>
        <div>
          <b>W3 / Host Broker 在本阶段为 UNAVAILABLE（诚实标注）。</b>
          <span className="muted"> 未连接的真实数据源不会被伪造为 healthy，也不会从 Markdown 假装生成真实 memory 状态。</span>
        </div>
      </div>
    </div>
  )
}
