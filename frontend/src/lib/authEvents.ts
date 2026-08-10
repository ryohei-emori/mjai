// Lightweight pub/sub bridging non-React modules (api.ts) with the React
// AuthProvider context, so `apiFetch` can trigger a forced sign-out on a 401
// without importing React or the auth context directly.

type UnauthorizedHandler = () => void

let handler: UnauthorizedHandler | null = null

export function registerUnauthorizedHandler(fn: UnauthorizedHandler): () => void {
  handler = fn
  return () => {
    if (handler === fn) {
      handler = null
    }
  }
}

export function notifyUnauthorized(): void {
  handler?.()
}
