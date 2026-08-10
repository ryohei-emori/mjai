import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import TextCorrectionApp from "../page";
import { AuthProvider } from "../auth-provider";

import fetchMock from "jest-fetch-mock";
fetchMock.enableMocks();

// WebLLMモジュールをモック（ESM互換性の問題を回避）
jest.mock("@/lib/webllm", () => ({
  generateSuggestions: jest.fn(),
  checkWebGPUSupport: jest.fn().mockReturnValue({ supported: true }),
  isEngineReady: jest.fn().mockReturnValue(false),
  WebGPUUnsupportedError: class WebGPUUnsupportedError extends Error {
    constructor(message: string) {
      super(message);
      this.name = "WebGPUUnsupportedError";
    }
  },
  ModelLoadError: class ModelLoadError extends Error {
    constructor(message: string) {
      super(message);
      this.name = "ModelLoadError";
    }
  },
  InferenceError: class InferenceError extends Error {
    constructor(message: string) {
      super(message);
      this.name = "InferenceError";
    }
  },
}));

// Supabaseクライアントをモックする。テストごとにセッションの有無を切り替えられるようにする。
const mockGetSession = jest.fn();
const mockOnAuthStateChange = jest.fn().mockReturnValue({
  data: { subscription: { unsubscribe: jest.fn() } },
});
const mockSignOut = jest.fn();

jest.mock("@/lib/supabaseClient", () => ({
  supabase: {
    auth: {
      getSession: (...args: unknown[]) => mockGetSession(...args),
      onAuthStateChange: (...args: unknown[]) => mockOnAuthStateChange(...args),
      signInWithOAuth: jest.fn(),
      signOut: (...args: unknown[]) => mockSignOut(...args),
    },
  },
}));

beforeEach(() => {
  fetchMock.resetMocks();
  mockGetSession.mockReset();
  mockOnAuthStateChange.mockClear();
  mockSignOut.mockClear();
});

test("未認証の場合はログイン画面が表示され、保護されたAPIは呼ばれない", async () => {
  mockGetSession.mockResolvedValue({ data: { session: null } });

  render(
    <AuthProvider>
      <TextCorrectionApp />
    </AuthProvider>
  );

  await waitFor(() => {
    expect(screen.getByText("Googleでログイン")).toBeInTheDocument();
  });

  // ログイン画面ではセッション一覧などの保護APIを呼び出さない
  expect(fetchMock).not.toHaveBeenCalled();
});

test("認証済みの場合はログイン画面を表示せず、通常のワークスペースが表示される", async () => {
  mockGetSession.mockResolvedValue({
    data: {
      session: {
        access_token: "test-access-token",
        user: { email: "owner@example.com" },
      },
    },
  });
  fetchMock.mockResponseOnce(JSON.stringify([]));

  render(
    <AuthProvider>
      <TextCorrectionApp />
    </AuthProvider>
  );

  await waitFor(() => {
    expect(screen.getByText("新しいセッション作成")).toBeInTheDocument();
  });

  expect(screen.queryByText("Googleでログイン")).not.toBeInTheDocument();
});
