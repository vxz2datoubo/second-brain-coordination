/**
 * Refresh bus — a single, global "refresh token" shared by every data hook.
 *
 * WHY THIS EXISTS (root-cause note, do not remove):
 * Before this module, each component that called `useProjects()` / `useTasks()`
 * received its OWN React state instance. `App.refreshAll()` only reloaded the
 * instances it happened to hold, so pages (HomePage / ProjectPage / …) never
 * saw the click. The refresh button looked broken even though data was refetched
 * somewhere else in the tree.
 *
 * FIX: one module-level tick + a subscriber set. Every `useAsync` instance
 * subscribes on mount and re-runs its fetcher when the tick changes. A single
 * `bumpRefresh()` therefore reaches ALL hooks in ALL components at once.
 *
 * This keeps the DAG discipline (iron rule 9): bumpRefresh() is the single
 * top-level entry point; render functions never call each other.
 */

type Listener = () => void

let tick = 0
const listeners = new Set<Listener>()

/** Read the current global refresh token (used as a useEffect dependency). */
export function getRefreshTick(): number {
  return tick
}

/** Subscribe to global refresh events. Returns an unsubscribe function. */
export function subscribeRefresh(fn: Listener): () => void {
  listeners.add(fn)
  return () => {
    listeners.delete(fn)
  }
}

/**
 * Trigger a global refresh. Every mounted `useAsync` instance will refetch.
 * Call this from exactly one place per user intent (the top bar button / a
 * page-level "onRefresh" handler) — never from inside a render function.
 */
export function bumpRefresh(): void {
  tick += 1
  listeners.forEach((fn) => {
    try {
      fn()
    } catch {
      // A single bad subscriber must never break the whole refresh wave.
    }
  })
}
