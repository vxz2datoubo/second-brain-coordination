import { useCallback, useEffect, useState } from 'react'
import { Routes, Route, NavLink, useNavigate } from 'react-router-dom'
import {
  IconHome, IconGrid, IconTower, IconTask, IconAgent, IconHealth,
  IconRefresh, IconBrain, IconChart, IconFilm, IconCamera, IconWarn, IconClock,
} from './components/Icons'
import { useHealth, useSystem, useProjects } from './hooks'
import { bumpRefresh } from './refreshBus'
import HomePage from './pages/HomePage'
import ProjectPage from './pages/ProjectPage'
import ControlTowerPage from './pages/ControlTowerPage'
import TasksPage from './pages/TasksPage'
import AgentsPage from './pages/AgentsPage'
import HealthPage from './pages/HealthPage'

const PROJECT_NAV = [
  { id: 'SECOND_BRAIN', label: '第二大脑', Icon: IconBrain },
  { id: 'TRADING_SYSTEM', label: '交易系统', Icon: IconChart },
  { id: 'REALTIME_INTERACTIVE_FILM_GAME', label: '实时互动电影', Icon: IconFilm },
  { id: 'AI_DIRECTOR', label: 'AI导演', Icon: IconCamera },
]

function healthColor(s: string) {
  if (s === 'OK') return 'var(--ok)'
  if (s === 'DEGRADED') return 'var(--warn)'
  if (s === 'UNAVAILABLE') return 'var(--bad)'
  return 'var(--neutral)'
}

export default function App() {
  const nav = useNavigate()
  const health = useHealth()
  const system = useSystem()
  const projects = useProjects()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<number | null>(null)

  // Single top-level entry point (iron rule 9). bumpRefresh() fans out to EVERY
  // mounted hook instance — App's own AND every page's — so one click updates
  // the whole UI. Each hook also keeps its local reload() for focused use.
  const refreshAll = useCallback(() => {
    setRefreshing(true)
    bumpRefresh()
    health.reload(); system.reload(); projects.reload()
    setLastRefresh(Date.now())
    setTimeout(() => setRefreshing(false), 600)
  }, [health, system, projects])

  // Keyboard shortcut R / Ctrl+R-ish affordance: press "r" to refresh (when not typing).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null
      const typing = el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)
      if (!typing && (e.key === 'r' || e.key === 'R') && !e.ctrlKey && !e.metaKey && !e.altKey) {
        refreshAll()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [refreshAll])

  const repo = system.data?.repos?.find((r) => r.repo.includes('second-brain-coordination'))
  const lastRefreshLabel = lastRefresh
    ? new Date(lastRefresh).toLocaleTimeString('zh-CN', { hour12: false })
    : null

  return (
    <div className="shell">
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`} aria-label="主导航">
        <div className="brand">
          <div className="brand-name">洛雪认知控制中心</div>
          <div className="brand-sub">Second Brain Command Center · Phase 1</div>
        </div>
        <nav className="nav">
          <div className="nav-group">
            <NavLink to="/" end className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
              <IconHome size={18} /> 首页总览
            </NavLink>
          </div>
          <div className="nav-group">
            <div className="nav-group-label">项目 PROJECTS</div>
            {PROJECT_NAV.map(({ id, label, Icon }) => (
              <NavLink key={id} to={`/projects/${id}`} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}>
                <Icon size={18} /> {label}
              </NavLink>
            ))}
          </div>
          <div className="nav-group">
            <div className="nav-group-label">全局 GLOBAL</div>
            <NavLink to="/control-tower" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}><IconTower size={18} /> 控制塔</NavLink>
            <NavLink to="/tasks" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}><IconTask size={18} /> 任务</NavLink>
            <NavLink to="/agents" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}><IconAgent size={18} /> 施工者</NavLink>
            <NavLink to="/health" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`} onClick={() => setSidebarOpen(false)}><IconHealth size={18} /> 系统健康</NavLink>
          </div>
        </nav>
      </aside>

      <div className="main">
        <header className="topbar">
          <button className="btn-icon hamburger" onClick={() => setSidebarOpen((o) => !o)} aria-label="切换导航">☰</button>
          <span className="topbar-title">洛雪认知系统</span>

          <div className="topbar-health">
            {(health.data?.components ?? []).map((c) => (
              <span className="health-dot" key={c.component} title={c.detail ?? ''}>
                <i style={{ background: healthColor(c.status) }} />
                {c.component}
              </span>
            ))}
            {health.loading && <span className="health-dot"><i style={{ background: 'var(--neutral)' }} />检测中…</span>}
          </div>

          <div className="topbar-spacer" />

          {repo && (
            <div className="repo-mini" title={`本地 ${repo.local_sha} · 远端 ${repo.remote_main_sha}`}>
              <IconWarn size={12} style={{ display: repo.sync_state === 'SYNCED' ? 'none' : 'inline' }} />
              <span>{repo.sync_state === 'SYNCED' ? '已同步' : repo.sync_state}</span>
              <span className="mono">{repo.local_sha?.slice(0, 8)}</span>
              {repo.behind > 0 && <span className="mono">↓{repo.behind}</span>}
              {repo.ahead > 0 && <span className="mono">↑{repo.ahead}</span>}
            </div>
          )}

          {lastRefreshLabel && (
            <span className="refresh-stamp" title="本页数据最后一次拉取的时间（数据时点见各卡片来源）">
              <IconClock size={12} /> {lastRefreshLabel} 已更新
            </span>
          )}

          <button className="btn" onClick={refreshAll} title="刷新全部数据（手动刷新，非高频轮询）· 快捷键 R">
            <IconRefresh size={15} className={refreshing ? 'spin' : ''} />
            {refreshing ? '刷新中…' : '刷新'}
          </button>
        </header>

        <main className="content">
          <Routes>
            <Route path="/" element={<HomePage onRefresh={refreshAll} />} />
            <Route path="/projects/:projectId" element={<ProjectPage />} />
            <Route path="/control-tower" element={<ControlTowerPage />} />
            <Route path="/tasks" element={<TasksPage />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/health" element={<HealthPage />} />
            <Route path="*" element={<div className="empty">页面不存在 · <span className="hover-link" onClick={() => nav('/')}>返回首页</span></div>} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
