/**
 * Cold-path engineReady must not pull @mlc-ai/web-llm.
 */

import { WEBLLM_MODEL_ID } from "../config";
import {
  clearEngineReady,
  isEngineReady,
  markEngineModelReady,
} from "../engineReady";

describe("engineReady", () => {
  afterEach(() => {
    clearEngineReady();
  });

  it("starts not ready", () => {
    expect(isEngineReady()).toBe(false);
  });

  it("marks ready for configured model id", () => {
    markEngineModelReady(WEBLLM_MODEL_ID);
    expect(isEngineReady()).toBe(true);
  });

  it("clearEngineReady resets flag", () => {
    markEngineModelReady(WEBLLM_MODEL_ID);
    clearEngineReady();
    expect(isEngineReady()).toBe(false);
  });
});
