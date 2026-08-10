## Context

現在 `frontend/src/lib/webllm/prompt.ts` には約 50 行のプロンプトテキスト（`SYSTEM_PROMPT`、`FEW_SHOT_EXAMPLES`）がハードコードされている。`buildPrompt` 関数はこれらを結合してユーザー入力と共に完全なプロンプトを構築する。動機は proposal.md - Why を参照。

## Goals / Non-Goals

**Goals:**
- プロンプトテンプレートを `frontend/src/lib/webllm/prompts/` 配下の独立ファイルに抽出
- TypeScript のインポート互換性を維持
- `buildPrompt` / `buildChatMessages` の API シグネチャを変更しない
- 非エンジニアでもプロンプト編集可能な明確なファイル構造

**Non-Goals:**
- プロンプトの動的ロード（実行時にファイルから読み込む仕組み）- ビルド時インポートで十分
- プロンプトのバージョン管理 UI や A/B テスト機能
- プロンプト内容自体の改善・最適化（構造整理のみ）

## Decisions

### Decision 1: ディレクトリ構造

**選択:** `frontend/src/lib/webllm/prompts/` 配下に以下のファイル構成

```
prompts/
├── index.ts          # 再エクスポート（クリーンなインポート用）
├── system.ts         # SYSTEM_PROMPT 定数
├── fewShot.ts        # FEW_SHOT_EXAMPLES 定数
└── templates.ts      # ユーザーテンプレート（問題セクション、追加指示セクションなど）
```

**理由:**
- TypeScript ファイル（`.ts`）を採用：型安全性、IDE 補完、インポートの容易さ
- Markdown (`.md`) は却下：Next.js で raw import するには追加設定が必要、TypeScript との統合が複雑
- 単一ファイルは却下：関心の分離が不十分、編集時に他の部分に触れるリスク

**代替案:**
- `prompts.json` + TypeScript 型定義：JSON はマルチライン文字列が読みにくい
- `*.md` + raw-loader：ビルド設定の複雑化、型安全性の欠如

### Decision 2: エクスポート形式

**選択:** 各ファイルから named export で定数をエクスポート、`index.ts` で再エクスポート

```typescript
// prompts/system.ts
export const SYSTEM_PROMPT = `...`;

// prompts/index.ts
export { SYSTEM_PROMPT } from './system';
export { FEW_SHOT_EXAMPLES } from './fewShot';
export { USER_PROMPT_TEMPLATE, INSTRUCTION_TEMPLATE } from './templates';

// prompt.ts での使用
import { SYSTEM_PROMPT, FEW_SHOT_EXAMPLES, USER_PROMPT_TEMPLATE } from './prompts';
```

**理由:**
- Tree-shaking 対応（未使用エクスポートはバンドルから除外）
- 明示的なインポートで依存関係が明確
- テストでのモック化が容易

### Decision 3: テンプレート文字列の構造化

**選択:** テンプレート内のセクション（`## 問題`、`## 追加指示` など）も定数として `templates.ts` に抽出

```typescript
// templates.ts
export const SECTION_ORIGINAL = '＜中国語または日本語に翻訳する日本語または中国語の文＞';
export const SECTION_TARGET = '＜日本語または中国語の文から中国語または日本語に翻訳を試みた文＞';
export const SECTION_INSTRUCTION = '## 追加指示';
export const SECTION_ANSWER = '## あなたが生成する回答';
```

**理由:**
- セクションヘッダーの一貫性を保証
- パーサーとプロンプト構築の同期が容易（同じ定数を参照）
- 将来の多言語対応に備えた構造

## Risks / Trade-offs

**[Risk]** ファイル分割によりコードジャンプが増える → **Mitigation:** `index.ts` からの一括インポートで最小化、IDE の Go to Definition で解決

**[Risk]** テンプレートリテラル内の改行・空白が意図せず変わる → **Mitigation:** 既存テストで出力を検証、リファクタ後に差分がないことを確認

**[Trade-off]** TypeScript ファイルは非エンジニアにとって「コード」に見える → 文字列定数のみを含むシンプルな構造とコメントで補う。将来的に GUI エディタを検討可能

## Migration Plan

1. `frontend/src/lib/webllm/prompts/` ディレクトリを作成
2. 各プロンプト定数を新ファイルに移動
3. `prompt.ts` を新しいインポートに更新
4. 既存テスト (`prompt.test.ts`) がパスすることを確認
5. AGENTS.md にプロンプト管理セクションを追加

ロールバック: Git revert のみで完了（外部依存なし、データマイグレーションなし）
