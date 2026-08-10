/**
 * WebLLM Diagnostics Module
 * 
 * Provides detailed phase tracking, timing, and logging for AI inference.
 * Used to diagnose slow performance, hangs, and errors.
 */

import { WEBLLM_MODEL_ID, WEBLLM_MODEL_DISPLAY_NAME } from "./config";

/**
 * Inference phases in order of execution
 */
export type InferencePhase = 
  | "idle"
  | "webgpu-check"
  | "engine-init"
  | "model-download"
  | "prompt-build"
  | "inference"
  | "parse"
  | "done"
  | "error"
  | "timeout";

/**
 * Japanese labels for each phase (for UI display)
 */
export const PHASE_LABELS: Record<InferencePhase, string> = {
  "idle": "待機中",
  "webgpu-check": "WebGPU確認中",
  "engine-init": "エンジン初期化中",
  "model-download": "モデルダウンロード中",
  "prompt-build": "プロンプト構築中",
  "inference": "AI推論中",
  "parse": "結果解析中",
  "done": "完了",
  "error": "エラー",
  "timeout": "タイムアウト",
};

/**
 * Phase timing data
 */
export type PhaseTimingRecord = {
  phase: InferencePhase;
  startedAt: number;
  endedAt?: number;
  durationMs?: number;
};

/**
 * Current diagnostics state
 */
export type DiagnosticsState = {
  modelId: string;
  modelDisplayName: string;
  currentPhase: InferencePhase;
  phaseLabel: string;
  currentPhaseStartedAt: number | null;
  currentPhaseElapsedMs: number;
  totalStartedAt: number | null;
  totalElapsedMs: number;
  downloadProgress: number | null;
  downloadText: string | null;
  lastError: string | null;
  timeoutPhase: InferencePhase | null;
  phaseHistory: PhaseTimingRecord[];
};

/**
 * Format milliseconds to human-readable string
 * @example formatElapsedTime(65000) => "1:05"
 * @example formatElapsedTime(3500) => "3.5秒"
 */
export function formatElapsedTime(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }
  if (ms < 60000) {
    const seconds = ms / 1000;
    return `${seconds.toFixed(1)}秒`;
  }
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

/**
 * Format download progress percentage
 */
export function formatDownloadProgress(progress: number): string {
  return `${Math.round(progress * 100)}%`;
}

/**
 * Console logger with [webllm] prefix
 */
export function logWebLLM(
  level: "info" | "warn" | "error",
  phase: InferencePhase,
  message: string,
  data?: Record<string, unknown>
): void {
  const timestamp = new Date().toISOString();
  const prefix = `[webllm] [${phase}]`;
  const logData = {
    timestamp,
    phase,
    modelId: WEBLLM_MODEL_ID,
    ...data,
  };

  switch (level) {
    case "info":
      console.info(`${prefix} ${message}`, logData);
      break;
    case "warn":
      console.warn(`${prefix} ${message}`, logData);
      break;
    case "error":
      console.error(`${prefix} ${message}`, logData);
      break;
  }
}

/**
 * Diagnostics tracker class
 * Tracks phases, timing, and provides state snapshots
 */
export class DiagnosticsTracker {
  private currentPhase: InferencePhase = "idle";
  private currentPhaseStartedAt: number | null = null;
  private totalStartedAt: number | null = null;
  private downloadProgress: number | null = null;
  private downloadText: string | null = null;
  private lastError: string | null = null;
  private timeoutPhase: InferencePhase | null = null;
  private phaseHistory: PhaseTimingRecord[] = [];
  private lastRawOutput: string | null = null;

  /**
   * Start a new inference run (resets all state)
   */
  start(): void {
    const now = Date.now();
    this.currentPhase = "webgpu-check";
    this.currentPhaseStartedAt = now;
    this.totalStartedAt = now;
    this.downloadProgress = null;
    this.downloadText = null;
    this.lastError = null;
    this.timeoutPhase = null;
    this.phaseHistory = [];
    
    this.recordPhaseStart("webgpu-check", now);
    logWebLLM("info", "webgpu-check", "Starting inference run");
  }

  /**
   * Transition to a new phase
   */
  setPhase(phase: InferencePhase): void {
    const now = Date.now();
    
    // Record end of previous phase
    if (this.currentPhase !== "idle" && this.phaseHistory.length > 0) {
      const lastRecord = this.phaseHistory[this.phaseHistory.length - 1];
      if (!lastRecord.endedAt) {
        lastRecord.endedAt = now;
        lastRecord.durationMs = now - lastRecord.startedAt;
      }
    }

    const previousPhase = this.currentPhase;
    this.currentPhase = phase;
    this.currentPhaseStartedAt = now;
    
    this.recordPhaseStart(phase, now);
    
    logWebLLM("info", phase, `Phase transition: ${previousPhase} → ${phase}`, {
      previousPhase,
      elapsedSinceStart: this.totalStartedAt ? now - this.totalStartedAt : 0,
    });
  }

  /**
   * Update download progress (during model-download phase)
   */
  setDownloadProgress(progress: number, text?: string): void {
    this.downloadProgress = progress;
    this.downloadText = text || null;
    
    // Log progress at 10% intervals
    const progressPercent = Math.round(progress * 100);
    if (progressPercent % 10 === 0 || progressPercent === 100) {
      logWebLLM("info", "model-download", `Download progress: ${progressPercent}%`, {
        progress,
        text,
      });
    }
  }

  /**
   * Record an error
   */
  setError(error: string, isTimeout: boolean = false): void {
    this.lastError = error;
    if (isTimeout) {
      this.timeoutPhase = this.currentPhase;
      logWebLLM("error", this.currentPhase, `Timeout in phase: ${this.currentPhase}`, {
        timeoutPhase: this.currentPhase,
        elapsedMs: this.getCurrentPhaseElapsedMs(),
        error,
      });
    } else {
      logWebLLM("error", this.currentPhase, `Error: ${error}`, { error });
    }
    this.setPhase(isTimeout ? "timeout" : "error");
  }

  /**
   * Mark inference as complete
   */
  complete(): void {
    const now = Date.now();
    const totalMs = this.totalStartedAt ? now - this.totalStartedAt : 0;
    
    logWebLLM("info", "done", "Inference complete", {
      totalElapsedMs: totalMs,
      phaseCount: this.phaseHistory.length,
    });
    
    this.setPhase("done");
  }

  /**
   * Reset to idle state
   */
  reset(): void {
    this.currentPhase = "idle";
    this.currentPhaseStartedAt = null;
    this.totalStartedAt = null;
    this.downloadProgress = null;
    this.downloadText = null;
    this.lastError = null;
    this.timeoutPhase = null;
    // Keep phaseHistory for debugging
  }

  /**
   * Get current phase elapsed time in ms
   */
  getCurrentPhaseElapsedMs(): number {
    if (!this.currentPhaseStartedAt) return 0;
    return Date.now() - this.currentPhaseStartedAt;
  }

  /**
   * Get total elapsed time in ms
   */
  getTotalElapsedMs(): number {
    if (!this.totalStartedAt) return 0;
    return Date.now() - this.totalStartedAt;
  }

  /**
   * Get a snapshot of current diagnostics state
   */
  getState(): DiagnosticsState {
    return {
      modelId: WEBLLM_MODEL_ID,
      modelDisplayName: WEBLLM_MODEL_DISPLAY_NAME,
      currentPhase: this.currentPhase,
      phaseLabel: PHASE_LABELS[this.currentPhase],
      currentPhaseStartedAt: this.currentPhaseStartedAt,
      currentPhaseElapsedMs: this.getCurrentPhaseElapsedMs(),
      totalStartedAt: this.totalStartedAt,
      totalElapsedMs: this.getTotalElapsedMs(),
      downloadProgress: this.downloadProgress,
      downloadText: this.downloadText,
      lastError: this.lastError,
      timeoutPhase: this.timeoutPhase,
      phaseHistory: [...this.phaseHistory],
    };
  }

  /**
   * Store the last raw output for debugging
   */
  setLastRawOutput(output: string): void {
    this.lastRawOutput = output;
  }

  /**
   * Get the last raw model output (for debugging)
   */
  getLastRawOutput(): string | null {
    return this.lastRawOutput;
  }

  /**
   * Get last run diagnostics (for DevTools inspection)
   */
  getLastRunSummary(): {
    phases: Array<{ phase: string; durationMs: number }>;
    totalMs: number;
    error: string | null;
    timeoutPhase: string | null;
    lastRawOutput: string | null;
  } {
    const totalMs = this.phaseHistory.reduce((sum, r) => sum + (r.durationMs || 0), 0);
    return {
      phases: this.phaseHistory
        .filter(r => r.durationMs !== undefined)
        .map(r => ({ phase: r.phase, durationMs: r.durationMs! })),
      totalMs,
      error: this.lastError,
      timeoutPhase: this.timeoutPhase,
      lastRawOutput: this.lastRawOutput,
    };
  }

  private recordPhaseStart(phase: InferencePhase, startedAt: number): void {
    this.phaseHistory.push({
      phase,
      startedAt,
    });
  }
}

// Global singleton for DevTools access
let globalTracker: DiagnosticsTracker | null = null;

/**
 * Get the global diagnostics tracker (creates one if needed)
 */
export function getDiagnosticsTracker(): DiagnosticsTracker {
  if (!globalTracker) {
    globalTracker = new DiagnosticsTracker();
  }
  return globalTracker;
}

/**
 * Expose to window for DevTools debugging
 */
if (typeof window !== "undefined") {
  (window as unknown as { __webllmDiagnostics?: DiagnosticsTracker }).
    __webllmDiagnostics = getDiagnosticsTracker();
}
