/**
 * WebLLM module - Client-side AI suggestion generation
 * 
 * This module provides in-browser LLM inference using WebGPU via @mlc-ai/web-llm.
 * It replaces the server-side Gemini API calls with client-side inference.
 * 
 * ## Diagnostics
 * 
 * Access window.__webllmDiagnostics in DevTools for debugging:
 * - getState() - Current phase, timing, progress
 * - getLastRunSummary() - Phase durations from last run
 */

/**
 * Barrel export for tests and offline tooling.
 *
 * App cloud path (`page.tsx`) MUST NOT statically import this barrel or
 * `./engine` — that pulls `@mlc-ai/web-llm`. Prefer:
 * - `./webgpu`, `./config`, `./diagnostics`, `./types`, `./engineReady` (cold path)
 * - `await import("./engine")` only when オフラインモード is explicitly ON (never on API failure)
 */

export { WEBLLM_MODEL_ID, WEBLLM_MODEL_DISPLAY_NAME, ALTERNATIVE_MODELS } from "./config";
export { checkWebGPUSupport, checkWebGPUAdapter, type WebGPUStatus } from "./webgpu";
export { buildPrompt, buildChatMessages, type PromptInput } from "./prompt";
export {
  parseModelOutput,
  hasNonChineseReason,
  type CorrectionSuggestion,
  type ParsedResponse,
} from "./parser";
export { isEngineReady } from "./engineReady";
export type { EngineStatus, ProgressCallback } from "./types";
export {
  initializeEngine,
  generateSuggestions,
  getCachedEngine,
  resetEngine,
  WebGPUUnsupportedError,
  ModelLoadError,
  InferenceError,
  TimeoutError,
  MODEL_LOAD_TIMEOUT_MS,
  INFERENCE_TIMEOUT_MS,
  type DiagnosticsState,
} from "./engine";
export {
  getDiagnosticsTracker,
  formatElapsedTime,
  formatDownloadProgress,
  PHASE_LABELS,
  type InferencePhase,
  type DiagnosticsTracker,
} from "./diagnostics";
