/**
 * Model provenance surfaced in the workspace (`{model} used` caption) and
 * persisted with the correction round.
 *
 * Gemini and Groq rotate models per request, so "which model wrote this
 * critique" is only knowable from the response — hence the caption reads the
 * response rather than a client-side constant, and shows nothing when the
 * backend reports no model (rounds saved before provenance existed).
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

const SUGGESTION = {
  id: "1",
  original: "比較し",
  reason: "「比較し」では原文の対照の含意が落ちる。",
}

/** Routes by URL + method so the order of the page's calls does not matter. */
function routeApi(suggestionsBody: Record<string, unknown>) {
  fetchMock.mockResponse(async (req) => {
    const url = new URL(req.url)
    const path = url.pathname
    if (path.endsWith("/sessions") && req.method === "GET") return JSON.stringify([])
    if (path.endsWith("/sessions") && req.method === "POST") {
      return JSON.stringify({
        sessionId: "session-1",
        name: "セッション 1",
        createdAt: new Date().toISOString(),
        correctionCount: 0,
      })
    }
    if (path.endsWith("/histories") && req.method === "GET") return JSON.stringify([])
    if (path.endsWith("/histories") && req.method === "POST") {
      return JSON.stringify({ historyId: "hist-1", status: "pending" })
    }
    if (path.endsWith("/suggestions")) return JSON.stringify(suggestionsBody)
    if (path.endsWith("/proposals")) return JSON.stringify({ proposalId: "prop-1" })
    return JSON.stringify({})
  })
}

function postedHistoryBody(): Record<string, unknown> {
  const call = fetchMock.mock.calls.find(([url, init]) => {
    const request = init as RequestInit
    return String(url).includes("/histories") && request?.method === "POST"
  })
  if (!call) throw new Error("no POST /histories call was made")
  return JSON.parse((call[1] as RequestInit).body as string)
}

async function generateOnce() {
  render(
    <AuthProvider>
      <Toaster />
      <TextCorrectionApp />
    </AuthProvider>,
  )

  await waitFor(() => expect(screen.getByText("新しいセッション作成")).toBeInTheDocument())
  fireEvent.click(screen.getByText("新しいセッション作成"))

  await waitFor(() =>
    expect(
      screen.getByPlaceholderText("原文テキストをここに貼り付けてください..."),
    ).toBeInTheDocument(),
  )
  fireEvent.change(screen.getByPlaceholderText("原文テキストをここに貼り付けてください..."), {
    target: { value: "多伦多大学的研究者对比了三十种灵长类动物的睡眠数据" },
  })
  fireEvent.change(screen.getByPlaceholderText("添削対象テキストをここに貼り付けてください..."), {
    target: { value: "トロント大学の研究者は３０種類の霊長類動物の睡眠データを比較し" },
  })

  fireEvent.click(screen.getByRole("button", { name: /Generate AI Suggestions/i }))

  // The completed job must be confirmed before the suggestions panel renders.
  await waitFor(() => expect(screen.getByText("確認")).toBeInTheDocument())
  fireEvent.click(screen.getByText("確認"))
  await waitFor(() => expect(screen.getByText("AI Suggestions")).toBeInTheDocument())
}

beforeAll(() => {
  Object.assign(navigator, { clipboard: { writeText: jest.fn().mockResolvedValue(undefined) } })
})

beforeEach(() => {
  fetchMock.resetMocks()
  localStorage.clear()
  process.env.NEXT_PUBLIC_FRONTEND_MODE = "real"
})

test("caption names the model that answered, and the round records it", async () => {
  routeApi({
    suggestions: [SUGGESTION],
    overallComment: "整体评价",
    llmProvider: "gemini",
    llmModel: "gemini-3.7-flash",
  })

  await generateOnce()

  expect(screen.getByTestId("suggestion-model-caption")).toHaveTextContent(
    "gemini-3.7-flash used",
  )
  // クラウドAPI / ローカルAI badge is driven by the same completion path.
  expect(screen.getByText("クラウドAPI")).toBeInTheDocument()

  expect(postedHistoryBody()).toMatchObject({
    status: "pending",
    provider: "api",
    llmProvider: "gemini",
    llmModel: "gemini-3.7-flash",
  })
})

test("caption is omitted when the backend reports no model", async () => {
  routeApi({ suggestions: [SUGGESTION], overallComment: "整体评价" })

  await generateOnce()

  expect(screen.queryByTestId("suggestion-model-caption")).not.toBeInTheDocument()

  const body = postedHistoryBody()
  expect(body).not.toHaveProperty("llmProvider")
  expect(body).not.toHaveProperty("llmModel")
})
