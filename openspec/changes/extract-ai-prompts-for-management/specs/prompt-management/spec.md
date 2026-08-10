## Purpose

WebLLM プロンプトテンプレートを独立したファイルとして管理し、エンジンコード (`prompt.ts`) を変更せずにプロンプトの編集・最適化を可能にする仕組みを提供する。

## ADDED Requirements

### Requirement: Prompts stored as separate files
プロンプトテンプレート（システムプロンプト、few-shot 例、ユーザーテンプレート構造）は `frontend/src/lib/webllm/prompts/` ディレクトリ内の独立したファイルとして保存されなければならない（SHALL）。

#### Scenario: System prompt in dedicated file
- **WHEN** 開発者がシステムプロンプトを確認または編集する
- **THEN** `frontend/src/lib/webllm/prompts/` 内の専用ファイルにシステムプロンプト全文が存在する

#### Scenario: Few-shot examples in dedicated file  
- **WHEN** 開発者が few-shot 例を確認または編集する
- **THEN** `frontend/src/lib/webllm/prompts/` 内の専用ファイルに few-shot 例が存在する

### Requirement: Prompt building uses imported templates
`buildPrompt` 関数は prompts ディレクトリからインポートしたテンプレートを使用してプロンプトを構築しなければならない（SHALL）。ハードコードされた文字列リテラルは使用しない。

#### Scenario: buildPrompt constructs from imported templates
- **WHEN** `buildPrompt({ originalText, targetText })` を呼び出す
- **THEN** 返されるプロンプト文字列は prompts ディレクトリからインポートされたシステムプロンプトと few-shot 例を含む

#### Scenario: Template changes reflect in output
- **WHEN** prompts ディレクトリ内のテンプレートファイルを編集してビルドする
- **THEN** `buildPrompt` の出力は更新されたテンプレート内容を反映する

### Requirement: No engine code changes for prompt edits
プロンプトテキストの変更には `prompt.ts` のエンジンロジックを変更する必要がない（SHALL NOT）。テンプレートファイルのみを編集すればよい。

#### Scenario: Edit prompt without touching engine
- **WHEN** 開発者がシステムプロンプトの文言を調整したい
- **THEN** prompts ディレクトリ内のテンプレートファイルのみを編集し、`prompt.ts` は変更不要

### Requirement: TypeScript type safety preserved
プロンプトテンプレートは TypeScript でインポート可能であり、既存の `buildPrompt` 関数の型シグネチャを変更してはならない（SHALL NOT）。

#### Scenario: Type-safe imports
- **WHEN** `prompt.ts` がテンプレートをインポートする
- **THEN** TypeScript コンパイルエラーなしでインポートが成功する

#### Scenario: API compatibility maintained
- **WHEN** `buildPrompt(input: PromptInput)` を呼び出す
- **THEN** 関数シグネチャは変更前と同一であり、戻り値は `string` 型である
