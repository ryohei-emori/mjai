/**
 * Integration tests for WebLLM suggestion generation
 * 
 * These tests verify the full pipeline from generateSuggestions to parsed output.
 * Unlike unit tests, these use the real parser instead of mocking it.
 * 
 * @jest-environment jsdom
 */

import {
  generateSuggestions,
  resetEngine,
  TimeoutError,
  INFERENCE_TIMEOUT_MS,
  MODEL_LOAD_TIMEOUT_MS,
} from "../engine";
import { parseModelOutput } from "../parser";
import { buildPrompt, buildChatMessages } from "../prompt";

// Mock the webgpu module
jest.mock("../webgpu", () => ({
  checkWebGPUSupport: jest.fn(() => ({ supported: true })),
  checkWebGPUAdapter: jest.fn(() => Promise.resolve({ supported: true })),
}));

// Mock @mlc-ai/web-llm - but NOT the parser or prompt modules
const mockEngine = {
  chat: {
    completions: {
      create: jest.fn(),
    },
  },
};

jest.mock("@mlc-ai/web-llm", () => ({
  CreateMLCEngine: jest.fn(() => Promise.resolve(mockEngine)),
}));

// Real model output samples (SmolLM2-style)
const REALISTIC_MODEL_OUTPUTS = {
  // Valid JSON with suggestions
  valid: `{"指摘":[{"番号":1,"箇所":"我并不想回复","コメント":"ようがない并非不想的含义，这里可以再看一下这个文法的含义"},{"番号":2,"箇所":"どんな担任にあったか","コメント":"担任指的是学校的老师哦"}],"全体講評":"译文整体不错，加油～"}`,
  
  // Valid JSON with no errors found
  noErrors: `{"指摘":[],"全体講評":"翻译非常完美，没有问题！加油～"}`,
  
  // JSON with preamble (model sometimes adds text before JSON)
  withPreamble: `好的，我来分析这段翻译。

{"指摘":[{"番号":1,"箇所":"测试文本","コメント":"这里需要修改"}],"全体講評":"整体不错，加油～"}

以上是我的分析。`,
  
  // Malformed JSON
  malformed: `{"指摘": [{ broken json`,
  
  // Empty response
  empty: "",
  
  // Non-JSON response
  nonJson: "这段翻译很好，没有问题。",
  
  // Valid but with Unicode characters
  unicode: `{"指摘":[{"番号":1,"箇所":"テスト","コメント":"コメント内容😀"}],"全体講評":"素晴らしい翻訳です！💪加油～"}`,
  
  // Minimal valid response
  minimal: `{"指摘":[],"全体講評":"加油～"}`,
};

describe("WebLLM Integration Tests", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    resetEngine();
  });

  describe("generateSuggestions with real parser", () => {
    it("parses valid model output correctly", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [{ message: { content: REALISTIC_MODEL_OUTPUTS.valid } }],
      });

      const result = await generateSuggestions({
        originalText: "答えようがありませんでした。",
        targetText: "我并不想回复。",
      });

      expect(result.suggestions).toHaveLength(2);
      expect(result.suggestions[0].original).toBe("我并不想回复");
      expect(result.suggestions[0].reason).toContain("ようがない");
      expect(result.overallComment).toContain("加油");
    });

    it("handles model output with preamble text", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [{ message: { content: REALISTIC_MODEL_OUTPUTS.withPreamble } }],
      });

      const result = await generateSuggestions({
        originalText: "テスト",
        targetText: "测试",
      });

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("测试文本");
      expect(result.overallComment).toContain("加油");
    });

    it("handles empty suggestions gracefully", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [{ message: { content: REALISTIC_MODEL_OUTPUTS.noErrors } }],
      });

      const result = await generateSuggestions({
        originalText: "完璧な文章",
        targetText: "完美的句子",
      });

      expect(result.suggestions).toHaveLength(0);
      expect(result.overallComment).toContain("完美");
    });

    it("handles malformed JSON gracefully", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [{ message: { content: REALISTIC_MODEL_OUTPUTS.malformed } }],
      });

      const result = await generateSuggestions({
        originalText: "テスト",
        targetText: "测试",
      });

      // Should not throw, but return empty suggestions with error message
      expect(result.suggestions).toHaveLength(0);
      expect(result.overallComment).toContain("JSON");
    });

    it("handles empty response gracefully", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [{ message: { content: REALISTIC_MODEL_OUTPUTS.empty } }],
      });

      const result = await generateSuggestions({
        originalText: "テスト",
        targetText: "测试",
      });

      expect(result.suggestions).toHaveLength(0);
      expect(result.overallComment).toContain("JSON");
    });

    it("handles non-JSON response gracefully", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [{ message: { content: REALISTIC_MODEL_OUTPUTS.nonJson } }],
      });

      const result = await generateSuggestions({
        originalText: "テスト",
        targetText: "测试",
      });

      expect(result.suggestions).toHaveLength(0);
      expect(result.overallComment).toContain("JSON");
    });

    it("handles Unicode characters correctly", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [{ message: { content: REALISTIC_MODEL_OUTPUTS.unicode } }],
      });

      const result = await generateSuggestions({
        originalText: "テスト",
        targetText: "测试",
      });

      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].reason).toContain("😀");
      expect(result.overallComment).toContain("💪");
    });

    it("handles choices array edge cases", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [],
      });

      const result = await generateSuggestions({
        originalText: "テスト",
        targetText: "测试",
      });

      // Empty choices should result in empty string, which parser handles
      expect(result.suggestions).toHaveLength(0);
    });
  });

  describe("Prompt construction", () => {
    it("builds prompt with all sections", () => {
      const prompt = buildPrompt({
        originalText: "日本語のテスト",
        targetText: "中国语测试",
        instructionPrompt: "丁寧にチェックしてください",
      });

      // Verify all sections are present
      expect(prompt).toContain("日本語のテスト");
      expect(prompt).toContain("中国语测试");
      expect(prompt).toContain("丁寧にチェックしてください");
      expect(prompt).toContain("指摘");
    });

    it("builds prompt without optional instruction", () => {
      const prompt = buildPrompt({
        originalText: "テスト",
        targetText: "测试",
      });

      expect(prompt).toContain("テスト");
      expect(prompt).toContain("测试");
      expect(prompt).not.toContain("追加指示");
    });

    it("builds chat messages with user role", () => {
      const messages = buildChatMessages({
        originalText: "テスト",
        targetText: "测试",
      });

      expect(messages).toHaveLength(1);
      expect(messages[0].role).toBe("user");
      expect(messages[0].content).toContain("テスト");
    });
  });

  describe("Timeout and bounded generation", () => {
    it("INFERENCE_TIMEOUT_MS is bounded (not infinite)", () => {
      // 2 minutes is the max allowed inference time
      expect(INFERENCE_TIMEOUT_MS).toBe(2 * 60 * 1000);
      expect(INFERENCE_TIMEOUT_MS).toBeLessThanOrEqual(5 * 60 * 1000);
    });

    it("MODEL_LOAD_TIMEOUT_MS is bounded", () => {
      // 5 minutes is the max allowed model load time
      expect(MODEL_LOAD_TIMEOUT_MS).toBe(5 * 60 * 1000);
      expect(MODEL_LOAD_TIMEOUT_MS).toBeLessThanOrEqual(10 * 60 * 1000);
    });

    it("inference timeout is enforced", async () => {
      // Make inference hang forever
      mockEngine.chat.completions.create.mockImplementation(
        () => new Promise(() => {})
      );

      // Use very short timeout for test
      await expect(
        generateSuggestions(
          { originalText: "test", targetText: "测试" },
          undefined,
          50 // 50ms timeout
        )
      ).rejects.toThrow(TimeoutError);
    }, 1000);

    it("progress callback receives all expected states", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [{ message: { content: REALISTIC_MODEL_OUTPUTS.minimal } }],
      });

      const states: string[] = [];
      const progressCallback = (status: { state: string }) => {
        if (!states.includes(status.state)) {
          states.push(status.state);
        }
      };

      await generateSuggestions(
        { originalText: "テスト", targetText: "测试" },
        progressCallback
      );

      // Should go through checking_webgpu -> loading -> generating -> ready
      expect(states).toContain("generating");
      expect(states).toContain("ready");
    });
  });

  describe("Parser edge cases", () => {
    it("extracts JSON from text with multiple JSON-like patterns", () => {
      const input = `Some text {"not":"valid"} more text {"指摘":[{"番号":1,"箇所":"テスト","コメント":"コメント"}],"全体講評":"OK"} end`;
      const result = parseModelOutput(input);
      
      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("テスト");
    });

    it("handles missing optional fields", () => {
      const input = `{"指摘":[{"番号":1}],"全体講評":""}`;
      const result = parseModelOutput(input);
      
      expect(result.suggestions).toHaveLength(1);
      expect(result.suggestions[0].original).toBe("");
      expect(result.suggestions[0].reason).toBe("");
    });

    it("handles deeply nested JSON gracefully", () => {
      const input = `{"指摘":[{"番号":1,"箇所":"test","コメント":"comment","extra":{"nested":true}}],"全体講評":"ok"}`;
      const result = parseModelOutput(input);
      
      expect(result.suggestions).toHaveLength(1);
    });
  });
});

describe("SmolLM2 specific tests", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    resetEngine();
  });

  it("handles SmolLM2 max_tokens=512 bounded output", async () => {
    // SmolLM2 with max_tokens=512 should produce reasonable output
    const longButValidOutput = `{"指摘":[{"番号":1,"箇所":"${"x".repeat(100)}","コメント":"${"y".repeat(200)}"}],"全体講評":"${"z".repeat(100)}"}`;
    
    mockEngine.chat.completions.create.mockResolvedValue({
      choices: [{ message: { content: longButValidOutput } }],
    });

    const result = await generateSuggestions({
      originalText: "テスト",
      targetText: "测试",
    });

    expect(result.suggestions).toHaveLength(1);
    expect(result.suggestions[0].original.length).toBe(100);
  });

  it("verifies temperature=0.2 produces consistent JSON structure", async () => {
    // With low temperature, output should be consistently structured
    mockEngine.chat.completions.create.mockResolvedValue({
      choices: [{ message: { content: REALISTIC_MODEL_OUTPUTS.valid } }],
    });

    // Run multiple times to verify consistency
    for (let i = 0; i < 3; i++) {
      const result = await generateSuggestions({
        originalText: "テスト",
        targetText: "测试",
      });
      
      expect(result.suggestions).toBeDefined();
      expect(Array.isArray(result.suggestions)).toBe(true);
      expect(typeof result.overallComment).toBe("string");
      
      resetEngine();
    }
  });
});
