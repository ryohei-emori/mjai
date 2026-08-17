/**
 * Workspace chrome preferences persisted in `localStorage`
 * (`floating-session-pane-and-collapsible-panels` design.md Decision 4).
 *
 * These are global (not per-session) UI preferences, so they use the flat
 * `mjai-…` key naming of `mjai-right-pane-width` rather than the per-session
 * `mjai:draft:` / `mjai:jobQueue:` prefixes.
 *
 * They are read from a mount-time effect, never during `useState`
 * initialization, so SSR and the first client render agree. Every read falls
 * back to a default instead of throwing, which is what keeps the workspace
 * usable when storage is unavailable (Safari private mode, disabled storage).
 */

/**
 * How the session list is presented. `docked` occupies a fixed column inside
 * the layout; `floating` removes that column so the center and right panes
 * reclaim its width, and shows the list as an overlay on demand. `docked` is
 * only honoured at the `lg` breakpoint and above.
 */
export type SessionPaneMode = 'docked' | 'floating'

export const SESSION_PANE_STORAGE_KEY = 'mjai-session-pane-mode'
export const EXEMPLAR_CARD_STORAGE_KEY = 'mjai-exemplar-card-open'
export const BROWSER_NOTIFICATIONS_STORAGE_KEY = 'mjai-browser-notifications'
export const LG_BREAKPOINT_PX = 1024

export function defaultSessionPaneMode(viewportWidth: number): SessionPaneMode {
  return viewportWidth >= LG_BREAKPOINT_PX ? 'docked' : 'floating'
}

/**
 * The observable state of the session pane: which presentation is stored, and
 * whether the floating overlay is currently open (meaningless while docked).
 */
export type SessionPaneState = {
  mode: SessionPaneMode
  overlayOpen: boolean
}

/** Whether the docked column is actually rendered, given the current viewport. */
export function isPaneDocked(state: SessionPaneState, isLgScreen: boolean): boolean {
  return state.mode === 'docked' && isLgScreen
}

/**
 * The single always-visible trigger. From docked it floats the pane — the point
 * of that click is to gain width, not to immediately see the list again — and
 * from floating it toggles the overlay. It deliberately never re-docks, because
 * the same button serves narrow viewports where docking does not exist.
 */
export function toggleSessionPaneState(
  state: SessionPaneState,
  isLgScreen: boolean,
): SessionPaneState {
  if (isPaneDocked(state, isLgScreen)) {
    return { mode: 'floating', overlayOpen: false }
  }
  return { mode: state.mode, overlayOpen: !state.overlayOpen }
}

/** The floating panel's dock button: give the list a permanent home again. */
export function dockSessionPaneState(): SessionPaneState {
  return { mode: 'docked', overlayOpen: false }
}

/**
 * Resolves a stored value to a mode. Anything unrecognised — absent, empty, or
 * garbage left by an older/newer build — is treated as "nothing stored" and
 * falls back to the viewport default.
 */
export function resolveSessionPaneMode(
  stored: string | null,
  viewportWidth: number,
): SessionPaneMode {
  if (stored === 'docked' || stored === 'floating') return stored
  return defaultSessionPaneMode(viewportWidth)
}

export function loadSessionPaneMode(): SessionPaneMode {
  const viewportWidth = typeof window === 'undefined' ? 0 : window.innerWidth
  try {
    return resolveSessionPaneMode(
      window.localStorage.getItem(SESSION_PANE_STORAGE_KEY),
      viewportWidth,
    )
  } catch {
    return defaultSessionPaneMode(viewportWidth)
  }
}

export function saveSessionPaneMode(mode: SessionPaneMode): void {
  try {
    window.localStorage.setItem(SESSION_PANE_STORAGE_KEY, mode)
  } catch (error) {
    console.warn('[persistence] Failed to save session pane mode:', error)
  }
}

/** Collapsed unless explicitly opened before, so an unreadable value is `false`. */
export function loadExemplarCardOpen(): boolean {
  try {
    return window.localStorage.getItem(EXEMPLAR_CARD_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function saveExemplarCardOpen(open: boolean): void {
  try {
    window.localStorage.setItem(EXEMPLAR_CARD_STORAGE_KEY, open ? '1' : '0')
  } catch (error) {
    console.warn('[persistence] Failed to save exemplar card state:', error)
  }
}

/**
 * Whether completed generations may be announced outside the tab
 * (`add-browser-job-notifications`).
 *
 * Off unless explicitly turned on, so an unreadable value reads as off: for this
 * preference "off" is also the privacy-preserving answer, and storage we cannot
 * read cannot be evidence of consent.
 */
export function loadBrowserNotificationsEnabled(): boolean {
  try {
    return window.localStorage.getItem(BROWSER_NOTIFICATIONS_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function saveBrowserNotificationsEnabled(enabled: boolean): void {
  try {
    window.localStorage.setItem(BROWSER_NOTIFICATIONS_STORAGE_KEY, enabled ? '1' : '0')
  } catch (error) {
    console.warn('[persistence] Failed to save browser notification preference:', error)
  }
}
