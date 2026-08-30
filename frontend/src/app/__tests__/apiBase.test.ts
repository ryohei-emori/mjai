import { resolveApiBase } from "../apiBase"

describe("resolveApiBase", () => {
  it("trims whitespace and redundant trailing slashes", () => {
    expect(resolveApiBase("  /api///\n", "production")).toBe("/api")
    expect(resolveApiBase(" https://api.example.test/// ", "production")).toBe(
      "https://api.example.test",
    )
  })

  it("uses same-origin /api for an empty production value", () => {
    expect(resolveApiBase(undefined, "production")).toBe("/api")
    expect(resolveApiBase(" \n ", "production")).toBe("/api")
  })

  it("uses localhost only outside production", () => {
    expect(resolveApiBase(undefined, "development")).toBe("http://localhost:8000")
    expect(resolveApiBase("", "test")).toBe("http://localhost:8000")
  })
})
