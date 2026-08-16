/**
 * The editor/review pane switch that below `lg` decides which of the two panes
 * is on screen.
 *
 * Which breakpoint is in force is a CSS question, and jsdom applies no
 * stylesheet, so these tests cover the part that is not CSS: the switch's own
 * state, and the fact that work arriving for review moves the switch — without
 * which a phone user would confirm a completed job and be left looking at the
 * editor, with the proposals in the pane they cannot see.
 */
import React from "react"
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react"
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
    if (path.endsWith("/histories") && req.method === "GET") return JSON.stringify([])
    if (path.endsWith("/histories") && req.method === "POST") {
      return JSON.stringify({ historyId: "hist-1", status: "pending" })
    }
    if (path.endsWith("/suggestions")) {
      return JSON.stringify({
        suggestions: [
          { id: "1", original: "比較し", reason: "「比較し」では原文の対照の含意が落ちる。" },
        ],
        overallComment: "整体评价",
      })
    }
    if (path.endsWith("/proposals")) return JSON.stringify({ proposalId: "prop-1" })
    return JSON.stringify({})
  })
}

function paneSwitch() {
  return screen.getByRole("group", { name: "表示するペーン" })
}

/** Scoped to the switch, so `編集` cannot match an edit control elsewhere. */
function paneButton(name: "編集" | "添削案") {
  return within(paneSwitch()).getByRole("button", { name: new RegExp(`^${name}`) })
}

function renderApp() {
  render(
    <AuthProvider>
      <Toaster />
      <TextCorrectionApp />
    </AuthProvider>,
  )
}

async function startSession() {
  renderApp()
  await waitFor(() => expect(screen.getByText("新しいセッション作成")).toBeInTheDocument())
  fireEvent.click(screen.getByText("新しいセッション作成"))
  await waitFor(() =>
    expect(
      screen.getByPlaceholderText("原文テキストをここに貼り付けてください..."),
    ).toBeInTheDocument(),
  )
}

async function generateAndConfirm() {
  fireEvent.change(screen.getByPlaceholderText("原文テキストをここに貼り付けてください..."), {
    target: { value: "多伦多大学的研究者对比了三十种灵长类动物的睡眠数据" },
  })
  fireEvent.change(screen.getByPlaceholderText("添削対象テキストをここに貼り付けてください..."), {
    target: { value: "トロント大学の研究者は３０種類の霊長類動物の睡眠データを比較し" },
  })
  fireEvent.click(screen.getByRole("button", { name: /Generate AI Suggestions/i }))
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

test("there is nothing to switch between until a session is open", async () => {
  routeApi()
  renderApp()

  await waitFor(() => expect(screen.getByText("セッションを開始")).toBeInTheDocument())
  expect(screen.queryByRole("group", { name: "表示するペーン" })).not.toBeInTheDocument()
})

test("a session opens on the editor, and the switch moves between the two panes", async () => {
  routeApi()
  await startSession()

  expect(paneSwitch()).toBeInTheDocument()
  expect(paneButton("編集")).toHaveAttribute("aria-pressed", "true")
  expect(paneButton("添削案")).toHaveAttribute("aria-pressed", "false")

  fireEvent.click(paneButton("添削案"))
  expect(paneButton("添削案")).toHaveAttribute("aria-pressed", "true")
  expect(paneButton("編集")).toHaveAttribute("aria-pressed", "false")

  fireEvent.click(paneButton("編集"))
  expect(paneButton("編集")).toHaveAttribute("aria-pressed", "true")
})

test("confirming a completed job brings the review pane forward", async () => {
  routeApi()
  await startSession()
  expect(paneButton("編集")).toHaveAttribute("aria-pressed", "true")

  await generateAndConfirm()

  expect(paneButton("添削案")).toHaveAttribute("aria-pressed", "true")
  expect(paneButton("編集")).toHaveAttribute("aria-pressed", "false")
  // The switch also reports what is waiting in the pane that is off screen.
  expect(paneButton("添削案")).toHaveTextContent("1")
})
