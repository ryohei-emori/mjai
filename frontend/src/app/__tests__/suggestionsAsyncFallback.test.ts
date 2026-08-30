import fetchMock from "jest-fetch-mock"

fetchMock.enableMocks()

jest.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: jest.fn().mockResolvedValue({
        data: { session: { access_token: "test-access-token" } },
      }),
    },
  },
}))

import {
  isSuggestionsAPIError,
  suggestionsAPI,
  tryAsyncCodexSuggestions,
} from "../api"

const REQUEST = { originalText: "原文", targetText: "対象" }
const AUTH = { Authorization: "Bearer test-access-token" }
const COMPLETED = {
  status: "completed",
  suggestions: [{ id: "1", original: "対象", reason: "理由" }],
  overallComment: "講評",
}
const CLOUD = {
  suggestions: [{ id: "2", original: "対象", reason: "クラウド理由" }],
  overallComment: "クラウド講評",
  llmProvider: "gemini",
}

describe("suggestionsAPI async Codex fallback", () => {
  beforeEach(() => {
    fetchMock.resetMocks()
    jest.useRealTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it.each([
    ["unconfigured", 404],
    ["submission server failure", 502],
  ])("falls back for %s", async (_name, status) => {
    fetchMock.mockResponseOnce(JSON.stringify({ error: "codex unavailable" }), { status })
    fetchMock.mockResponseOnce(JSON.stringify(CLOUD))

    await expect(suggestionsAPI.generate("原文", "対象")).resolves.toEqual(CLOUD)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(String(fetchMock.mock.calls[0][0])).toContain("/suggestions/async")
    expect(String(fetchMock.mock.calls[1][0])).toMatch(/\/suggestions$/)
  })

  it("falls back when async submission cannot reach the server", async () => {
    fetchMock.mockRejectOnce(new TypeError("Failed to fetch"))
    fetchMock.mockResponseOnce(JSON.stringify(CLOUD))

    await expect(suggestionsAPI.generate("原文", "対象")).resolves.toEqual(CLOUD)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it("falls back when a successful submission body is malformed", async () => {
    fetchMock.mockResponseOnce(JSON.stringify({ suggestions: [], overallComment: "" }))
    fetchMock.mockResponseOnce(JSON.stringify(CLOUD))

    await expect(suggestionsAPI.generate("原文", "対象")).resolves.toEqual(CLOUD)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })

  it("returns a completed async result without calling the cloud endpoint", async () => {
    fetchMock.mockResponseOnce(JSON.stringify(COMPLETED))

    await expect(suggestionsAPI.generate("原文", "対象")).resolves.toEqual(COMPLETED)
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it("falls back to the cloud endpoint after polling fails", async () => {
    jest.useFakeTimers()
    fetchMock.mockResponseOnce(JSON.stringify({ status: "pending", taskId: "task-5" }))
    fetchMock.mockResponseOnce(JSON.stringify({ error: "gateway down" }), { status: 502 })
    fetchMock.mockResponseOnce(JSON.stringify(CLOUD))

    const result = suggestionsAPI.generate("原文", "対象")
    await jest.advanceTimersByTimeAsync(2_000)

    await expect(result).resolves.toEqual(CLOUD)
    expect(fetchMock).toHaveBeenCalledTimes(3)
    expect(String(fetchMock.mock.calls[2][0])).toMatch(/\/suggestions$/)
    jest.useRealTimers()
  })

  it("uses the cloud-chain diagnostics when Codex and cloud fallback both fail", async () => {
    const cloudFailure = {
      error: "All LLM providers failed",
      fallback_available: true,
      gemini_error: "quota exhausted",
      gemini_pool_size: 1,
    }
    fetchMock.mockResponseOnce(JSON.stringify({ error: "codex down" }), { status: 502 })
    fetchMock.mockResponseOnce(JSON.stringify(cloudFailure), { status: 503 })

    const error = await suggestionsAPI.generate("原文", "対象").catch((value) => value)
    expect(isSuggestionsAPIError(error)).toBe(true)
    expect(error.status).toBe(503)
    expect(error.body).toEqual(cloudFailure)
    expect(error.providerDetail).toContain("Gemini（鍵1件）")
  })

  it.each([400, 401, 403])(
    "keeps submission HTTP %s terminal",
    async (status) => {
      fetchMock.mockResponseOnce(JSON.stringify({ error: "terminal" }), { status })

      const error = await suggestionsAPI.generate("原文", "対象").catch((value) => value)
      expect(isSuggestionsAPIError(error)).toBe(true)
      expect(error.status).toBe(status)
      expect(fetchMock).toHaveBeenCalledTimes(1)
    },
  )
})

describe("Codex async polling contract", () => {
  beforeEach(() => {
    fetchMock.resetMocks()
    jest.useRealTimers()
  })

  afterEach(() => {
    jest.useRealTimers()
  })

  it("polls a pending task to completion", async () => {
    fetchMock.mockResponseOnce(JSON.stringify({ status: "pending", taskId: "task-1" }))
    fetchMock.mockResponseOnce(JSON.stringify(COMPLETED))

    await expect(
      tryAsyncCodexSuggestions(REQUEST, AUTH, { pollIntervalMs: 0, pollTimeoutMs: 100 }),
    ).resolves.toEqual(COMPLETED)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(String(fetchMock.mock.calls[1][0])).toContain("/suggestions/async/task-1")
  })

  it.each([
    ["missing task", 404, JSON.stringify({ error: "missing" })],
    ["server error", 502, JSON.stringify({ error: "gateway down" })],
    ["malformed status", 200, JSON.stringify({ status: "unexpected" })],
  ])("makes polling %s recoverable", async (_name, status, body) => {
    fetchMock.mockResponseOnce(JSON.stringify({ status: "pending", taskId: "task-2" }))
    fetchMock.mockResponseOnce(body, { status })

    await expect(
      tryAsyncCodexSuggestions(REQUEST, AUTH, { pollIntervalMs: 0, pollTimeoutMs: 100 }),
    ).resolves.toBeNull()
  })

  it("makes a polling network failure recoverable", async () => {
    fetchMock.mockResponseOnce(JSON.stringify({ status: "pending", taskId: "task-3" }))
    fetchMock.mockRejectOnce(new TypeError("Failed to fetch"))

    await expect(
      tryAsyncCodexSuggestions(REQUEST, AUTH, { pollIntervalMs: 0, pollTimeoutMs: 100 }),
    ).resolves.toBeNull()
  })

  it("falls back when the polling deadline expires", async () => {
    jest.useFakeTimers()
    fetchMock.mockResponseOnce(JSON.stringify({ status: "pending", taskId: "task-4" }))
    fetchMock.mockResponse(JSON.stringify({ status: "pending", taskId: "task-4" }))

    const result = tryAsyncCodexSuggestions(REQUEST, AUTH, {
      pollIntervalMs: 10,
      pollTimeoutMs: 25,
    })
    await jest.advanceTimersByTimeAsync(40)

    await expect(result).resolves.toBeNull()
    expect(fetchMock.mock.calls.length).toBeGreaterThan(1)
  })
})
