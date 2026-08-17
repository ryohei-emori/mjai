import { buildPrompt, buildChatMessages, buildSystemPrompt } from "../prompt";
import {
  SYSTEM_PROMPT,
  SYSTEM_PROMPT_HEAD,
  SYSTEM_PROMPT_TAIL,
  OUTPUT_CONTRACT,
} from "../prompts";

describe("buildPrompt", () => {
  it("builds prompt with originalText and targetText", () => {
    const prompt = buildPrompt({
      originalText: "今日は天気がいいです",
      targetText: "今天天气很好",
    });

    expect(prompt).toContain("今日は天気がいいです");
    expect(prompt).toContain("今天天气很好");
    expect(prompt).toContain("## 問題");
    // Ultra-short SmolLM2-optimized prompt contains JSON instruction
    expect(prompt).toContain("JSON");
    expect(prompt).toContain(
      "意味の不一致、文法、流暢さ、スペルミスに焦点を当てて、この課題を添削してください。"
    );
    expect(prompt).toContain("简体中文");
  });

  it("includes instructionPrompt when provided", () => {
    const prompt = buildPrompt({
      originalText: "テスト",
      targetText: "测试",
      instructionPrompt: "特に文法に注意してください",
    });

    expect(prompt).toContain("## 追加指示");
    expect(prompt).toContain("特に文法に注意してください");
  });

  it("does not include instruction section when instructionPrompt is empty", () => {
    const prompt = buildPrompt({
      originalText: "テスト",
      targetText: "测试",
      instructionPrompt: "",
    });

    expect(prompt).not.toContain("## 追加指示");
  });

  describe("optional exemplarTranslation (模範回答訳文)", () => {
    const baseInput = { originalText: "テスト", targetText: "测试" };

    it("includes the exemplar section and its guard rules when provided", () => {
      const prompt = buildPrompt({
        ...baseInput,
        exemplarTranslation: "模範の訳文です",
      });

      expect(prompt).toContain("模範回答訳文");
      expect(prompt).toContain("模範の訳文です");
      expect(prompt).toContain("MUST仍以原文为判断依据");
      expect(prompt).toContain("禁止在reason/overallComment里提及参考译文");
    });

    it("places the exemplar between SOURCE and TARGET sections", () => {
      const prompt = buildPrompt({
        originalText: "原文セクション",
        targetText: "対象セクション",
        exemplarTranslation: "模範セクション",
      });

      expect(prompt.indexOf("原文セクション")).toBeLessThan(
        prompt.indexOf("模範セクション")
      );
      expect(prompt.indexOf("模範セクション")).toBeLessThan(
        prompt.indexOf("対象セクション")
      );
    });

    it("leaves the prompt byte-identical when the exemplar is absent or blank", () => {
      // The backward-compat guarantee: an offline user without an exemplar
      // must get exactly the prompt they got before this field existed.
      const baseline = buildPrompt(baseInput);

      expect(buildPrompt({ ...baseInput, exemplarTranslation: "" })).toBe(baseline);
      expect(buildPrompt({ ...baseInput, exemplarTranslation: "   \n" })).toBe(
        baseline
      );
      expect(baseline).not.toContain("模範回答訳文");
    });

    it("trims surrounding whitespace from the exemplar", () => {
      const prompt = buildPrompt({
        ...baseInput,
        exemplarTranslation: "  模範の訳文です \n",
      });

      expect(prompt).toContain("＞\n模範の訳文です\n\n");
    });
  });
});

describe("shared prompt override (systemPromptOverride)", () => {
  const baseInput = { originalText: "テスト", targetText: "测试" };

  it("keeps the built-in offline prompt intact when the parts are reassembled", () => {
    // The split exists so an override can replace the rules without taking the
    // JSON contract with it. If reassembly drifted, every offline user without a
    // custom prompt would silently get a different prompt than the one measured
    // against Mistral 7B.
    expect(SYSTEM_PROMPT).toBe(
      `${SYSTEM_PROMPT_HEAD}${OUTPUT_CONTRACT}\n${SYSTEM_PROMPT_TAIL}`,
    );
    expect(SYSTEM_PROMPT).toContain(
      "中译日文学/学术翻译校对。只输出JSON，禁止其他文字。",
    );
    expect(SYSTEM_PROMPT.startsWith("意味の不一致、文法、流暢さ、スペルミス")).toBe(
      true,
    );
  });

  it("leaves the prompt byte-identical when no override is supplied", () => {
    // The backward-compat guarantee: an offline user who never customized the
    // shared prompt must get exactly the prompt they got before it could reach
    // this path.
    const baseline = buildPrompt(baseInput);

    expect(buildPrompt({ ...baseInput, systemPromptOverride: undefined })).toBe(
      baseline,
    );
    expect(buildPrompt({ ...baseInput, systemPromptOverride: "" })).toBe(baseline);
    expect(buildPrompt({ ...baseInput, systemPromptOverride: "  \n " })).toBe(
      baseline,
    );
    expect(baseline).toContain(SYSTEM_PROMPT);
  });

  it("replaces the rules body but keeps the code-owned contract and example", () => {
    const prompt = buildPrompt({
      ...baseInput,
      systemPromptOverride: "只指出助词错误。",
    });

    expect(prompt).toContain("只指出助词错误。");
    expect(prompt).toContain(OUTPUT_CONTRACT);
    // The example is appended by code, so an override cannot drop it.
    expect(prompt).toContain('输出：{"suggestions"');
    // The built-in rules are what the override replaces.
    expect(prompt).not.toContain(SYSTEM_PROMPT_TAIL);
  });

  it("appends the contract last so an override cannot bury it", () => {
    const prompt = buildSystemPrompt(undefined, "OPERATOR_RULES");

    expect(prompt).toBe(`OPERATOR_RULES\n${OUTPUT_CONTRACT}`);
  });

  it("keeps the exemplar rules between the override and the contract", () => {
    const prompt = buildSystemPrompt("模範の訳文です", "OPERATOR_RULES");

    expect(prompt.indexOf("OPERATOR_RULES")).toBeLessThan(
      prompt.indexOf("MUST仍以原文为判断依据"),
    );
    expect(prompt.indexOf("MUST仍以原文为判断依据")).toBeLessThan(
      prompt.indexOf(OUTPUT_CONTRACT),
    );
  });

  it("trims the override so stored whitespace cannot detach the contract", () => {
    expect(buildSystemPrompt(undefined, "  OPERATOR_RULES  ")).toBe(
      `OPERATOR_RULES\n${OUTPUT_CONTRACT}`,
    );
  });
});

describe("buildChatMessages", () => {
  it("returns array with single user message", () => {
    const messages = buildChatMessages({
      originalText: "テスト",
      targetText: "测试",
    });

    expect(messages).toHaveLength(1);
    expect(messages[0].role).toBe("user");
    expect(messages[0].content).toContain("テスト");
  });
});
