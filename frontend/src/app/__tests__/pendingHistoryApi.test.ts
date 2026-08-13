/**
 * API helpers for persist-on-generation (pending history promote + proposal update).
 */
import { historyAPI, proposalAPI } from "../api"

jest.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: jest.fn().mockResolvedValue({ data: { session: null } }),
    },
  },
}))

jest.mock("@/lib/authEvents", () => ({
  notifyUnauthorized: jest.fn(),
}))

describe("pending history / proposal update APIs", () => {
  const originalFetch = global.fetch

  beforeEach(() => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers(),
      text: async () =>
        JSON.stringify({
          historyId: "hist-1",
          status: "confirmed",
          proposalId: "prop-1",
          isSelected: true,
        }),
    }) as unknown as typeof fetch
  })

  afterEach(() => {
    global.fetch = originalFetch
    jest.clearAllMocks()
  })

  it("updateHistory sends PUT with status confirmed", async () => {
    await historyAPI.updateHistory("hist-1", {
      status: "confirmed",
      combinedComment: "整体评价",
    })

    expect(global.fetch).toHaveBeenCalled()
    const [url, init] = (global.fetch as jest.Mock).mock.calls[0]
    expect(String(url)).toContain("/histories/hist-1")
    expect(init.method).toBe("PUT")
    expect(JSON.parse(init.body)).toMatchObject({
      status: "confirmed",
      combinedComment: "整体评价",
    })
  })

  it("createHistory can request pending status", async () => {
    await historyAPI.createHistory({
      sessionId: "sess-1",
      originalText: "原文",
      targetText: "訳文",
      status: "pending",
      overallComment: "整体评价",
      provider: "api",
      clientJobId: "job-1",
    })

    const [, init] = (global.fetch as jest.Mock).mock.calls[0]
    expect(init.method).toBe("POST")
    expect(JSON.parse(init.body)).toMatchObject({
      status: "pending",
      provider: "api",
      clientJobId: "job-1",
    })
  })

  it("updateProposal sends PUT with selection flags", async () => {
    await proposalAPI.updateProposal("prop-1", {
      isSelected: true,
      selectedOrder: 2,
      modifiedReason: "编辑",
    })

    const [url, init] = (global.fetch as jest.Mock).mock.calls[0]
    expect(String(url)).toContain("/proposals/prop-1")
    expect(init.method).toBe("PUT")
    expect(JSON.parse(init.body)).toMatchObject({
      isSelected: true,
      selectedOrder: 2,
      modifiedReason: "编辑",
    })
  })
})
