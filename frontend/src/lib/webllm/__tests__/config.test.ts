/**
 * @jest-environment jsdom
 */

import { WEBLLM_MODEL_ID, WEBLLM_MODEL_DISPLAY_NAME, ALTERNATIVE_MODELS } from "../config";

describe("WebLLM Config", () => {
  describe("WEBLLM_MODEL_ID", () => {
    it("exports the current model ID", () => {
      expect(WEBLLM_MODEL_ID).toBe("SmolLM2-1.7B-Instruct-q4f16_1-MLC");
    });

    it("model ID follows MLC naming convention", () => {
      expect(WEBLLM_MODEL_ID).toMatch(/-MLC$/);
    });
  });

  describe("WEBLLM_MODEL_DISPLAY_NAME", () => {
    it("exports a human-readable model name", () => {
      expect(WEBLLM_MODEL_DISPLAY_NAME).toBe("SmolLM2 1.7B");
    });

    it("is concise for UI display", () => {
      expect(WEBLLM_MODEL_DISPLAY_NAME.length).toBeLessThan(20);
    });
  });

  describe("ALTERNATIVE_MODELS", () => {
    it("includes SmolLM2 variants", () => {
      expect(ALTERNATIVE_MODELS.SMOLLM2_360M).toBeDefined();
      expect(ALTERNATIVE_MODELS.SMOLLM2_1_7B).toBeDefined();
    });

    it("includes larger models for quality", () => {
      expect(ALTERNATIVE_MODELS.PHI_3_5_MINI).toBeDefined();
      expect(ALTERNATIVE_MODELS.LLAMA_3_1_8B).toBeDefined();
    });

    it("all model IDs follow MLC naming convention", () => {
      Object.values(ALTERNATIVE_MODELS).forEach((modelId) => {
        expect(modelId).toMatch(/-MLC$/);
      });
    });
  });
});
