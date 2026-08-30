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

import { suggestionsAPI } from "../api"

const OK_BODY = JSON.stringify({ suggestions: [], overallComment: "" })

function sentBody(): Record<string, unknown> {
  const [, init] = fetchMock.mock.calls[0] as [string, RequestInit]
  return JSON.parse(init.body as string)
}

describe("suggestionsAPI.generate — optional exemplarTranslation", () => {
  beforeEach(() => {
    fetchMock.resetMocks()
    fetchMock.mockResponseOnce(JSON.stringify({ error: "not configured" }), { status: 404 })
    fetchMock.mockResponseOnce(OK_BODY)
  })

  it("omits the key entirely when no exemplar is passed", async () => {
    await suggestionsAPI.generate("原文", "対象")

    expect(sentBody()).toEqual({ originalText: "原文", targetText: "対象" })
  })

  it("omits the key when the exemplar is whitespace only", async () => {
    await suggestionsAPI.generate("原文", "対象", "  \n ")

    expect(sentBody()).not.toHaveProperty("exemplarTranslation")
  })

  it("sends the trimmed exemplar when one is provided", async () => {
    await suggestionsAPI.generate("原文", "対象", "  模範の訳文 \n")

    expect(sentBody()).toEqual({
      originalText: "原文",
      targetText: "対象",
      exemplarTranslation: "模範の訳文",
    })
  })
})
