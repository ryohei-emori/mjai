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

export { WEBLLM_MODEL_ID, WEBLLM_MODEL_DISPLAY_NAME, ALTERNATIVE_MODELS } from "./config";
export { checkWebGPUSupport, checkWebGPUAdapter, type WebGPUStatus } from "./webgpu";
export { buildPrompt, buildChatMessages, type PromptInput } from "./prompt";
export { parseModelOutput, type CorrectionSuggestion, type ParsedResponse } from "./parser";
export {
  initializeEngine,
  generateSuggestions,
  isEngineReady,
  getCachedEngine,
  resetEngine,
  WebGPUUnsupportedError,
  ModelLoadError,
  InferenceError,
  TimeoutError,
  MODEL_LOAD_TIMEOUT_MS,
  INFERENCE_TIMEOUT_MS,
  type EngineStatus,
  type ProgressCallback,
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
