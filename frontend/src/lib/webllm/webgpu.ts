/**
 * WebGPU feature detection utilities
 */

export type WebGPUStatus = {
  supported: boolean;
  reason?: string;
};

/**
 * Check if WebGPU is supported in the current browser/environment
 * This should be called before attempting any model load
 */
export function checkWebGPUSupport(): WebGPUStatus {
  if (typeof window === "undefined") {
    return {
      supported: false,
      reason: "WebGPU is only available in browser environments",
    };
  }

  if (!navigator.gpu) {
    return {
      supported: false,
      reason: "このブラウザはWebGPUに対応していません。Chrome/Edge/Safariの最新版をお試しください。",
    };
  }

  return { supported: true };
}

/**
 * Async check for WebGPU adapter availability
 * More thorough check than just navigator.gpu presence
 */
export async function checkWebGPUAdapter(): Promise<WebGPUStatus> {
  const basicCheck = checkWebGPUSupport();
  if (!basicCheck.supported) {
    return basicCheck;
  }

  try {
    const adapter = await navigator.gpu.requestAdapter();
    if (!adapter) {
      return {
        supported: false,
        reason: "WebGPUアダプターが見つかりません。GPUドライバーを更新するか、別のブラウザをお試しください。",
      };
    }
    return { supported: true };
  } catch (error) {
    return {
      supported: false,
      reason: `WebGPUの初期化に失敗しました: ${error instanceof Error ? error.message : "不明なエラー"}`,
    };
  }
}
