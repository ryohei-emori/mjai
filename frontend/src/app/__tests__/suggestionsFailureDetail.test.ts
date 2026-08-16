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
  describeSuggestionsFailure,
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

  it("does not read the response JSON's key names as quota wording", async () => {
    // The raw body text used to be part of the classification input, so the
    // `"rate_limited"` key alone made every 503 look rate-limited.
    fetchMock.mockResponseOnce(
      JSON.stringify({
        error: "All LLM providers failed",
        message: "All cloud providers failed. Try WebLLM offline mode.",
        fallback_available: true,
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
    expect(error.rateLimited).toBe(false)
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

describe("describeSuggestionsFailure", () => {
  function failure(body: Record<string, unknown>, status = 503) {
    fetchMock.resetMocks()
    fetchMock.mockResponseOnce(JSON.stringify(body), { status })
    return suggestionsAPI.generate("原文", "対象").catch((e: unknown) => e)
  }

  it("explains a provider outage in Japanese rather than passing English through", async () => {
    // The backend `message` is ops-facing English; it is what reached the user
    // as "All cloud providers failed" in a Japanese UI.
    const message = describeSuggestionsFailure(
      await failure({
        error: "All LLM providers failed",
        message: "All cloud providers failed. Try WebLLM offline mode.",
        fallback_available: true,
        gemini_error: "Gemini request timed out after 22.0s",
        gemini_pool_size: 1,
      }),
    )

    expect(message).toContain("クラウドAPIでの添削生成に失敗しました")
    expect(message).not.toContain("All cloud providers failed")
    expect(message).toContain("内訳: Gemini（鍵1件）")
  })

  it("advises retrying when the failure was the wall-clock budget", async () => {
    const message = describeSuggestionsFailure(
      await failure({
        error: "Suggestions generation exceeded wall-clock budget (55s)",
        fallback_available: true,
        timed_out: true,
      }),
    )

    expect(message).toContain("制限時間内に終わりませんでした")
  })

  it("advises waiting when providers are rate-limited", async () => {
    const message = describeSuggestionsFailure(
      await failure({
        error: "All LLM providers rate-limited or quota exhausted",
        fallback_available: true,
        rate_limited: true,
      }),
    )

    expect(message).toContain("レート制限またはクォータ超過")
  })

  it("keeps the browser's own message when the request never reached the backend", () => {
    const networkError = new (class extends Error {})("Failed to fetch")
    expect(describeSuggestionsFailure(networkError)).toBe("Failed to fetch")
  })

  it("explains a platform-level function timeout instead of showing its raw text", async () => {
    // Vercel kills the function with a non-JSON 504, so none of the app's own
    // diagnostics are in the response — the user saw the bare
    // FUNCTION_INVOCATION_TIMEOUT string.
    fetchMock.resetMocks()
    fetchMock.mockResponseOnce(
      "An error occurred with your deployment\n\nFUNCTION_INVOCATION_TIMEOUT",
      { status: 504 },
    )

    const error = await suggestionsAPI.generate("原文", "対象").catch((e: unknown) => e)
    const message = describeSuggestionsFailure(error)

    expect(message).toContain("サーバーの実行時間上限に達した")
    expect(message).not.toContain("FUNCTION_INVOCATION_TIMEOUT")
  })
})
