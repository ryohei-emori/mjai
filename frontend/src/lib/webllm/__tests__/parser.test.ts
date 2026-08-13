import { parseModelOutput, hasNonChineseReason } from "../parser";

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
      sourceExcerpt: "",
    });
    expect(result.suggestions[1]).toEqual({
      id: "2",
      original: "有个孩子霸凌",
      reason: "这里最好把問題行為译出来哦",
      sourceExcerpt: "",
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

  // === HARDENED PARSER TESTS ===
  // These tests verify the parser never throws SyntaxError to break the UI

  describe("hardened parsing - trailing commas", () => {
    it("handles trailing comma in array", () => {
      const input = `{"指摘":[{"番号":1,"箇所":"test","コメント":"comment"},],"全体講評":"OK"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("test");
    });

    it("handles trailing comma in object", () => {
      const input = `{"指摘":[{"番号":1,"箇所":"test","コメント":"comment",}],"全体講評":"OK",}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
    });

    it("handles multiple trailing commas", () => {
      const input = `{
        "指摘": [
          { "番号": 1, "箇所": "a", "コメント": "b", },
          { "番号": 2, "箇所": "c", "コメント": "d", },
        ],
        "全体講評": "test",
      }`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(2);
    });
  });

  describe("hardened parsing - truncated JSON", () => {
    it("handles JSON truncated at ~position 299 (real error scenario)", () => {
      // Simulate the actual error: "SyntaxError at position 299"
      // Build a string that's truncated around position 299
      const truncatedInput = `{"指摘":[{"番号":1,"箇所":"これはテストの文章です","コメント":"この部分に問題があります"},{"番号":2,"箇所":"もう一つのテスト文","コメント":"ここも修正が必要です"},{"番号":3,"箇所":"三番目の指摘箇所","コメント":"詳細なコメントがここに入りま`;
      // This is truncated mid-string, simulating model output cutoff

      const result = parseModelOutput(truncatedInput);

      // Should not throw, should return gracefully
      expect(result).toBeDefined();
      expect(result.suggestions).toBeDefined();
      expect(Array.isArray(result.suggestions)).toBe(true);
    });

    it("handles truncated array mid-object", () => {
      const input = `{"指摘":[{"番号":1,"箇所":"test","コメント":"comment"},{"番号":2,"箇所":"test2","コメント":`;

      const result = parseModelOutput(input);

      expect(result).toBeDefined();
      // May or may not extract partial data, but must not throw
      expect(Array.isArray(result.suggestions)).toBe(true);
    });

    it("handles truncated after opening brace only", () => {
      const input = `{"指摘":[`;

      const result = parseModelOutput(input);

      expect(result).toBeDefined();
      expect(result.suggestions).toHaveLength(0);
    });
  });

  describe("hardened parsing - markdown fences", () => {
    it("handles JSON wrapped in ```json fence", () => {
      const input = "```json\n{\"指摘\":[{\"番号\":1,\"箇所\":\"test\",\"コメント\":\"comment\"}],\"全体講評\":\"OK\"}\n```";

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("test");
    });

    it("handles JSON wrapped in plain ``` fence", () => {
      const input = "```\n{\"指摘\":[],\"全体講評\":\"完璧です\"}\n```";

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(0);
      expect(result.overallComment).toBe("完璧です");
    });

    it("handles uppercase ```JSON fence", () => {
      const input = "```JSON\n{\"指摘\":[{\"番号\":1,\"箇所\":\"x\",\"コメント\":\"y\"}],\"全体講評\":\"z\"}\n```";

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
    });
  });

  describe("hardened parsing - preamble and postamble text", () => {
    it("handles preamble text before JSON", () => {
      const input = `Here is my analysis of the translation:

{\"指摘\":[{\"番号\":1,\"箇所\":\"問題箇所\",\"コメント\":\"修正案\"}],\"全体講評\":\"Good\"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("問題箇所");
    });

    it("handles postamble text after JSON", () => {
      const input = `{\"指摘\":[],\"全体講評\":\"Perfect\"}

I hope this helps! Let me know if you need anything else.`;

      const result = parseModelOutput(input);

      expect(result.overallComment).toBe("Perfect");
    });

    it("handles both preamble and postamble", () => {
      const input = `Analysis result:
{\"指摘\":[{\"番号\":1,\"箇所\":\"a\",\"コメント\":\"b\"}],\"全体講評\":\"Done\"}
End of analysis.`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.overallComment).toBe("Done");
    });
  });

  describe("hardened parsing - never throws SyntaxError", () => {
    const malformedInputs = [
      `{ "指摘": [ { broken`,
      `{"指摘":[{"番号":1,"箇所":"test"`,
      `not json at all`,
      `{"指摘": undefined}`,
      `{"指摘": [null, null]}`,
      `{"指摘": "not an array"}`,
      `{incomplete`,
      `[]`, // array instead of object
      `null`,
      ``,
      `   `,
      `{"指摘":[{"番号":1,"箇所":"has "quotes" inside","コメント":"bad"}]}`,
    ];

    malformedInputs.forEach((input, index) => {
      it(`does not throw on malformed input #${index + 1}`, () => {
        expect(() => parseModelOutput(input)).not.toThrow();
        const result = parseModelOutput(input);
        expect(result).toBeDefined();
        expect(result.suggestions).toBeDefined();
        expect(Array.isArray(result.suggestions)).toBe(true);
      });
    });
  });

  describe("hardened parsing - edge cases", () => {
    it("handles 指摘 as non-array gracefully", () => {
      const input = `{"指摘": "not an array", "全体講評": "test"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(0);
      expect(result.overallComment).toBe("test");
    });

    it("handles missing 全体講評 field", () => {
      const input = `{"指摘":[{"番号":1,"箇所":"x","コメント":"y"}]}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.overallComment).toBe("");
    });

    it("handles null values in suggestions array", () => {
      const input = `{"指摘":[null,{"番号":1,"箇所":"x","コメント":"y"},null],"全体講評":"test"}`;

      const result = parseModelOutput(input);

      // Should skip null entries
      expect(result.suggestions).toHaveLength(1);
    });

    it("handles suggestions with missing fields", () => {
      const input = `{"指摘":[{"番号":1},{"箇所":"x"},{"コメント":"y"}],"全体講評":"test"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(3);
      // All should have empty strings for missing fields
      expect(result.suggestions[0].original).toBe("");
      expect(result.suggestions[0].reason).toBe("");
    });
  });

  // === ENGLISH KEY FORMAT TESTS (canonical schema per AGENTS.md) ===
  describe("English key format (canonical)", () => {
    it("parses canonical English key format", () => {
      const input = `{"suggestions":[{"id":"1","original":"問題箇所","reason":"修正理由"}],"overallComment":"全体的に良い"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("問題箇所");
      expect(result.suggestions[0].reason).toBe("修正理由");
      expect(result.overallComment).toBe("全体的に良い");
    });

    it("parses multiple suggestions with English keys", () => {
      const input = `{
        "suggestions": [
          {"id": "1", "original": "箇所1", "reason": "理由1"},
          {"id": "2", "original": "箇所2", "reason": "理由2"}
        ],
        "overallComment": "総評コメント"
      }`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(2);
      expect(result.suggestions[0].original).toBe("箇所1");
      expect(result.suggestions[1].original).toBe("箇所2");
      expect(result.overallComment).toBe("総評コメント");
    });

    it("handles English keys with preamble/postamble", () => {
      const input = `Here's the analysis:
{"suggestions":[{"id":"1","original":"test","reason":"fix"}],"overallComment":"good"}
Hope this helps!`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("test");
      expect(result.overallComment).toBe("good");
    });

    it("handles English keys with markdown fence", () => {
      const input = "```json\n{\"suggestions\":[{\"id\":\"1\",\"original\":\"x\",\"reason\":\"y\"}],\"overallComment\":\"z\"}\n```";

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.overallComment).toBe("z");
    });

    it("handles empty suggestions array with English keys", () => {
      const input = `{"suggestions":[],"overallComment":"No issues found"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(0);
      expect(result.overallComment).toBe("No issues found");
    });

    it("prefers English keys when both formats present", () => {
      const input = `{"suggestions":[{"id":"1","original":"English","reason":"en reason"}],"overallComment":"English comment","指摘":[],"全体講評":"Japanese"}`;

      const result = parseModelOutput(input);

      // English keys should take precedence
      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("English");
      expect(result.overallComment).toBe("English comment");
    });
  });

  // === Tests for alternative field name fallbacks ===
  describe("Alternative field name fallbacks", () => {
    it("handles text/comment as alternative field names", () => {
      const input = `{"suggestions":[{"id":"1","text":"問題箇所","comment":"修正理由"}],"overallComment":"OK"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("問題箇所");
      expect(result.suggestions[0].reason).toBe("修正理由");
    });

    it("handles content/suggestion as alternative field names", () => {
      const input = `{"suggestions":[{"id":"1","content":"箇所A","suggestion":"理由B"}],"overallComment":"Done"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("箇所A");
      expect(result.suggestions[0].reason).toBe("理由B");
    });

    it("handles excerpt/fix as alternative field names", () => {
      const input = `{"suggestions":[{"id":"1","excerpt":"抜粋","fix":"修正"}],"overallComment":"完了"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("抜粋");
      expect(result.suggestions[0].reason).toBe("修正");
    });

    it("prefers original over text when both present", () => {
      const input = `{"suggestions":[{"original":"優先","text":"非優先","reason":"理由"}],"overallComment":""}`;

      const result = parseModelOutput(input);

      expect(result.suggestions[0].original).toBe("優先");
    });

    it("returns empty strings when content fields are missing", () => {
      const input = `{"suggestions":[{"id":"1"}],"overallComment":""}`;

      const result = parseModelOutput(input);

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("");
      expect(result.suggestions[0].reason).toBe("");
    });
  });

  // === Tests for optional sourceExcerpt field (highlight-suggestion-text-spans) ===
  describe("sourceExcerpt field", () => {
    it("extracts sourceExcerpt when present under the canonical key", () => {
      const input = `{"suggestions":[{"id":"1","original":"行きます","reason":"时态错误","sourceExcerpt":"行きました"}],"overallComment":"OK"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions[0].sourceExcerpt).toBe("行きました");
    });

    it("defaults to empty string when sourceExcerpt is absent", () => {
      const input = `{"suggestions":[{"id":"1","original":"良いから","reason":"语气问题"}],"overallComment":"OK"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions[0].sourceExcerpt).toBe("");
    });

    it("extracts sourceExcerpt via the 原文箇所 fallback key", () => {
      const input = `{"suggestions":[{"id":"1","original":"テスト","reason":"理由","原文箇所":"対応箇所"}],"overallComment":"OK"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions[0].sourceExcerpt).toBe("対応箇所");
    });

    it("extracts sourceExcerpt via the source/sourceText fallback keys", () => {
      const inputSource = `{"suggestions":[{"id":"1","original":"テスト","reason":"理由","source":"対応A"}],"overallComment":"OK"}`;
      const inputSourceText = `{"suggestions":[{"id":"1","original":"テスト","reason":"理由","sourceText":"対応B"}],"overallComment":"OK"}`;

      expect(parseModelOutput(inputSource).suggestions[0].sourceExcerpt).toBe("対応A");
      expect(parseModelOutput(inputSourceText).suggestions[0].sourceExcerpt).toBe("対応B");
    });

    it("prefers the canonical sourceExcerpt key over fallbacks", () => {
      const input = `{"suggestions":[{"id":"1","original":"テスト","reason":"理由","sourceExcerpt":"優先","source":"非優先"}],"overallComment":"OK"}`;

      const result = parseModelOutput(input);

      expect(result.suggestions[0].sourceExcerpt).toBe("優先");
    });
  });

  describe("hasNonChineseReason", () => {
    it("returns false for Simplified Chinese explanations", () => {
      expect(
        hasNonChineseReason({
          suggestions: [
            {
              id: "1",
              original: "行きます",
              reason: "这里应该用过去式",
              sourceExcerpt: "行きました",
            },
          ],
          overallComment: "整体表达清楚",
        })
      ).toBe(false);
    });

    it("returns true when reason contains hiragana", () => {
      expect(
        hasNonChineseReason({
          suggestions: [
            {
              id: "1",
              original: "行きます",
              reason: "ここは過去形です",
              sourceExcerpt: "",
            },
          ],
          overallComment: "中文总评",
        })
      ).toBe(true);
    });

    it("ignores Japanese in original/sourceExcerpt", () => {
      expect(
        hasNonChineseReason({
          suggestions: [
            {
              id: "1",
              original: "これはひらがなです",
              reason: "这是中文说明",
              sourceExcerpt: "行きました",
            },
          ],
          overallComment: "中文总评",
        })
      ).toBe(false);
    });

    it("allows Japanese forms quoted inside 「」 in Chinese reasons", () => {
      expect(
        hasNonChineseReason({
          suggestions: [
            {
              id: "1",
              original: "行きます",
              reason:
                "「昨日」表示的是过去发生的事情，所以应该使用过去式「行きました」",
              sourceExcerpt: "",
            },
          ],
          overallComment: "整体表达清楚",
        })
      ).toBe(false);
    });
  });
});
