/**
 * Request shapes for the shared correction-prompt settings API.
 *
 * The prompt is one global row, so a wrong verb here is not a cosmetic bug: a
 * DELETE sent where PUT was meant would silently drop everyone's customization.
 */
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

jest.mock("@/lib/authEvents", () => ({
  notifyUnauthorized: jest.fn(),
}))

import { settingsAPI } from "../api"

const READ_BODY = JSON.stringify({
  systemPrompt: "保存済みの本文",
  defaultSystemPrompt: "既定の本文",
  isCustomized: true,
  updatedAt: "2026-08-16T07:00:00+00:00",
  updatedBy: "owner@example.com",
})

function lastCall(): [string, RequestInit] {
  return fetchMock.mock.calls[0] as [string, RequestInit]
}

describe("settingsAPI", () => {
  beforeEach(() => {
    fetchMock.resetMocks()
    fetchMock.mockResponseOnce(READ_BODY)
  })

  it("reads the effective prompt with GET and the bearer token", async () => {
    const settings = await settingsAPI.getPrompt()

    const [url, init] = lastCall()
    expect(String(url)).toContain("/settings/prompt")
    // GET is the default verb; api.ts passes no method for reads.
    expect(init.method).toBeUndefined()
    expect((init.headers as Record<string, string>).Authorization).toBe(
      "Bearer test-access-token",
    )
    expect(settings.isCustomized).toBe(true)
    expect(settings.updatedBy).toBe("owner@example.com")
  })

  it("saves with PUT and a systemPrompt body", async () => {
    await settingsAPI.updatePrompt("編集後の本文")

    const [url, init] = lastCall()
    expect(String(url)).toContain("/settings/prompt")
    expect(init.method).toBe("PUT")
    expect(JSON.parse(init.body as string)).toEqual({ systemPrompt: "編集後の本文" })
  })

  it("resets with DELETE and no body", async () => {
    await settingsAPI.resetPrompt()

    const [url, init] = lastCall()
    expect(String(url)).toContain("/settings/prompt")
    expect(init.method).toBe("DELETE")
    expect(init.body).toBeUndefined()
  })

  it("propagates a rejected save so the dialog can keep the user's text", async () => {
    fetchMock.resetMocks()
    fetchMock.mockResponseOnce("prompt must not be empty", { status: 400 })

    await expect(settingsAPI.updatePrompt("   ")).rejects.toThrow("API Error: 400")
  })
})
