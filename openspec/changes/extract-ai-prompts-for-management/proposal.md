## Why

現在、AI校正プロンプト（システムプロンプト、few-shot例、ユーザーテンプレート）は `frontend/src/lib/webllm/prompt.ts` 内にハードコードされている。このため、プロンプトの調整・最適化には TypeScript コードを直接編集する必要があり、非エンジニアがプロンプトを改善することが困難。プロンプトを独立したファイルに抽出し、整理された場所で管理することで、エンジンコードを触らずにプロンプトの最適化・実験が可能になる。

## What Changes

- プロンプト文字列を `frontend/src/lib/webllm/prompts/` ディレクトリに抽出
- システムプロンプト、few-shot 例、テンプレートを個別ファイルとして分離
- `prompt.ts` をこれらのファイルからインポートするようリファクタ
- プロンプトファイルの構造と編集方法を AGENTS.md に文書化
- 既存のプロンプト構築テストを新構造に対応させる

## Capabilities

### New Capabilities
- `prompt-management`: WebLLM プロンプトを独立ファイルとして管理し、エンジンコードを変更せずに編集・最適化可能にする仕組み

### Modified Capabilities
<!-- なし - これは純粋なコード構成の変更であり、外部から見える動作は変わらない -->

## Impact

- **Code**: `frontend/src/lib/webllm/prompt.ts` をリファクタ
- **New files**: `frontend/src/lib/webllm/prompts/` 配下に新規ファイル作成
- **Tests**: `frontend/src/lib/webllm/__tests__/prompt.test.ts` を更新
- **Docs**: `AGENTS.md` にプロンプト管理セクションを追加
- **No backend changes**: AI 生成は WebLLM でクライアント側のみ、バックエンドデプロイ不要
- **No behavior changes**: 既存の校正提案の出力形式・品質に影響なし
