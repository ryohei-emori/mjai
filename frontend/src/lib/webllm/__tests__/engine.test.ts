/**
 * @jest-environment jsdom
 */

import {
  initializeEngine,
  generateSuggestions,
  resetEngine,
  isEngineReady,
  WebGPUUnsupportedError,
  ModelLoadError,
  InferenceError,
  TimeoutError,
  MODEL_LOAD_TIMEOUT_MS,
  INFERENCE_TIMEOUT_MS,
  type EngineStatus,
  type ProgressCallback,
} from "../engine";

// Mock the webgpu module
jest.mock("../webgpu", () => ({
  checkWebGPUSupport: jest.fn(),
  checkWebGPUAdapter: jest.fn(),
}));

// Mock the prompt module
jest.mock("../prompt", () => ({
  buildChatMessages: jest.fn(() => [{ role: "user", content: "test prompt" }]),
}));

// Mock the parser module
jest.mock("../parser", () => ({
  parseModelOutput: jest.fn(() => ({
    suggestions: [{ id: "1", original: "test", reason: "test reason" }],
    overallComment: "test comment",
  })),
}));

// Mock @mlc-ai/web-llm
const mockEngine = {
  chat: {
    completions: {
      create: jest.fn(),
    },
  },
};

jest.mock("@mlc-ai/web-llm", () => ({
  CreateMLCEngine: jest.fn(),
}));

import { checkWebGPUSupport, checkWebGPUAdapter } from "../webgpu";
import { CreateMLCEngine } from "@mlc-ai/web-llm";

const mockCheckWebGPUSupport = checkWebGPUSupport as jest.Mock;
const mockCheckWebGPUAdapter = checkWebGPUAdapter as jest.Mock;
const mockCreateMLCEngine = CreateMLCEngine as jest.Mock;

describe("WebLLM Engine", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    resetEngine();
    
    // Default: WebGPU supported
    mockCheckWebGPUSupport.mockReturnValue({ supported: true });
    mockCheckWebGPUAdapter.mockResolvedValue({ supported: true });
  });

  describe("initializeEngine", () => {
    it("throws WebGPUUnsupportedError when WebGPU is not available", async () => {
      mockCheckWebGPUSupport.mockReturnValue({
        supported: false,
        reason: "WebGPU not available",
      });

      const progressCallback = jest.fn();

      await expect(initializeEngine(progressCallback)).rejects.toThrow(
        WebGPUUnsupportedError
      );

      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({ state: "checking_webgpu" })
      );
      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          state: "unsupported",
          reason: "WebGPU not available",
        })
      );
    });

    it("throws WebGPUUnsupportedError when WebGPU adapter is not available", async () => {
      mockCheckWebGPUSupport.mockReturnValue({ supported: true });
      mockCheckWebGPUAdapter.mockResolvedValue({
        supported: false,
        reason: "No WebGPU adapter",
      });

      const progressCallback = jest.fn();

      await expect(initializeEngine(progressCallback)).rejects.toThrow(
        WebGPUUnsupportedError
      );

      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          state: "unsupported",
          reason: "No WebGPU adapter",
        })
      );
    });

    it("throws ModelLoadError when CreateMLCEngine fails", async () => {
      mockCreateMLCEngine.mockRejectedValue(new Error("Model load failed"));

      const progressCallback = jest.fn();

      await expect(initializeEngine(progressCallback)).rejects.toThrow(
        ModelLoadError
      );

      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          state: "error",
          error: "Model load failed",
        })
      );
    });

    it("throws TimeoutError when model loading times out", async () => {
      // Make CreateMLCEngine hang forever (never resolve)
      mockCreateMLCEngine.mockImplementation(
        () => new Promise(() => {})
      );

      const progressCallback = jest.fn();

      // Use a short timeout for testing
      await expect(
        initializeEngine(progressCallback, 100)
      ).rejects.toThrow(TimeoutError);

      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({ state: "error" })
      );
    }, 1000);

    it("returns cached engine on subsequent calls", async () => {
      mockCreateMLCEngine.mockResolvedValue(mockEngine);

      const progressCallback1 = jest.fn();
      const progressCallback2 = jest.fn();

      const engine1 = await initializeEngine(progressCallback1);
      const engine2 = await initializeEngine(progressCallback2);

      expect(engine1).toBe(engine2);
      expect(mockCreateMLCEngine).toHaveBeenCalledTimes(1);
      expect(progressCallback2).toHaveBeenCalledWith(
        expect.objectContaining({ state: "ready" })
      );
    });

    it("calls progress callback with loading states", async () => {
      mockCreateMLCEngine.mockImplementation(async (modelId, options) => {
        // Simulate progress callbacks
        options?.initProgressCallback?.({ progress: 0.5, text: "Loading..." });
        return mockEngine;
      });

      const progressCallback = jest.fn();
      await initializeEngine(progressCallback);

      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({ state: "checking_webgpu" })
      );
      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          state: "loading",
          progress: 0,
          text: "モデルを準備しています...",
        })
      );
      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          state: "loading",
          progress: 0.5,
          text: "Loading...",
        })
      );
      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({ state: "ready" })
      );
    });
  });

  describe("generateSuggestions", () => {
    beforeEach(() => {
      mockCreateMLCEngine.mockResolvedValue(mockEngine);
    });

    it("generates suggestions successfully", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [{ message: { content: '{"指摘": [], "全体講評": "Good!"}' } }],
      });

      const progressCallback = jest.fn();
      const result = await generateSuggestions(
        { originalText: "test", targetText: "テスト" },
        progressCallback
      );

      expect(result.suggestions).toHaveLength(1);
      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({ state: "generating" })
      );
      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({ state: "ready" })
      );
    });

    it("throws InferenceError when chat completion fails", async () => {
      mockEngine.chat.completions.create.mockRejectedValue(
        new Error("Inference failed")
      );

      const progressCallback = jest.fn();

      await expect(
        generateSuggestions(
          { originalText: "test", targetText: "テスト" },
          progressCallback
        )
      ).rejects.toThrow(InferenceError);

      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({
          state: "error",
          error: "Inference failed",
        })
      );
    });

    it("throws TimeoutError when inference times out", async () => {
      // Make inference hang forever
      mockEngine.chat.completions.create.mockImplementation(
        () => new Promise(() => {})
      );

      const progressCallback = jest.fn();

      // Use a short timeout for testing
      await expect(
        generateSuggestions(
          { originalText: "test", targetText: "テスト" },
          progressCallback,
          100
        )
      ).rejects.toThrow(TimeoutError);

      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({ state: "generating" })
      );
      expect(progressCallback).toHaveBeenCalledWith(
        expect.objectContaining({ state: "error" })
      );
    }, 1000);

    it("handles empty response gracefully", async () => {
      mockEngine.chat.completions.create.mockResolvedValue({
        choices: [],
      });

      const result = await generateSuggestions({
        originalText: "test",
        targetText: "テスト",
      });

      // parseModelOutput is mocked, so we just verify no error thrown
      expect(result).toBeDefined();
    });
  });

  describe("resetEngine", () => {
    it("clears the cached engine", async () => {
      mockCreateMLCEngine.mockResolvedValue(mockEngine);

      await initializeEngine();
      expect(isEngineReady()).toBe(true);

      resetEngine();
      expect(isEngineReady()).toBe(false);
    });
  });

  describe("isEngineReady", () => {
    it("returns false when engine is not initialized", () => {
      expect(isEngineReady()).toBe(false);
    });

    it("returns true when engine is initialized", async () => {
      mockCreateMLCEngine.mockResolvedValue(mockEngine);
      await initializeEngine();
      expect(isEngineReady()).toBe(true);
    });
  });

  describe("timeout constants", () => {
    it("has reasonable timeout values", () => {
      // Model load: 5 minutes
      expect(MODEL_LOAD_TIMEOUT_MS).toBe(5 * 60 * 1000);
      // Inference: 2 minutes
      expect(INFERENCE_TIMEOUT_MS).toBe(2 * 60 * 1000);
    });
  });

  describe("error class naming", () => {
    it("TimeoutError has correct name", () => {
      const error = new TimeoutError("test");
      expect(error.name).toBe("TimeoutError");
      expect(error.message).toBe("test");
    });

    it("WebGPUUnsupportedError has correct name", () => {
      const error = new WebGPUUnsupportedError("test");
      expect(error.name).toBe("WebGPUUnsupportedError");
    });

    it("ModelLoadError has correct name", () => {
      const error = new ModelLoadError("test");
      expect(error.name).toBe("ModelLoadError");
    });

    it("InferenceError has correct name", () => {
      const error = new InferenceError("test");
      expect(error.name).toBe("InferenceError");
    });
  });
});

describe("UI state recovery scenarios", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    resetEngine();
    mockCheckWebGPUSupport.mockReturnValue({ supported: true });
    mockCheckWebGPUAdapter.mockResolvedValue({ supported: true });
  });

  it("progress callback is called with error state even on timeout", async () => {
    mockCreateMLCEngine.mockImplementation(() => new Promise(() => {}));

    const states: EngineStatus[] = [];
    const progressCallback: ProgressCallback = (status) => {
      states.push(status);
    };

    try {
      await initializeEngine(progressCallback, 50);
    } catch {
      // Expected to throw
    }

    const errorState = states.find((s) => s.state === "error");
    expect(errorState).toBeDefined();
    expect(errorState?.state).toBe("error");
  }, 1000);

  it("allows retry after timeout by calling resetEngine", async () => {
    // First call times out
    mockCreateMLCEngine.mockImplementationOnce(() => new Promise(() => {}));

    try {
      await initializeEngine(undefined, 50);
    } catch {
      // Expected to throw TimeoutError
    }

    // Reset and try again
    resetEngine();

    // Second call succeeds
    mockCreateMLCEngine.mockResolvedValueOnce(mockEngine);
    const engine = await initializeEngine();
    expect(engine).toBe(mockEngine);
  }, 2000);
});
