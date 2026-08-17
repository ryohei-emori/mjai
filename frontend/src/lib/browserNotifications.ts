/**
 * Browser notifications for generations that finished while the user was
 * elsewhere (`add-browser-job-notifications`).
 *
 * The in-app bell only speaks to someone already looking at the tab, which is
 * the one situation where a generation does not need announcing. This module is
 * the second channel, and the policy for when using it is welcome rather than
 * obnoxious.
 *
 * Two rules shape the API:
 *
 * 1. **Permission is never requested from here implicitly.** `requestPermission`
 *    exists, but nothing in this module calls it — the caller must wire it to a
 *    user gesture. An unprompted permission dialog is the fastest route to an
 *    origin the user has blocked forever, and denial cannot be undone from the
 *    page.
 * 2. **The decision is a pure function.** `shouldShowBrowserNotification` takes
 *    plain values, so every interesting path — granted, denied, unsupported,
 *    tab visible — is testable without a DOM or a fake `Notification`.
 */

/**
 * Permission as this app needs to reason about it. "No Notification API" is a
 * member rather than a separate predicate so callers stay on one exhaustive
 * switch, and so the unsupported path is structurally identical to `denied` —
 * which is how it must behave.
 */
export type BrowserNotificationPermission =
  | 'granted'
  | 'denied'
  | 'default'
  | 'unsupported'

function notificationApi(): typeof Notification | null {
  if (typeof window === 'undefined') return null
  if (typeof window.Notification === 'undefined') return null
  return window.Notification
}

export function isBrowserNotificationSupported(): boolean {
  return notificationApi() !== null
}

export function getNotificationPermission(): BrowserNotificationPermission {
  const api = notificationApi()
  if (!api) return 'unsupported'
  const permission = api.permission
  if (permission === 'granted' || permission === 'denied') return permission
  return 'default'
}

/**
 * Ask the browser for permission. Call only from a user gesture.
 *
 * Never throws: an unavailable or misbehaving implementation resolves to
 * `'unsupported'`, so the caller's failure path is the same one it already has.
 */
export async function requestNotificationPermission(): Promise<BrowserNotificationPermission> {
  const api = notificationApi()
  if (!api) return 'unsupported'
  try {
    const result = await api.requestPermission()
    if (result === 'granted' || result === 'denied') return result
    return 'default'
  } catch (error) {
    console.warn('[notifications] Permission request failed:', error)
    return 'unsupported'
  }
}

export type ShouldShowInput = {
  /** The user's stored preference. */
  enabled: boolean
  permission: BrowserNotificationPermission
  /** `document.visibilityState` at the moment the job completed. */
  documentVisibility: DocumentVisibilityState | 'unknown'
}

/**
 * The whole policy. Suppressed while the tab is visible: the bell badge and
 * shake are already on screen there, and a second signal for one event is
 * noise. Anything other than `visible` — background tab, minimised window,
 * another desktop — is a case where the bell cannot be seen.
 */
export function shouldShowBrowserNotification({
  enabled,
  permission,
  documentVisibility,
}: ShouldShowInput): boolean {
  if (!enabled) return false
  if (permission !== 'granted') return false
  if (documentVisibility === 'visible') return false
  return true
}

export type JobCompletedNotificationInput = {
  /** The round's label, from the same helper the job card and bell row use. */
  label: string
  /** Tags the notification so re-firing replaces rather than stacks. */
  jobId: string
  /** Runs on activation, after the tab has been asked to come forward. */
  onActivate: (jobId: string) => void
}

/**
 * The only place a `Notification` is constructed. Returns `null` when it could
 * not be shown, so callers never have to guard the constructor themselves.
 *
 * Tagged per job rather than globally: up to 30 generations run concurrently,
 * and one shared tag would collapse them all into the last one to finish.
 */
export function showJobCompletedNotification({
  label,
  jobId,
  onActivate,
}: JobCompletedNotificationInput): Notification | null {
  const api = notificationApi()
  if (!api || api.permission !== 'granted') return null

  try {
    const notification = new api('Correction suggestions ready', {
      body: `${label} — open to review`,
      tag: `mjai-job-${jobId}`,
      icon: '/favicon.ico',
    })
    notification.onclick = () => {
      // Best-effort: browsers differ on whether a notification click may raise
      // a window. The half that matters is the app being in the right state
      // once the user arrives.
      try {
        window.focus()
      } catch {
        /* ignore */
      }
      notification.close()
      onActivate(jobId)
    }
    return notification
  } catch (error) {
    console.warn('[notifications] Failed to show notification:', error)
    return null
  }
}
