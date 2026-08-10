/**
 * WebLLM configuration
 * 
 * ## Current Model
 * - Model ID: SmolLM2-1.7B-Instruct-q4f16_1-MLC
 * - Approximate download size: ~0.9 GB (quantized weights, tokenizer, model config)
 * - VRAM required: ~1.8 GB
 * - Quantization: 4-bit (q4f16_1) for reduced memory footprint
 * - Context window: 8192 tokens (8K)
 * 
 * ## Caching Behavior
 * - @mlc-ai/web-llm uses the browser's Cache API (via MLC's tvmjs runtime)
 * - Model weights are stored in browser Cache Storage (DevTools → Application → Cache Storage)
 * - Cache persists across page reloads, browser sessions, and logout events
 * - MJAI logout does NOT clear the model cache (only Supabase auth state is cleared)
 * - First visit downloads full model; subsequent visits load from cache
 * - Browser may evict cache under storage pressure (standard browser behavior)
 * 
 * ## Model Selection Rationale
 * - SmolLM2-1.7B-Instruct-q4f16_1-MLC: ~0.9GB, fastest inference, good for structured output
 * - SmolLM2-360M-Instruct-q4f16_1-MLC: ~0.4GB, even faster but lower quality
 * - Phi-3.5-mini-instruct-q4f16_1-MLC: ~3.7GB, better reasoning but slow in browser
 * - Qwen2.5-1.5B-Instruct-q4f16_1-MLC: ~1.6GB, strong multilingual quality
 * 
 * Previously used Phi-3.5-mini but switched to SmolLM2-1.7B for faster inference.
 * 
 * ## Liquid AI LFM2.5 Status (Blocked)
 * User requested LFM2.5 ("LFG2.5") - Liquid AI's hybrid model family.
 * LFM2.5 models (2.6B, 8B-A1B) are NOT available in WebLLM's prebuilt catalog.
 * They exist only in native/GGUF/MLX/ONNX formats, not MLC format.
 * Custom compilation would be required - deferred as future enhancement.
 */

export const WEBLLM_MODEL_ID = "SmolLM2-1.7B-Instruct-q4f16_1-MLC";

// Human-readable model name for UI display
export const WEBLLM_MODEL_DISPLAY_NAME = "SmolLM2 1.7B";

// Alternative models for future consideration
export const ALTERNATIVE_MODELS = {
  SMOLLM2_360M: "SmolLM2-360M-Instruct-q4f16_1-MLC",
  SMOLLM2_1_7B: "SmolLM2-1.7B-Instruct-q4f16_1-MLC",
  QWEN_2_5_1_5B: "Qwen2.5-1.5B-Instruct-q4f16_1-MLC",
  PHI_3_5_MINI: "Phi-3.5-mini-instruct-q4f16_1-MLC",
  LLAMA_3_1_8B: "Llama-3.1-8B-Instruct-q4f16_1-MLC",
} as const;
