const LOCAL_API_BASE_URL = "http://localhost:8000"
const PRODUCTION_API_BASE_URL = "/api"

export function normalizeApiBase(configured: string | undefined): string {
  return (configured || "").trim().replace(/\/+$/, "")
}

/** Resolve the browser API base without baking localhost into production. */
export function resolveApiBase(
  configured: string | undefined,
  environment: string | undefined,
): string {
  const normalized = normalizeApiBase(configured)
  if (normalized) return normalized
  return environment === "production"
    ? PRODUCTION_API_BASE_URL
    : LOCAL_API_BASE_URL
}
