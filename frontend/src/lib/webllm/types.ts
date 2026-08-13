/**
 * WebLLM UI/status types — safe to import on the cloud-API cold path.
 * Must not import `@mlc-ai/web-llm` or `engine.ts`.
 */

import type { DiagnosticsState } from "./diagnostics";

export type EngineStatus =
  | { state: "idle"; diagnostics?: DiagnosticsState }
  | { state: "checking_webgpu"; diagnostics?: DiagnosticsState }
  | {
      state: "loading";
      progress: number;
      text: string;
      diagnostics?: DiagnosticsState;
    }
  | { state: "ready"; diagnostics?: DiagnosticsState }
  | { state: "generating"; diagnostics?: DiagnosticsState }
  | { state: "error"; error: string; diagnostics?: DiagnosticsState }
  | { state: "unsupported"; reason: string; diagnostics?: DiagnosticsState };

export type ProgressCallback = (status: EngineStatus) => void;
