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

// Cold-path WebLLM modules (page.tsx no longer imports the barrel / engine)
jest.mock("@/lib/webllm/webgpu", () => ({
  checkWebGPUSupport: jest.fn().mockReturnValue({
    supported: false,
    reason: "WebGPU非対応ブラウザ",
  }),
}));
jest.mock("@/lib/webllm/engineReady", () => ({
  isEngineReady: jest.fn().mockReturnValue(false),
}));
jest.mock("@/lib/webllm/config", () => ({
  WEBLLM_MODEL_DISPLAY_NAME: "test-model",
  WEBLLM_MODEL_ID: "test-model-id",
}));
jest.mock("@/lib/webllm/diagnostics", () => ({
  formatElapsedTime: (ms: number) => `${ms}ms`,
  formatDownloadProgress: () => "0%",
  PHASE_LABELS: {},
  getDiagnosticsTracker: () => ({
    getState: () => ({}),
  }),
}));
jest.mock("@/lib/webllm/engine", () => ({
  generateSuggestions: jest.fn(),
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
    expect(screen.getByText("Create a new session")).toBeInTheDocument();
  });

  // セッション作成
  fireEvent.click(screen.getByText("Create a new session"));

  // セッション作成が完了し、テキスト入力欄が表示されるまで待機
  await waitFor(() => {
    expect(screen.getByPlaceholderText("Paste the source text here...")).toBeInTheDocument();
  });

  // テキスト入力
  fireEvent.change(screen.getByPlaceholderText("Paste the source text here..."), {
    target: { value: "今日は天気がいいです" },
  });
  fireEvent.change(screen.getByPlaceholderText("Paste the text you want corrected here..."), {
    target: { value: "今日は天気が良いです" },
  });

  // WebGPU非対応メッセージが表示されることを確認
  await waitFor(() => {
    expect(screen.getByText("AI suggestions cannot be generated.")).toBeInTheDocument();
  });

  // AI提案生成ボタンはAPI経由で利用可能なため、有効のままであることを確認
  // （旧アーキテクチャではWebGPU必須だったが、新アーキテクチャではクラウドAPI優先）
  const generateButton = screen.getByRole("button", { name: /Generate AI Suggestions/i });
  expect(generateButton).not.toBeDisabled();

  // オフラインモードのチェックボックスは無効化されていることを確認
  const offlineModeCheckbox = screen.getByLabelText("Offline Mode (WebLLM)");
  expect(offlineModeCheckbox).toBeDisabled();
});

// 必要な依存が未インストールの場合:
// npm install --save-dev @testing-library/react @testing-library/jest-dom jest-fetch-mock @types/jest