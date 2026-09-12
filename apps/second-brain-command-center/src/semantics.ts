/**
 * Status semantics — the single place that maps raw system states into
 * human-readable labels + visual tokens.
 *
 * Core principle (from Owner spec): NEVER collapse these states:
 *   candidate / CI passed / ACCEPT / canonical / deployed / active
 * And NEVER show "working" from PID or heartbeat alone.
 */
import type {
  Freshness, Trust, ProjectStateKind, TaskState, AgentLiveness, RepoSyncState,
} from './types'

export interface Label {
  zh: string
  en: string
  tone: Tone
}

export type Tone =
  | 'ok' | 'warn' | 'bad' | 'review' | 'neutral' | 'candidate' | 'accent' | 'cyan'

export const toneVar: Record<Tone, { fg: string; bg: string }> = {
  ok:        { fg: 'var(--ok)',        bg: 'var(--ok-soft)' },
  warn:      { fg: 'var(--warn)',      bg: 'var(--warn-soft)' },
  bad:       { fg: 'var(--bad)',       bg: 'var(--bad-soft)' },
  review:    { fg: 'var(--review)',    bg: 'var(--review-soft)' },
  neutral:   { fg: 'var(--neutral)',   bg: 'var(--neutral-soft)' },
  candidate: { fg: 'var(--candidate)', bg: 'var(--candidate-soft)' },
  accent:    { fg: 'var(--accent)',    bg: 'var(--accent-soft)' },
  cyan:      { fg: 'var(--cyan)',      bg: 'var(--accent-soft)' },
}

export const projectStateLabel: Record<ProjectStateKind, Label> = {
  ACTIVE:            { zh: '正在推进', en: 'ACTIVE', tone: 'ok' },
  PAUSED:            { zh: '已暂停',   en: 'PAUSED', tone: 'warn' },
  CLOSED:            { zh: '已关闭',   en: 'CLOSED', tone: 'neutral' },
  BLOCKED:           { zh: '受阻',     en: 'BLOCKED', tone: 'bad' },
  CANONICAL_HISTORY: { zh: '已进正史', en: 'CANONICAL_HISTORY', tone: 'neutral' },
  UNKNOWN:           { zh: '状态未知', en: 'UNKNOWN', tone: 'neutral' },
}

export const taskStateLabel: Record<TaskState, Label> = {
  IDEA:             { zh: '想法',       en: 'IDEA', tone: 'neutral' },
  PLANNED:          { zh: '已规划',     en: 'PLANNED', tone: 'neutral' },
  READY:            { zh: '待派发',     en: 'READY', tone: 'candidate' },
  DISPATCHED:       { zh: '已派发',     en: 'DISPATCHED', tone: 'accent' },
  RUNNING:          { zh: '执行中',     en: 'RUNNING', tone: 'ok' },
  REVIEW:           { zh: '等待验算',   en: 'REVIEW', tone: 'review' },
  CANONICALIZATION: { zh: '等待入正史', en: 'CANONICALIZATION', tone: 'review' },
  DONE:             { zh: '已完成',     en: 'DONE', tone: 'neutral' },
  BLOCKED:          { zh: '受阻',       en: 'BLOCKED', tone: 'bad' },
  STALLED:          { zh: '停滞',       en: 'STALLED', tone: 'warn' },
  OUTCOME_UNKNOWN:  { zh: '结果不明',   en: 'OUTCOME_UNKNOWN', tone: 'bad' },
  OWNER_GATE:       { zh: '等待主人决定', en: 'OWNER_GATE', tone: 'warn' },
  PAUSED:           { zh: '已暂停',     en: 'PAUSED', tone: 'warn' },
}

export const livenessLabel: Record<AgentLiveness, Label> = {
  INFRA_LIVE:         { zh: '仅基础设施在线', en: 'INFRA_LIVE', tone: 'neutral' },
  SESSION_LIVE:       { zh: '会话在线',       en: 'SESSION_LIVE', tone: 'warn' },
  AGENT_ACTIVE:       { zh: '智能体活跃',     en: 'AGENT_ACTIVE', tone: 'ok' },
  MEANINGFUL_PROGRESS:{ zh: '有实质进展',     en: 'MEANINGFUL_PROGRESS', tone: 'ok' },
  STALLED:            { zh: '停滞',           en: 'STALLED', tone: 'warn' },
  BLOCKED:            { zh: '受阻',           en: 'BLOCKED', tone: 'bad' },
  TERMINATED:         { zh: '已结束',         en: 'TERMINATED', tone: 'neutral' },
  OUTCOME_UNKNOWN:    { zh: '结果不明',       en: 'OUTCOME_UNKNOWN', tone: 'bad' },
  IDLE:               { zh: '空闲',           en: 'IDLE', tone: 'neutral' },
}

export const freshnessLabel: Record<Freshness, Label> = {
  FRESH:   { zh: '新鲜',   en: 'FRESH', tone: 'ok' },
  AGING:   { zh: '渐旧',   en: 'AGING', tone: 'warn' },
  STALE:   { zh: '已过期', en: 'STALE', tone: 'bad' },
  UNKNOWN: { zh: '未知',   en: 'UNKNOWN', tone: 'neutral' },
}

export const trustLabel: Record<Trust, Label> = {
  CANONICAL:        { zh: '已入正史', en: 'CANONICAL', tone: 'ok' },
  CANDIDATE:        { zh: '候选',     en: 'CANDIDATE', tone: 'candidate' },
  RUNTIME_OBSERVED: { zh: '运行时观测', en: 'RUNTIME_OBSERVED', tone: 'cyan' },
  DERIVED:          { zh: '推导',     en: 'DERIVED', tone: 'neutral' },
  HISTORICAL:       { zh: '历史',     en: 'HISTORICAL', tone: 'neutral' },
  UNKNOWN:          { zh: '未知',     en: 'UNKNOWN', tone: 'neutral' },
}

export const syncStateLabel: Record<RepoSyncState, Label> = {
  SYNCED:       { zh: '已同步',       en: 'SYNCED', tone: 'ok' },
  REMOTE_AHEAD: { zh: '远端更新',     en: 'REMOTE_AHEAD', tone: 'warn' },
  LOCAL_AHEAD:  { zh: '本地领先',     en: 'LOCAL_AHEAD', tone: 'candidate' },
  DIVERGED:     { zh: '已分叉',       en: 'DIVERGED', tone: 'bad' },
  DIRTY:        { zh: '有未提交改动', en: 'DIRTY', tone: 'warn' },
  NO_REMOTE:    { zh: '无远端',       en: 'NO_REMOTE', tone: 'neutral' },
  UNKNOWN:      { zh: '未知',         en: 'UNKNOWN', tone: 'neutral' },
}

export const PROJECT_ICON: Record<string, string> = {
  SECOND_BRAIN: 'brain',
  TRADING_SYSTEM: 'chart',
  REALTIME_INTERACTIVE_FILM_GAME: 'film',
  AI_DIRECTOR: 'camera',
}
