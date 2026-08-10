## 1. 推論パラメータ最適化

- [x] 1.1 `engine.ts`の`max_tokens`を2048から512に変更
- [x] 1.2 `engine.ts`の`temperature`を0.7から0.2に変更

## 2. プロンプト短縮

- [x] 2.1 `prompts/system.ts`を短縮（JSON-only出力を明示、冗長な説明削除）
- [x] 2.2 `prompts/fewShot.ts`の例文を最小限の構造例に置き換え

## 3. テスト更新

- [x] 3.1 `__tests__/prompt.test.ts`を更新（新プロンプト構造に対応）
- [x] 3.2 `__tests__/engine.test.ts`を更新（新パラメータに対応 - 変更不要、モック使用）
- [x] 3.3 `__tests__/prompts.test.ts`を更新（短縮されたプロンプトに対応）

## 4. ドキュメント更新

- [x] 4.1 `AGENTS.md`のAI Suggestion Generationセクションを更新（新パラメータ・プロンプト方針を記載）

## 5. 追加修正（調査で発見）

- [x] 5.1 `config.ts`のContext window誤記を修正（4096→8192トークン）
