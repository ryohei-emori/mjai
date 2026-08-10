/**
 * @jest-environment jsdom
 */

import { checkWebGPUSupport } from "../webgpu";

describe("checkWebGPUSupport", () => {
  const originalNavigator = global.navigator;

  afterEach(() => {
    // Restore navigator after each test
    Object.defineProperty(global, "navigator", {
      value: originalNavigator,
      writable: true,
    });
  });

  it("returns unsupported when navigator.gpu is not available", () => {
    // Mock navigator without gpu
    Object.defineProperty(global, "navigator", {
      value: { ...originalNavigator, gpu: undefined },
      writable: true,
    });

    const result = checkWebGPUSupport();

    expect(result.supported).toBe(false);
    expect(result.reason).toContain("WebGPU");
  });

  it("returns supported when navigator.gpu is available", () => {
    // Mock navigator with gpu
    Object.defineProperty(global, "navigator", {
      value: { ...originalNavigator, gpu: {} },
      writable: true,
    });

    const result = checkWebGPUSupport();

    expect(result.supported).toBe(true);
    expect(result.reason).toBeUndefined();
  });
});
