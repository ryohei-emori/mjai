import {
  SYSTEM_PROMPT,
  FEW_SHOT_EXAMPLES,
  SECTION_ORIGINAL,
  SECTION_TARGET,
  SECTION_INSTRUCTION,
  SECTION_ANSWER,
  SECTION_ERROR_POINTING,
  SECTION_PROBLEM,
} from "../prompts";

describe("prompts exports", () => {
  it("exports SYSTEM_PROMPT with expected content", () => {
    expect(SYSTEM_PROMPT).toBeDefined();
    expect(typeof SYSTEM_PROMPT).toBe("string");
    // Ultra-short SmolLM2-optimized prompt: JSON-only output, no markdown fences, no trailing commas
    expect(SYSTEM_PROMPT).toContain("JSON");
    expect(SYSTEM_PROMPT).toContain("禁止");
    expect(SYSTEM_PROMPT).toContain("指摘");
  });

  it("exports FEW_SHOT_EXAMPLES with expected structure", () => {
    expect(FEW_SHOT_EXAMPLES).toBeDefined();
    expect(typeof FEW_SHOT_EXAMPLES).toBe("string");
    // Ultra-short example showing JSON structure
    expect(FEW_SHOT_EXAMPLES).toContain("例");
    expect(FEW_SHOT_EXAMPLES).toContain("指摘");
    expect(FEW_SHOT_EXAMPLES).toContain("全体講評");
  });

  it("exports all section templates", () => {
    expect(SECTION_ORIGINAL).toBe("＜中国語または日本語に翻訳する日本語または中国語の文＞");
    expect(SECTION_TARGET).toBe("＜日本語または中国語の文から中国語または日本語に翻訳を試みた文＞");
    expect(SECTION_INSTRUCTION).toBe("## 追加指示");
    expect(SECTION_ANSWER).toBe("## あなたが生成する回答");
    expect(SECTION_ERROR_POINTING).toBe("＜日本語または中国語の文から中国語または日本語に翻訳を試みた文に対する誤りの指摘＞");
    expect(SECTION_PROBLEM).toBe("## 問題");
  });
});
