/**
 * Data hooks — thin wrappers over the BFF with manual refresh support.
 * Prefer manual refresh over high-frequency polling (Owner preference).
 * All fetches carry freshness/provenance back to the UI.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from './api'
import type {
  AgentView, ControlTowerSummary, Meta, ProjectDetail, ProjectSummary,
  SystemHealth, SystemTop, TaskView, Envelope,
} from './types'

export interface AsyncState<T> {
  data: T | null
  meta: Meta | null
  loading: boolean
  error: string | null
  reload: () => void
  lastLoadedAt: number | null
}

export function useAsync<T>(
  fetcher: () => Promise<Envelope<T>>,
  deps: unknown[] = [],
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null)
  const [meta, setMeta] = useState<Meta | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastLoadedAt, setLastLoadedAt] = useState<number | null>(null)
  const [tick, setTick] = useState(0)
  const alive = useRef(true)

  useEffect(() => { alive.current = true; return () => { alive.current = false } }, [])

  useEffect(() => {
    setLoading(true); setError(null)
    fetcher()
      .then((env) => {
        if (!alive.current) return
        setData(env.data); setMeta(env.meta); setLastLoadedAt(Date.now())
      })
      .catch((e: unknown) => {
        if (!alive.current) return
        setError(e instanceof ApiError ? e.message : String(e))
      })
      .finally(() => { if (alive.current) setLoading(false) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick, ...deps])

  const reload = useCallback(() => setTick((t) => t + 1), [])
  return { data, meta, loading, error, reload, lastLoadedAt }
}

/* ---- typed convenience hooks ---- */
export const useHealth = (): AsyncState<SystemHealth> => useAsync(api.health)
export const useSystem = (): AsyncState<SystemTop> => useAsync(api.system)
export const useProjects = (): AsyncState<ProjectSummary[]> => useAsync(api.projects)
export const useTasks = (): AsyncState<TaskView[]> => useAsync(api.tasks)
export const useAgents = (): AsyncState<AgentView[]> => useAsync(api.agents)
export const useControlTower = (): AsyncState<ControlTowerSummary> => useAsync(api.controlTower)

export function useProject(id: string, extraDeps: unknown[] = []): AsyncState<ProjectDetail> {
  return useAsync(() => api.project(id), [id, ...extraDeps])
}
