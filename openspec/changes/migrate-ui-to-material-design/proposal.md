## Why

MJAIの現在のUI（shadcn/uiベースのモノクロ調デザイン）を、提供されたHTMLモックアップに基づくMaterial Design 3インスパイアードなビジュアルシステムへ移行する。このモックアップは、より整理されたトップアプリバー、明確なナビゲーション構造（Sessions/Dashboard/Archive）、洗練されたカード中心のレイアウト、そしてセマンティックカラートークン体系を提示している。この移行により、ユーザー体験の一貫性向上と将来機能（Dashboard/Archive）への拡張性を確保する。

## What Changes

- **トークンシステム**: Material Design 3スタイルのセマンティックカラートークン（primary/on-primary/surface/surface-container-*/outline-variant/error/tertiary等）を導入し、現行の shadcn/ui HSL変数と置換または併存
- **タイポグラフィスケール**: Inter フォント + 名前付きテキストスタイル（headline-lg/headline-md/body-base/body-sm/metadata/label-caps）を追加
- **スペーシングスケール**: container-margin (1.5rem), card-gap (1.25rem), gutter (1rem), section-padding (2rem) の名前付きスペーシング
- **ボーダーラディウス**: DEFAULT 0.25rem, lg 0.5rem, xl 0.75rem, full (pill) の4段階
- **アイコンシステム**: Lucide React から Material Symbols Outlined へ移行（Google Fonts linkを追加）
- **レイアウト構造**: TopAppBar（MJAIロゴ + Sessions/Dashboard/Archive タブ + New Session ボタン + notifications/settings アイコン + avatar）→ 3ペインレイアウト（左: セッションリスト＋検索、中央: source/target テキストエディター、右: ジョブキュー + AI提案パネル）
- **セッションカード**: ステータスピル（"N Saved"/"Draft" 相当を「完了件数」「未確認」等にマッピング）付きの洗練されたカードデザイン
- **AI提案カード**: ホバーでcopy/確認アクションアイコンを表示するインタラクティブデザイン
- **Dashboard/Archive/Settings**: TopAppBarにナビタブ/アイコンとして配置（非機能スタブ or "Coming Soon" 表示、Settingsアイコンも今回はUIのみで設定画面なし）
- **⚠️ オフラインモード保持**: モックアップに明示されていないが、現行のWebLLM「オフラインモード」トグルは維持必須 — 新レイアウト内での明確な配置を決定

## Capabilities

### New Capabilities
- `design-tokens`: Material Design 3スタイルのカラー、タイポグラフィ、スペーシング、ラディウスのトークン体系

### Modified Capabilities
- `correction-workspace-ui`: レイアウト構造をTopAppBar + 3ペインへ変更（セッションリスト左ペイン、エディター中央、ジョブキュー＋AI提案右ペイン）、セッションカードにステータスピル追加、AI提案カードにホバーアクション追加、Dashboard/Archiveナビ追加（スタブ）、オフラインモードトグル配置決定

## Impact

- **Frontend code** (`frontend/src/app/page.tsx`, `frontend/tailwind.config.js`, `frontend/src/app/globals.css`): 大規模なUI再構築、トークン追加/置換
- **docs/UI-DESIGN.md**: 新トークン体系・コンポーネントパターンを反映するため全面書き換え
- **Backend API**: 変更なし（純粋にフロントエンドのビジュアル/構造移行）
- **Dependencies**: Material Symbols Outlined フォント（Google Fonts CDN）を追加
- **既存機能の保持必須**: 実行履歴、HITL確認フロー、ジョブキュー並列処理、top-right トースト通知、オフラインモードトグル、Groq/CF + WebLLM デュアルプロバイダー、ログアウト位置、favicon
