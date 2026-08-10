import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import TextCorrectionApp from "../page";
import { AuthProvider } from "../auth-provider";
import { Toaster } from "@/components/ui/toaster";

// fetch-mockのセットアップ
import fetchMock from "jest-fetch-mock";
fetchMock.enableMocks();

// Supabaseクライアントをモックし、ログイン済み状態でテストを実行する
jest.mock("@/lib/supabaseClient", () => {
  const fakeSession = {
    access_token: "test-access-token",
    user: { email: "owner@example.com" },
  };
  return {
    supabase: {
      auth: {
        getSession: jest.fn().mockResolvedValue({ data: { session: fakeSession } }),
        onAuthStateChange: jest.fn().mockReturnValue({
          data: { subscription: { unsubscribe: jest.fn() } },
        }),
        signInWithOAuth: jest.fn(),
        signOut: jest.fn(),
      },
    },
  };
});

// WebLLMをモック - WebGPU非対応をシミュレート
jest.mock("@/lib/webllm", () => ({
  generateSuggestions: jest.fn(),
  checkWebGPUSupport: jest.fn().mockReturnValue({ supported: false, reason: "WebGPU非対応ブラウザ" }),
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

// navigator.clipboard.writeTextをモック
beforeAll(() => {
  Object.assign(navigator, {
    clipboard: {
      writeText: jest.fn().mockResolvedValue(undefined),
    },
  });
});

beforeEach(() => {
  fetchMock.resetMocks();
  process.env.NEXT_PUBLIC_FRONTEND_MODE = "real";
});

test("WebGPU非対応時にボタンが無効化され、メッセージが表示される", async () => {
  // セッション一覧取得とセッション作成のモック
  fetchMock.mockResponseOnce(JSON.stringify([]));
  fetchMock.mockResponseOnce(
    JSON.stringify({
      sessionId: "session-1",
      name: "セッション 1",
      createdAt: new Date().toISOString(),
      correctionCount: 0,
    })
  );

  render(
    <AuthProvider>
      <Toaster />
      <TextCorrectionApp />
    </AuthProvider>
  );

  // ログイン済み状態に遷移するまで待機
  await waitFor(() => {
    expect(screen.getByText("新しいセッション作成")).toBeInTheDocument();
  });

  // セッション作成
  fireEvent.click(screen.getByText("新しいセッション作成"));

  // セッション作成が完了し、テキスト入力欄が表示されるまで待機
  await waitFor(() => {
    expect(screen.getByPlaceholderText("原文テキストをここに貼り付けてください...")).toBeInTheDocument();
  });

  // テキスト入力
  fireEvent.change(screen.getByPlaceholderText("原文テキストをここに貼り付けてください..."), {
    target: { value: "今日は天気がいいです" },
  });
  fireEvent.change(screen.getByPlaceholderText("添削対象テキストをここに貼り付けてください..."), {
    target: { value: "今日は天気が良いです" },
  });

  // WebGPU非対応メッセージが表示されることを確認
  await waitFor(() => {
    expect(screen.getByText("AI提案機能を利用できません")).toBeInTheDocument();
  });

  // AI提案生成ボタンが無効化されていることを確認
  const generateButton = screen.getByRole("button", { name: /AI提案を生成/ });
  expect(generateButton).toBeDisabled();
});

// 必要な依存が未インストールの場合:
// npm install --save-dev @testing-library/react @testing-library/jest-dom jest-fetch-mock @types/jest