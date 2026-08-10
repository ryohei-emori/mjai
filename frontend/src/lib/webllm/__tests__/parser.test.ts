import { parseModelOutput } from "../parser";

describe("parseModelOutput", () => {
  it("parses valid JSON with suggestions and overall comment", () => {
    const input = `Here is the analysis:

{
  "指摘": [
    {
      "番号": 1,
      "箇所": "我并不想回复",
      "コメント": "ようがない并非不想的含义"
    },
    {
      "番号": 2,
      "箇所": "有个孩子霸凌",
      "コメント": "这里最好把問題行為译出来哦"
    }
  ],
  "全体講評": "译文整体不错，加油～"
}

That's my analysis.`;

    const result = parseModelOutput(input);

    expect(result.suggestions).toHaveLength(2);
    expect(result.suggestions[0]).toEqual({
      id: "1",
      original: "我并不想回复",
      reason: "ようがない并非不想的含义",
    });
    expect(result.suggestions[1]).toEqual({
      id: "2",
      original: "有个孩子霸凌",
      reason: "这里最好把問題行為译出来哦",
    });
    expect(result.overallComment).toBe("译文整体不错，加油～");
  });

  it("returns empty suggestions when no JSON found", () => {
    const input = "This is a response without any JSON structure.";

    const result = parseModelOutput(input);

    expect(result.suggestions).toHaveLength(0);
    expect(result.overallComment).toContain("JSONを抽出できませんでした");
  });

  it("handles malformed JSON gracefully", () => {
    const input = `{ "指摘": [ { broken json`;

    const result = parseModelOutput(input);

    expect(result.suggestions).toHaveLength(0);
    // The regex doesn't match malformed JSON, so it returns the "no JSON found" message
    expect(result.overallComment).toContain("JSON");
  });

  it("handles empty suggestions array", () => {
    const input = `{
  "指摘": [],
  "全体講評": "素晴らしい翻訳です！"
}`;

    const result = parseModelOutput(input);

    expect(result.suggestions).toHaveLength(0);
    expect(result.overallComment).toBe("素晴らしい翻訳です！");
  });

  it("does not force-pad to 5 items (unlike old backend)", () => {
    const input = `{
  "指摘": [
    { "番号": 1, "箇所": "テスト1", "コメント": "コメント1" },
    { "番号": 2, "箇所": "テスト2", "コメント": "コメント2" },
    { "番号": 3, "箇所": "テスト3", "コメント": "コメント3" }
  ],
  "全体講評": "3つの指摘です"
}`;

    const result = parseModelOutput(input);

    expect(result.suggestions).toHaveLength(3);
  });
});
