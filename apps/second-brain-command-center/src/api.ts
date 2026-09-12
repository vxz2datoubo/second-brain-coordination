/**
 * API client — talks only to the local thin BFF (/api).
 * The browser NEVER holds credentials. No secrets in client storage.
 */
import type {
  Envelope, ProjectSummary, ProjectDetail, TaskView, AgentView,
  ControlTowerSummary, SystemHealth, SystemTop,
} from './types'

const BASE = '/api'

async function get<T>(path: string): Promise<Envelope<T>> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  })
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch { /* ignore */ }
    throw new ApiError(detail, res.status)
  }
  return res.json() as Promise<Envelope<T>>
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export const api = {
  health: () => get<SystemHealth>('/health'),
  system: () => get<SystemTop>('/system'),
  projects: () => get<ProjectSummary[]>('/projects'),
  project: (id: string) => get<ProjectDetail>(`/projects/${id}`),
  tasks: () => get<TaskView[]>('/tasks'),
  agents: () => get<AgentView[]>('/agents'),
  controlTower: () => get<ControlTowerSummary>('/control-tower'),
}
