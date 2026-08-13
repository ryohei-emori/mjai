## Why

「確定してコピー・保存」は現状、履歴/提案のネットワーク保存が終わるまでクリップボードコピーも UI 確定も待たされるため、待ち時間が長く「壊れている」ように感じる。加えて待機中のボタンに `progress_activity` アイコンはあるが `animate-spin` が無く、ぐるぐる回転しないためフリーズに見える。

## What Changes

- `saveCorrections()` を再構成し、**クリップボードコピーとローカル UI 確定を先に完了**させ、履歴/提案の API 保存はバックグラウンドで続行する。
- 保存成功/失敗はトーストで通知する（コピー成功と保存結果を分離）。
- 二重送信防止（`isSaving`）は維持する。
- ボタンが待機/ローディング状態の間は、既存の MD3 パターンどおり `progress_activity` + `animate-spin` を必ず表示する。
- `docs/UI-DESIGN.md` に確認ボタンのローディングパターンを短く追記する。

## Capabilities

### New Capabilities

（なし）

### Modified Capabilities

- `correction-workspace-ui`: 「確定してコピー・保存」の順序（コピー/ローカル確定を先行、サーバー保存を非同期）と、待機中のスピナー必須表示を要件化する。

## Impact

- **Frontend**: `frontend/src/app/page.tsx`（`saveCorrections`、確定ボタン JSX）
- **Docs**: `docs/UI-DESIGN.md`（ボタンローディングパターン）
- **Backend / API**: 変更なし（既存 `historyAPI` / `proposalAPI` をそのまま非同期呼び出し）
- **Out of scope**: LLM プロンプト変更（`raise-suggestion-quality-to-gemini-bar` / `harden-semantic-suggestion-reasons`）、`add-optional-exemplar-translation-input`、`frontend/out/*`
