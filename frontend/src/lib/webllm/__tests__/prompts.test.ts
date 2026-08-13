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
    // Uses English keys as canonical schema (per AGENTS.md)
    expect(SYSTEM_PROMPT).toContain("suggestions");
    expect(SYSTEM_PROMPT).toContain("overallComment");
  });

  it("requires why-in-reason and forbids false 缺少 inventing", () => {
    // harden-semantic-suggestion-reasons — Spec MUST in critique comments
    expect(SYSTEM_PROMPT).toContain("为什么必须改");
    expect(SYSTEM_PROMPT).toContain("缺少");
    expect(SYSTEM_PROMPT).toMatch(/臆造|禁止/);
  });

  it("requires accessible Chinese why and revised quote policy", () => {
    expect(SYSTEM_PROMPT).toMatch(/通俗|不懂日中翻译/);
    expect(SYSTEM_PROMPT).toContain("「」");
    expect(SYSTEM_PROMPT).toMatch(/""|双引号|“/);
    expect(SYSTEM_PROMPT).toMatch(/时态|中文说明/);
  });

  it("guides accurate SOURCE citation and multi-paragraph coverage", () => {
    expect(SYSTEM_PROMPT).toMatch(/误引|编造/);
    expect(SYSTEM_PROMPT).toContain("多段");
  });

  it("encodes Gemini quality-bar structure and domain", () => {
    expect(SYSTEM_PROMPT).toMatch(/优点|先写优点/);
    expect(SYSTEM_PROMPT).toMatch(/现状|→/);
    expect(SYSTEM_PROMPT).toMatch(/中译日|文学|规范译词|语域/);
  });

  it("encodes teaching-quality bar (essential gaps, anti-patterns, contrast)", () => {
    expect(SYSTEM_PROMPT).toMatch(/实质问题|意义偏移|情态/);
    expect(SYSTEM_PROMPT).toMatch(/表面|省略|简化/);
    expect(SYSTEM_PROMPT).toMatch(/跟原文对词|原文用了/);
    expect(SYSTEM_PROMPT).toMatch(/对比/);
    expect(SYSTEM_PROMPT).toMatch(/今后/);
  });

  it("exports FEW_SHOT_EXAMPLES with Gemini-shaped structure", () => {
    expect(FEW_SHOT_EXAMPLES).toBeDefined();
    expect(typeof FEW_SHOT_EXAMPLES).toBe("string");
    expect(FEW_SHOT_EXAMPLES).toContain("例");
    expect(FEW_SHOT_EXAMPLES).toContain("suggestions");
    expect(FEW_SHOT_EXAMPLES).toContain("overallComment");
    expect(FEW_SHOT_EXAMPLES).toContain("「叙事詩」");
    expect(FEW_SHOT_EXAMPLES).toMatch(/“史诗”|“/);
    expect(FEW_SHOT_EXAMPLES).toMatch(/已传达|优点|语域/);
    expect(FEW_SHOT_EXAMPLES).toContain("→");
    // Teaching bar: contrastive nuance; do not model anti-patterns as good.
    expect(FEW_SHOT_EXAMPLES).toMatch(/偏口语|偏书面|口语/);
    expect(FEW_SHOT_EXAMPLES).not.toContain("可以省略");
    expect(FEW_SHOT_EXAMPLES).not.toContain("更能体现");
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
