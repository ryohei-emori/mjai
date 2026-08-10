/**
 * Tests for WebLLM diagnostics module
 */

import {
  formatElapsedTime,
  formatDownloadProgress,
  PHASE_LABELS,
  DiagnosticsTracker,
  type InferencePhase,
} from "../diagnostics";

describe("formatElapsedTime", () => {
  it("formats milliseconds for values under 1 second", () => {
    expect(formatElapsedTime(0)).toBe("0ms");
    expect(formatElapsedTime(500)).toBe("500ms");
    expect(formatElapsedTime(999)).toBe("999ms");
  });

  it("formats seconds for values under 1 minute", () => {
    expect(formatElapsedTime(1000)).toBe("1.0秒");
    expect(formatElapsedTime(1500)).toBe("1.5秒");
    expect(formatElapsedTime(30000)).toBe("30.0秒");
    expect(formatElapsedTime(59999)).toBe("60.0秒");
  });

  it("formats minutes:seconds for values 1 minute and above", () => {
    expect(formatElapsedTime(60000)).toBe("1:00");
    expect(formatElapsedTime(65000)).toBe("1:05");
    expect(formatElapsedTime(125000)).toBe("2:05");
    expect(formatElapsedTime(3600000)).toBe("60:00");
  });
});

describe("formatDownloadProgress", () => {
  it("formats progress as percentage", () => {
    expect(formatDownloadProgress(0)).toBe("0%");
    expect(formatDownloadProgress(0.5)).toBe("50%");
    expect(formatDownloadProgress(0.99)).toBe("99%");
    expect(formatDownloadProgress(1)).toBe("100%");
  });

  it("rounds to nearest integer", () => {
    expect(formatDownloadProgress(0.123)).toBe("12%");
    expect(formatDownloadProgress(0.456)).toBe("46%");
    expect(formatDownloadProgress(0.789)).toBe("79%");
  });
});

describe("PHASE_LABELS", () => {
  it("has Japanese labels for all phases", () => {
    const expectedPhases: InferencePhase[] = [
      "idle",
      "webgpu-check",
      "engine-init",
      "model-download",
      "prompt-build",
      "inference",
      "parse",
      "done",
      "error",
      "timeout",
    ];

    expectedPhases.forEach((phase) => {
      expect(PHASE_LABELS[phase]).toBeDefined();
      expect(typeof PHASE_LABELS[phase]).toBe("string");
      expect(PHASE_LABELS[phase].length).toBeGreaterThan(0);
    });
  });
});

describe("DiagnosticsTracker", () => {
  let tracker: DiagnosticsTracker;

  beforeEach(() => {
    tracker = new DiagnosticsTracker();
  });

  describe("initial state", () => {
    it("starts in idle state", () => {
      const state = tracker.getState();
      expect(state.currentPhase).toBe("idle");
      expect(state.totalStartedAt).toBeNull();
      expect(state.currentPhaseStartedAt).toBeNull();
    });
  });

  describe("start()", () => {
    it("initializes tracking and transitions to webgpu-check", () => {
      tracker.start();
      const state = tracker.getState();
      
      expect(state.currentPhase).toBe("webgpu-check");
      expect(state.totalStartedAt).not.toBeNull();
      expect(state.currentPhaseStartedAt).not.toBeNull();
      expect(state.phaseHistory.length).toBe(1);
      expect(state.phaseHistory[0].phase).toBe("webgpu-check");
    });

    it("resets error state", () => {
      tracker.setError("Test error");
      tracker.start();
      const state = tracker.getState();
      
      expect(state.lastError).toBeNull();
      expect(state.timeoutPhase).toBeNull();
    });
  });

  describe("setPhase()", () => {
    it("transitions to new phase", () => {
      tracker.start();
      tracker.setPhase("engine-init");
      
      const state = tracker.getState();
      expect(state.currentPhase).toBe("engine-init");
      expect(state.phaseHistory.length).toBe(2);
    });

    it("records duration of previous phase", () => {
      tracker.start();
      
      // Wait a bit to get measurable duration
      const waitMs = 10;
      const startTime = Date.now();
      while (Date.now() - startTime < waitMs) {
        // busy wait
      }
      
      tracker.setPhase("engine-init");
      
      const state = tracker.getState();
      const firstPhase = state.phaseHistory[0];
      expect(firstPhase.endedAt).toBeDefined();
      expect(firstPhase.durationMs).toBeGreaterThanOrEqual(0);
    });
  });

  describe("setDownloadProgress()", () => {
    it("updates download progress", () => {
      tracker.start();
      tracker.setPhase("model-download");
      tracker.setDownloadProgress(0.5, "Loading model...");
      
      const state = tracker.getState();
      expect(state.downloadProgress).toBe(0.5);
      expect(state.downloadText).toBe("Loading model...");
    });
  });

  describe("setError()", () => {
    it("records error without timeout", () => {
      tracker.start();
      tracker.setPhase("inference");
      tracker.setError("Test error", false);
      
      const state = tracker.getState();
      expect(state.lastError).toBe("Test error");
      expect(state.currentPhase).toBe("error");
      expect(state.timeoutPhase).toBeNull();
    });

    it("records timeout phase when isTimeout is true", () => {
      tracker.start();
      tracker.setPhase("inference");
      tracker.setError("Timeout error", true);
      
      const state = tracker.getState();
      expect(state.lastError).toBe("Timeout error");
      expect(state.currentPhase).toBe("timeout");
      expect(state.timeoutPhase).toBe("inference");
    });
  });

  describe("complete()", () => {
    it("transitions to done state", () => {
      tracker.start();
      tracker.setPhase("inference");
      tracker.complete();
      
      const state = tracker.getState();
      expect(state.currentPhase).toBe("done");
    });
  });

  describe("reset()", () => {
    it("resets to idle state but keeps history", () => {
      tracker.start();
      tracker.setPhase("inference");
      tracker.reset();
      
      const state = tracker.getState();
      expect(state.currentPhase).toBe("idle");
      expect(state.totalStartedAt).toBeNull();
      expect(state.phaseHistory.length).toBeGreaterThan(0);
    });
  });

  describe("getLastRunSummary()", () => {
    it("returns summary of completed phases", () => {
      tracker.start();
      tracker.setPhase("engine-init");
      tracker.setPhase("inference");
      tracker.complete();
      
      const summary = tracker.getLastRunSummary();
      expect(summary.phases.length).toBeGreaterThan(0);
      expect(summary.error).toBeNull();
      expect(summary.timeoutPhase).toBeNull();
    });

    it("includes error info when present", () => {
      tracker.start();
      tracker.setPhase("inference");
      tracker.setError("Test error", true);
      
      const summary = tracker.getLastRunSummary();
      expect(summary.error).toBe("Test error");
      expect(summary.timeoutPhase).toBe("inference");
    });
  });

  describe("timing helpers", () => {
    it("getCurrentPhaseElapsedMs returns elapsed time", () => {
      tracker.start();
      
      // Wait a bit
      const waitMs = 10;
      const startTime = Date.now();
      while (Date.now() - startTime < waitMs) {
        // busy wait
      }
      
      const elapsed = tracker.getCurrentPhaseElapsedMs();
      expect(elapsed).toBeGreaterThanOrEqual(waitMs - 1);
    });

    it("getTotalElapsedMs returns total elapsed time", () => {
      tracker.start();
      
      // Wait a bit
      const waitMs = 10;
      const startTime = Date.now();
      while (Date.now() - startTime < waitMs) {
        // busy wait
      }
      
      tracker.setPhase("engine-init");
      
      const elapsed = tracker.getTotalElapsedMs();
      expect(elapsed).toBeGreaterThanOrEqual(waitMs - 1);
    });

    it("returns 0 before tracking starts", () => {
      expect(tracker.getCurrentPhaseElapsedMs()).toBe(0);
      expect(tracker.getTotalElapsedMs()).toBe(0);
    });
  });
});
