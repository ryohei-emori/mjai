/**
 * A failed cloud generation must tell the user which provider declined and why.
 *
 * "All cloud providers failed" on its own sent a production incident straight to
 * guesswork: an unset Groq key, an exhausted Gemini quota and a 22s timeout all
 * looked identical in the UI even though the backend distinguishes them
 * (`fix-suggestion-retry-budget-hard-failure`).
 */
import React from "react"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"
import "@testing-library/jest-dom"
import fetchMock from "jest-fetch-mock"

import TextCorrectionApp from "../page"
import { AuthProvider } from "../auth-provider"
import { Toaster } from "@/components/ui/toaster"

fetchMock.enableMocks()

jest.mock("@/lib/supabaseClient", () => {
  const fakeSession = {
    access_token: "test-access-token",
    user: { email: "owner@example.com" },
  }
  return {
    supabase: {
      auth: {
        getSession: jest.fn().mockResolvedValue({ data: { session: fakeSession } }),
        onAuthStateChange: jest.fn().mockReturnValue({
          data: { subscription: { unsubscribe: jest.fn() } },
        }),
        signInWithOAuth: jest.fn(),
        signOut: jest.fn(),
      },
    },
  }
})

jest.mock("@/lib/webllm/webgpu", () => ({
  checkWebGPUSupport: jest.fn().mockReturnValue({ supported: false, reason: "WebGPU非対応" }),
}))
jest.mock("@/lib/webllm/engineReady", () => ({
  isEngineReady: jest.fn().mockReturnValue(false),
}))
jest.mock("@/lib/webllm/config", () => ({
  WEBLLM_MODEL_DISPLAY_NAME: "test-model",
  WEBLLM_MODEL_ID: "test-model-id",
}))
jest.mock("@/lib/webllm/diagnostics", () => ({
  formatElapsedTime: (ms: number) => `${ms}ms`,
  formatDownloadProgress: () => "0%",
  PHASE_LABELS: {},
  getDiagnosticsTracker: () => ({ getState: () => ({}) }),
}))
jest.mock("@/lib/webllm/engine", () => ({
  generateSuggestions: jest.fn(),
}))

const FAILURE_BODY = {
  error: "All LLM providers failed",
  message: "All cloud providers failed. Try WebLLM offline mode.",
  fallback_available: true,
  rate_limited: false,
  gemini_error: "Gemini request timed out after 22.0s",
  groq_error: "Groq API key not configured",
  cf_error: "Cloudflare credentials not configured",
  gemini_pool_size: 1,
  groq_pool_size: 0,
  cf_pool_size: 0,
}

function routeApi() {
  fetchMock.mockResponse(async (req) => {
    const path = new URL(req.url).pathname
    if (path.endsWith("/sessions") && req.method === "GET") return JSON.stringify([])
    if (path.endsWith("/sessions") && req.method === "POST") {
      return JSON.stringify({
        sessionId: "session-1",
        name: "セッション 1",
        createdAt: new Date().toISOString(),
        correctionCount: 0,
      })
    }
    if (path.endsWith("/histories")) return JSON.stringify([])
    if (path.endsWith("/suggestions/async") && req.method === "POST") {
      return { body: JSON.stringify({ error: "not configured" }), status: 404 }
    }
    if (path.endsWith("/suggestions")) {
      return { body: JSON.stringify(FAILURE_BODY), status: 503 }
    }
    return JSON.stringify({})
  })
}

beforeAll(() => {
  Object.assign(navigator, { clipboard: { writeText: jest.fn().mockResolvedValue(undefined) } })
})

beforeEach(() => {
  fetchMock.resetMocks()
  localStorage.clear()
  process.env.NEXT_PUBLIC_FRONTEND_MODE = "real"
})

test("failed job names each provider that declined and its key count", async () => {
  routeApi()

  render(
    <AuthProvider>
      <Toaster />
      <TextCorrectionApp />
    </AuthProvider>,
  )

  await waitFor(() => expect(screen.getByText("Create a new session")).toBeInTheDocument())
  fireEvent.click(screen.getByText("Create a new session"))

  await waitFor(() =>
    expect(
      screen.getByPlaceholderText("Paste the source text here..."),
    ).toBeInTheDocument(),
  )
  fireEvent.change(screen.getByPlaceholderText("Paste the source text here..."), {
    target: { value: "多伦多大学的研究者对比了三十种灵长类动物的睡眠数据" },
  })
  fireEvent.change(screen.getByPlaceholderText("Paste the text you want corrected here..."), {
    target: { value: "トロント大学の研究者は３０種類の霊長類動物の睡眠データを比較し" },
  })

  fireEvent.click(screen.getByRole("button", { name: /Generate AI Suggestions/i }))

  await waitFor(() => expect(screen.getByText("Failed")).toBeInTheDocument())

  // Both the toast and the failed job card carry it: the toast is missed if the
  // user looks away, and the card is what they come back to.
  const details = await screen.findAllByText(/内訳: Gemini（鍵1件）/)
  expect(details).toHaveLength(2)
  for (const detail of details) {
    // The backend's ops-facing English is not what the user reads.
    expect(detail).toHaveTextContent("クラウドAPIでの添削生成に失敗しました")
    expect(detail).not.toHaveTextContent("All cloud providers failed")
    expect(detail).toHaveTextContent("Gemini request timed out after 22.0s")
    expect(detail).toHaveTextContent("Groq（鍵0件）: Groq API key not configured")
    expect(detail).toHaveTextContent("Cloudflare（鍵0件）")
  }
})
