import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import TextCorrectionApp from "../page";

// fetch-mockのセットアップ
import fetchMock from "jest-fetch-mock";
fetchMock.enableMocks();

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

test("API呼び出し失敗時にエラートーストが表示される", async () => {
  fetchMock.mockRejectOnce(new Error("API error"));

  render(<TextCorrectionApp />);

  // セッション作成
  fireEvent.click(screen.getByText("新しいセッション作成"));

  // テキスト入力
  fireEvent.change(screen.getByPlaceholderText("原文テキストをここに貼り付けてください..."), {
    target: { value: "今日は天気がいいです" },
  });
  fireEvent.change(screen.getByPlaceholderText("添削対象テキストをここに貼り付けてください..."), {
    target: { value: "今日は天気が良いです" },
  });

  // AI提案生成ボタンをクリック
  fireEvent.click(screen.getByText("AI提案を生成"));

  // エラートーストが表示されることを確認
  await waitFor(() => {
    expect(
      screen.getByText((content, element) =>
        content.includes("AI提案の取得に失敗しました")
      )
    ).toBeInTheDocument();
  });
});

// 必要な依存が未インストールの場合:
// npm install --save-dev @testing-library/react @testing-library/jest-dom jest-fetch-mock @types/jest 