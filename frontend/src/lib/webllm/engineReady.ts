/**
 * Lightweight engine-ready flag for UI (e.g. 「初回DL」).
 * Synced by engine.ts — does not import `@mlc-ai/web-llm`.
 */

import { WEBLLM_MODEL_ID } from "./config";

let readyModelId: string | null = null;

export function markEngineModelReady(modelId: string = WEBLLM_MODEL_ID): void {
  readyModelId = modelId;
}

export function clearEngineReady(): void {
  readyModelId = null;
}

/**
 * True when the WebLLM engine has been initialized for the configured model
 * in this page session (in-memory only; not a Cache API probe).
 */
export function isEngineReady(): boolean {
  return readyModelId === WEBLLM_MODEL_ID;
}
