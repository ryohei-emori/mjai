import { buildPrompt, buildChatMessages } from "../prompt";

describe("buildPrompt", () => {
  it("builds prompt with originalText and targetText", () => {
    const prompt = buildPrompt({
      originalText: "今日は天気がいいです",
      targetText: "今天天气很好",
    });

    expect(prompt).toContain("今日は天気がいいです");
    expect(prompt).toContain("今天天气很好");
    expect(prompt).toContain("## 問題");
    expect(prompt).toContain("纯JSON");
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
