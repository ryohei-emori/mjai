/**
 * WebLLM configuration
 * 
 * ## Current Model
 * - Model ID: Mistral-7B-Instruct-v0.3-q4f16_1-MLC
 * - Approximate download size: ~4-5 GB (quantized weights, tokenizer, model config)
 * - VRAM required: ~4.5 GB
 * - Quantization: 4-bit (q4f16_1) for reduced memory footprint
 * - Context window: 4096 tokens
 * - Required features: shader-f16
 * 
 * ## Generation Parameters
 * - max_tokens: 512 (sufficient for JSON with up to 3 suggestions + overall comment)
 * - temperature: 0.2 (low for consistent structured output)
 * - Input truncation: ~3000 tokens for SOURCE+TARGET (leaving headroom for system prompt)
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
 * Switched from SmolLM2-1.7B to Mistral 7B for better output quality:
 * - Mistral-7B-Instruct-v0.3-q4f16_1-MLC: ~4.5GB VRAM, strong instruction-following, good multilingual
 * - SmolLM2-1.7B-Instruct-q4f16_1-MLC: ~0.9GB, faster but struggled with consistent JSON output
 * - Phi-3.5-mini-instruct-q4f16_1-MLC: ~3.7GB, good reasoning but weaker multilingual/CJK
 * - Qwen2.5-1.5B-Instruct-q4f16_1-MLC: ~1.6GB, strong Chinese but smaller capacity
 * - Llama-3.1-8B-Instruct-q4f16_1-MLC: ~5GB, excellent quality but heavier VRAM footprint
 * 
 * ## Liquid AI LFM2.5 Status (Blocked)
 * User requested LFM2.5 ("LFG2.5") - Liquid AI's hybrid model family.
 * LFM2.5 models (2.6B, 8B-A1B) are NOT available in WebLLM's prebuilt catalog.
 * They exist only in native/GGUF/MLX/ONNX formats, not MLC format.
 * Custom compilation would be required - deferred as future enhancement.
 */

export const WEBLLM_MODEL_ID = "Mistral-7B-Instruct-v0.3-q4f16_1-MLC";

// Human-readable model name for UI display
export const WEBLLM_MODEL_DISPLAY_NAME = "Mistral 7B";

// Alternative models for future consideration
export const ALTERNATIVE_MODELS = {
  MISTRAL_7B: "Mistral-7B-Instruct-v0.3-q4f16_1-MLC",
  SMOLLM2_360M: "SmolLM2-360M-Instruct-q4f16_1-MLC",
  SMOLLM2_1_7B: "SmolLM2-1.7B-Instruct-q4f16_1-MLC",
  QWEN_2_5_1_5B: "Qwen2.5-1.5B-Instruct-q4f16_1-MLC",
  PHI_3_5_MINI: "Phi-3.5-mini-instruct-q4f16_1-MLC",
  LLAMA_3_1_8B: "Llama-3.1-8B-Instruct-q4f16_1-MLC",
} as const;
