/**
 * WebLLM engine management
 * Handles model loading, caching, and inference
 * 
 * ## Two-Level Caching
 * 
 * 1. **In-memory engine cache** (this module):
 *    - `cachedEngine` holds the initialized MLCEngine instance
 *    - Reused for multiple inference requests within the same page session
 *    - Cleared on page reload (module re-initialization)
 * 
 * 2. **Browser Cache API** (handled by @mlc-ai/web-llm):
 *    - Model weights (~3.7GB) are stored in browser Cache Storage
 *    - Persists across page reloads, browser sessions, and logout events
 *    - On page reload: engine re-initializes but loads weights from cache (fast)
 *    - MJAI logout does NOT clear this cache (only Supabase auth state is cleared)
 *    - See `frontend/src/lib/webllm/config.ts` for model details
 * 
 * ## Timeout Protection
 * 
 * Both model loading and inference have timeout guards to prevent infinite hangs:
 * - Model loading: 5 minutes (accounts for large downloads and GPU init)
 * - Inference: 2 minutes (should be more than enough for typical inputs)
 * 
 * Timeouts throw `TimeoutError` which the UI should handle to reset state.
 */

import { CreateMLCEngine, MLCEngine, InitProgressReport } from "@mlc-ai/web-llm";
import { WEBLLM_MODEL_ID, WEBLLM_MODEL_DISPLAY_NAME } from "./config";
import { checkWebGPUSupport, checkWebGPUAdapter } from "./webgpu";
import { buildChatMessages, PromptInput } from "./prompt";
import { parseModelOutput, ParsedResponse } from "./parser";
import {
  getDiagnosticsTracker,
  logWebLLM,
} from "./diagnostics";
import { clearEngineReady, markEngineModelReady } from "./engineReady";
import type { EngineStatus, ProgressCallback } from "./types";

// Timeout constants (in milliseconds)
export const MODEL_LOAD_TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes for model download/init
export const INFERENCE_TIMEOUT_MS = 2 * 60 * 1000;  // 2 minutes for inference

export type { EngineStatus, ProgressCallback } from "./types";
// Re-export DiagnosticsState for consumers
export type { DiagnosticsState } from "./diagnostics";
export { isEngineReady } from "./engineReady";

// Module-scoped engine instance for caching across generations
let cachedEngine: MLCEngine | null = null;
let engineModelId: string | null = null;

/**
 * Create a promise that rejects after the specified timeout
 */
function createTimeoutPromise<T>(ms: number, operationName: string): Promise<T> {
  return new Promise((_, reject) => {
    setTimeout(() => {
      reject(new TimeoutError(`${operationName}がタイムアウトしました（${Math.round(ms / 1000)}秒）`));
    }, ms);
  });
}

/**
 * Race a promise against a timeout
 */
async function withTimeout<T>(
  promise: Promise<T>,
  timeoutMs: number,
  operationName: string
): Promise<T> {
  return Promise.race([
    promise,
    createTimeoutPromise<T>(timeoutMs, operationName),
  ]);
}

/**
 * Get the cached engine if available
 */
export function getCachedEngine(): MLCEngine | null {
  return cachedEngine !== null && engineModelId === WEBLLM_MODEL_ID
    ? cachedEngine
    : null;
}

/**
 * Initialize the WebLLM engine
 * Called on first suggestion request, not on page load
 * 
 * @param onProgress - Callback for progress updates
 * @param timeoutMs - Timeout for model loading (default: MODEL_LOAD_TIMEOUT_MS)
 * @returns The initialized engine, or throws on error
 */
export async function initializeEngine(
  onProgress?: ProgressCallback,
  timeoutMs: number = MODEL_LOAD_TIMEOUT_MS
): Promise<MLCEngine> {
  const tracker = getDiagnosticsTracker();
  
  // Return cached engine if already loaded
  if (cachedEngine !== null && engineModelId === WEBLLM_MODEL_ID) {
    markEngineModelReady(WEBLLM_MODEL_ID);
    logWebLLM("info", "engine-init", "Using cached engine");
    onProgress?.({ state: "ready", diagnostics: tracker.getState() });
    return cachedEngine;
  }

  // Start diagnostics tracking
  tracker.start();

  // Check WebGPU support first
  onProgress?.({ state: "checking_webgpu", diagnostics: tracker.getState() });
  
  const basicCheck = checkWebGPUSupport();
  if (!basicCheck.supported) {
    tracker.setError(basicCheck.reason!, false);
    const status: EngineStatus = { 
      state: "unsupported", 
      reason: basicCheck.reason!,
      diagnostics: tracker.getState(),
    };
    onProgress?.(status);
    throw new WebGPUUnsupportedError(basicCheck.reason!);
  }

  const adapterCheck = await checkWebGPUAdapter();
  if (!adapterCheck.supported) {
    tracker.setError(adapterCheck.reason!, false);
    const status: EngineStatus = { 
      state: "unsupported", 
      reason: adapterCheck.reason!,
      diagnostics: tracker.getState(),
    };
    onProgress?.(status);
    throw new WebGPUUnsupportedError(adapterCheck.reason!);
  }

  // Transition to engine-init phase
  tracker.setPhase("engine-init");

  // Initialize engine with progress callback and timeout protection
  try {
    const initProgressCallback = (report: InitProgressReport) => {
      // Detect download phase from progress text
      if (report.text.includes("Loading") || report.text.includes("Fetching")) {
        if (tracker.getState().currentPhase !== "model-download") {
          tracker.setPhase("model-download");
        }
      }
      tracker.setDownloadProgress(report.progress, report.text);
      
      onProgress?.({
        state: "loading",
        progress: report.progress,
        text: report.text,
        diagnostics: tracker.getState(),
      });
    };

    onProgress?.({ 
      state: "loading", 
      progress: 0, 
      text: "モデルを準備しています...",
      diagnostics: tracker.getState(),
    });

    const enginePromise = CreateMLCEngine(WEBLLM_MODEL_ID, {
      initProgressCallback,
    });

    const engine = await withTimeout(
      enginePromise,
      timeoutMs,
      "モデルの読み込み"
    );

    // Cache the engine for subsequent requests
    cachedEngine = engine;
    engineModelId = WEBLLM_MODEL_ID;
    markEngineModelReady(WEBLLM_MODEL_ID);

    logWebLLM("info", "engine-init", "Engine initialized successfully", {
      modelId: WEBLLM_MODEL_ID,
      modelDisplayName: WEBLLM_MODEL_DISPLAY_NAME,
    });

    onProgress?.({ state: "ready", diagnostics: tracker.getState() });
    return engine;
  } catch (error) {
    // Re-throw TimeoutError as-is for proper handling
    if (error instanceof TimeoutError) {
      tracker.setError(error.message, true);
      onProgress?.({ state: "error", error: error.message, diagnostics: tracker.getState() });
      throw error;
    }
    const errorMessage = error instanceof Error ? error.message : "モデルの読み込みに失敗しました";
    tracker.setError(errorMessage, false);
    onProgress?.({ state: "error", error: errorMessage, diagnostics: tracker.getState() });
    throw new ModelLoadError(errorMessage);
  }
}

/**
 * Generate suggestions using the WebLLM engine
 * 
 * @param input - The original and target text, plus optional instruction
 * @param onProgress - Callback for progress updates
 * @param inferenceTimeoutMs - Timeout for inference (default: INFERENCE_TIMEOUT_MS)
 * @returns Parsed suggestions and overall comment
 */
export async function generateSuggestions(
  input: PromptInput,
  onProgress?: ProgressCallback,
  inferenceTimeoutMs: number = INFERENCE_TIMEOUT_MS
): Promise<ParsedResponse> {
  const tracker = getDiagnosticsTracker();
  
  // Initialize engine if needed (this handles webgpu-check, engine-init, model-download)
  const engine = await initializeEngine(onProgress);

  // Prompt build phase
  tracker.setPhase("prompt-build");
  onProgress?.({ state: "generating", diagnostics: tracker.getState() });

  try {
    const messages = buildChatMessages(input);
    logWebLLM("info", "prompt-build", "Prompt built", {
      originalTextLength: input.originalText.length,
      targetTextLength: input.targetText.length,
    });
    
    // Inference phase
    tracker.setPhase("inference");
    onProgress?.({ state: "generating", diagnostics: tracker.getState() });
    
    logWebLLM("info", "inference", "Starting inference...", {
      timestamp: new Date().toISOString(),
    });
    
    // Start heartbeat logging during inference
    const heartbeatInterval = setInterval(() => {
      const elapsedMs = tracker.getCurrentPhaseElapsedMs();
      logWebLLM("info", "inference", `Inference in progress...`, {
        elapsedMs,
        elapsedFormatted: `${(elapsedMs / 1000).toFixed(1)}s`,
      });
    }, 5000); // Log every 5 seconds during inference

    let response;
    try {
      const inferencePromise = engine.chat.completions.create({
        messages,
        temperature: 0.2,
        // Bumped 512 -> 1024 (2026-08) to fit the "at least 5 suggestions"
        // prompt target; see frontend/src/lib/webllm/config.ts.
        max_tokens: 1024,
      });

      response = await withTimeout(
        inferencePromise,
        inferenceTimeoutMs,
        "AI推論"
      );
    } finally {
      clearInterval(heartbeatInterval);
    }

    const rawOutput = response.choices[0]?.message?.content || "";
    const inferenceElapsedMs = tracker.getCurrentPhaseElapsedMs();
    
    // Log raw output preview for debugging (first 500 chars)
    const outputPreview = rawOutput.length > 500 
      ? rawOutput.substring(0, 500) + "..." 
      : rawOutput;
    logWebLLM("info", "inference", "Inference complete", {
      outputLength: rawOutput.length,
      inferenceTimeMs: inferenceElapsedMs,
      inferenceTimeFormatted: `${(inferenceElapsedMs / 1000).toFixed(1)}s`,
      outputPreview,
    });
    
    // Store raw output in diagnostics for debugging
    tracker.setLastRawOutput(rawOutput);
    
    // Parse phase
    tracker.setPhase("parse");
    onProgress?.({ state: "generating", diagnostics: tracker.getState() });
    
    const result = parseModelOutput(rawOutput);
    logWebLLM("info", "parse", "Output parsed", {
      suggestionCount: result.suggestions.length,
      hasOverallComment: !!result.overallComment,
    });
    
    // Complete
    tracker.complete();
    onProgress?.({ state: "ready", diagnostics: tracker.getState() });
    
    return result;
  } catch (error) {
    // Re-throw TimeoutError as-is for proper handling
    if (error instanceof TimeoutError) {
      tracker.setError(error.message, true);
      onProgress?.({ state: "error", error: error.message, diagnostics: tracker.getState() });
      throw error;
    }
    const errorMessage = error instanceof Error ? error.message : "推論に失敗しました";
    tracker.setError(errorMessage, false);
    onProgress?.({ state: "error", error: errorMessage, diagnostics: tracker.getState() });
    throw new InferenceError(errorMessage);
  }
}

/**
 * Reset the cached engine (useful for testing or error recovery)
 */
export function resetEngine(): void {
  cachedEngine = null;
  engineModelId = null;
  clearEngineReady();
}

// Custom error classes for different failure modes
export class WebGPUUnsupportedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "WebGPUUnsupportedError";
  }
}

export class ModelLoadError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ModelLoadError";
  }
}

export class InferenceError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InferenceError";
  }
}

export class TimeoutError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "TimeoutError";
  }
}
