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
  describeProviderFailures,
  isSuggestionsAPIError,
  suggestionsAPI,
  withProviderDetail,
} from "../api"

describe("describeProviderFailures", () => {
  it("names each provider that declined, with its loaded key count", () => {
    const detail = describeProviderFailures({
      error: "All LLM providers failed",
      fallback_available: true,
      gemini_error: "Gemini request timed out after 22.0s",
      groq_error: "Groq API key not configured",
      cf_error: "Cloudflare credentials not configured",
      gemini_pool_size: 1,
      groq_pool_size: 0,
      cf_pool_size: 0,
    })

    expect(detail).toBe(
      "Gemini（鍵1件）: Gemini request timed out after 22.0s / " +
        "Groq（鍵0件）: Groq API key not configured / " +
        "Cloudflare（鍵0件）: Cloudflare credentials not configured",
    )
  })

  it("omits providers that reported nothing", () => {
    expect(
      describeProviderFailures({
        error: "boom",
        fallback_available: true,
        gemini_error: "Gemini rate limit exceeded",
        gemini_pool_size: 2,
      }),
    ).toBe("Gemini（鍵2件）: Gemini rate limit exceeded")
  })

  it("returns an empty string when there is no body to describe", () => {
    expect(describeProviderFailures(null)).toBe("")
    expect(withProviderDetail("失敗しました", "")).toBe("失敗しました")
  })
})

describe("SuggestionsAPIError provider diagnostics", () => {
  beforeEach(() => {
    fetchMock.resetMocks()
  })

  it("carries the breakdown and classifies a Gemini quota failure as rate-limited", async () => {
    fetchMock.mockResponseOnce(
      JSON.stringify({
        error: "All Gemini API keys are in cooldown or exhausted (pool_size=1)",
        message: "All cloud providers failed. Try WebLLM offline mode.",
        fallback_available: true,
        gemini_error:
          "All Gemini API keys are in cooldown or exhausted (pool_size=1)",
        groq_error: "Groq API key not configured",
        gemini_pool_size: 1,
        groq_pool_size: 0,
        cf_pool_size: 0,
      }),
      { status: 503 },
    )

    const error = await suggestionsAPI
      .generate("原文", "対象")
      .catch((e: unknown) => e)

    if (!isSuggestionsAPIError(error)) throw new Error("expected a suggestions error")
    // gemini_error used to be dropped by the client, so a Gemini-only quota
    // failure looked like a generic outage.
    expect(error.rateLimited).toBe(true)
    expect(error.providerDetail).toContain("Gemini（鍵1件）")
    expect(error.providerDetail).toContain("Groq（鍵0件）")
  })

  it("exposes the wall-clock abort flag distinctly from a provider outage", async () => {
    fetchMock.mockResponseOnce(
      JSON.stringify({
        error: "Suggestions generation exceeded wall-clock budget (55s)",
        message:
          "Cloud generation ran out of time before any provider returned a usable answer.",
        fallback_available: true,
        timed_out: true,
        rate_limited: false,
        gemini_error: "Gemini request timed out after 22.0s",
        gemini_pool_size: 1,
      }),
      { status: 503 },
    )

    const error = await suggestionsAPI
      .generate("原文", "対象")
      .catch((e: unknown) => e)

    if (!isSuggestionsAPIError(error)) throw new Error("expected a suggestions error")
    expect(error.body?.timed_out).toBe(true)
    expect(error.rateLimited).toBe(false)
  })
})
