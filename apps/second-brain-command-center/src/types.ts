/**
 * UI ViewModel types — projections of existing authorities.
 * These mirror the BFF schema. They are NOT canonical schemas.
 */

export type Freshness = 'FRESH' | 'AGING' | 'STALE' | 'UNKNOWN'
export type Trust =
  | 'CANONICAL' | 'CANDIDATE' | 'RUNTIME_OBSERVED'
  | 'DERIVED' | 'HISTORICAL' | 'UNKNOWN'

export interface SourceRef {
  kind: string
  repo?: string | null
  ref?: string | null
  path?: string | null
  url?: string | null
  detail?: string | null
}

export interface Meta {
  observed_at: string
  freshness: Freshness
  authority: string
  trust: Trust
  projection_status: 'COMPLETE' | 'PARTIAL' | 'UNAVAILABLE'
  sources: SourceRef[]
  warnings: string[]
}

export interface Envelope<T> { data: T; meta: Meta }

export type RepoSyncState =
  | 'SYNCED' | 'REMOTE_AHEAD' | 'LOCAL_AHEAD' | 'DIVERGED'
  | 'DIRTY' | 'NO_REMOTE' | 'UNKNOWN'

export interface RepoState {
  repo: string
  local_path?: string | null
  branch?: string | null
  local_sha?: string | null
  remote_sha?: string | null
  remote_main_sha?: string | null
  ahead: number
  behind: number
  dirty: boolean
  untracked: number
  worktree_count: number
  sync_state: RepoSyncState
  main_protected?: boolean | null
  note?: string | null
}

export type ProjectStateKind =
  | 'ACTIVE' | 'PAUSED' | 'CLOSED' | 'BLOCKED' | 'CANONICAL_HISTORY' | 'UNKNOWN'

export interface ProjectSummary {
  project_id: string
  display_name: string
  mission?: string | null
  phase?: string | null
  state: ProjectStateKind
  desired_state?: string | null
  observed_state?: string | null
  active_executor?: string | null
  carrier?: string | null
  model?: string | null
  current_task?: string | null
  current_task_why?: string | null
  latest_progress?: string | null
  blocker?: string | null
  next_gate?: string | null
  lifecycle?: string | null
  authority_repo?: string | null
  domain_repo?: string | null
  lane_id?: string | null
  issue?: number | string | null
  pr?: number | string | null
  trading_authorized?: boolean | null
  owner_action_required: boolean
  meta: Meta
}

export interface ProjectDetail extends ProjectSummary {
  adapter_status?: string | null
  collision_domains: string[]
  canonical_entrypoints: string[]
  hard_boundaries: string[]
  relationships: Record<string, unknown>[]
}

export type TaskState =
  | 'IDEA' | 'PLANNED' | 'READY' | 'DISPATCHED' | 'RUNNING' | 'REVIEW'
  | 'CANONICALIZATION' | 'DONE' | 'BLOCKED' | 'STALLED'
  | 'OUTCOME_UNKNOWN' | 'OWNER_GATE' | 'PAUSED'

export interface TaskView {
  task_id: string
  project_id?: string | null
  title?: string | null
  goal?: string | null
  why?: string | null
  state: TaskState
  raw_status?: string | null
  executor?: string | null
  carrier?: string | null
  model?: string | null
  route_epoch?: number | string | null
  issue?: number | string | null
  pr?: number | string | null
  branch?: string | null
  exact_head?: string | null
  next_gate?: string | null
  blocker?: string | null
  execution_allowed?: boolean | null
  meta: Meta
}

export type AgentLiveness =
  | 'INFRA_LIVE' | 'SESSION_LIVE' | 'AGENT_ACTIVE' | 'MEANINGFUL_PROGRESS'
  | 'STALLED' | 'BLOCKED' | 'TERMINATED' | 'OUTCOME_UNKNOWN' | 'IDLE'

export interface AgentView {
  agent_id: string
  role?: string | null
  task_id?: string | null
  model?: string | null
  carrier?: string | null
  branch?: string | null
  liveness: AgentLiveness
  liveness_reason?: string | null
}

export interface ControlTowerSummary {
  counts: Record<string, number>
  lanes: Record<string, unknown>[]
  routes: Record<string, unknown>[]
  claims: Record<string, unknown>[]
  collisions: Record<string, unknown>[]
  projection_as_of?: string | null
}

export interface HealthComponent {
  component: string
  status: 'OK' | 'DEGRADED' | 'UNAVAILABLE' | 'UNKNOWN'
  detail?: string | null
  freshness: Freshness
}

export interface SystemHealth {
  components: HealthComponent[]
  overall: 'OK' | 'DEGRADED' | 'UNAVAILABLE' | 'UNKNOWN'
  frontend_version?: string | null
  backend_version?: string | null
  coordination_main_sha?: string | null
}

export interface SystemTop {
  repos: RepoState[]
  github_sha?: string | null
  github_error?: string | null
  active_task_count: number
  lane_count: number
  last_refresh: string
}
