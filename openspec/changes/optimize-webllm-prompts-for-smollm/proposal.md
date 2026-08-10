## Why

WebLLM推論が80秒以上かかりタイムアウトする。原因は`max_tokens: 2048`と`temperature: 0.7`が過剰で、ストップシーケンスがなく、SmolLM2-1.7Bが出力をいつ止めるべきか判断できない。プロンプトも冗長でsmall modelには不適切。

## What Changes

- **推論パラメータの最適化**: `max_tokens`を512以下に、`temperature`を0.2-0.3に下げ、ストップシーケンスを追加
- **プロンプトの簡潔化**: システムプロンプトを短く明確に、JSON-only出力を厳格に指示
- **few-shot例の短縮**: 長い翻訳例文を最小限の構造例に置き換え
- **パーサーのフェイルファスト**: パース失敗時に明確なエラーで即終了（無限リトライなし - 既に実装済み、確認のみ）

## Capabilities

### New Capabilities

- `ai-suggestion-generation`: WebLLMによるAI修正提案生成の動作仕様（SmolLM2最適化含む）

### Modified Capabilities

（なし - 既存specなし、新規capability）

## Impact

- `frontend/src/lib/webllm/engine.ts`: 推論パラメータ変更
- `frontend/src/lib/webllm/prompts/*.ts`: プロンプト全面改訂
- `frontend/src/lib/webllm/__tests__/*.ts`: 関連テスト更新
- `AGENTS.md`: AI提案生成のプロンプト管理セクション更新
