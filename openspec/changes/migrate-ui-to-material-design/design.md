## Context

See `proposal.md` for motivation. 現在のMJAIフロントエンドはshadcn/ui（Radix + Tailwind）をベースに、HSL CSS変数でカラートークンを定義している。`frontend/tailwind.config.js`でカスタムカラーを拡張し、`frontend/src/app/globals.css`でCSS変数を定義。アイコンはLucide Reactを使用。

既存の機能要件（実行履歴、HITL確認フロー、ジョブキュー、top-rightトースト、オフラインモード、デュアルAIプロバイダー）は`correction-workspace-ui`スペックおよび関連OpenSpec changesで定義済み。

## Goals / Non-Goals

**Goals:**
- Material Design 3スタイルのセマンティックトークン体系を導入
- TopAppBar + 3ペインレイアウトへの構造移行
- 既存の全機能要件を維持しながらビジュアル刷新
- docs/UI-DESIGN.md を新トークン体系に更新

**Non-Goals:**
- Dashboard/Archive の完全実装（UIスタブのみ）
- ダークモードの新規実装（既存のclass-basedダークモード維持、新トークンのダーク値は将来対応）
- バックエンドAPI変更
- Lucide Reactの完全削除（段階的移行、一部アイコンは併存可能）

## Decisions

### Decision 1: Token Integration Strategy — Additive with Gradual Replacement

**選択:** 新MD3トークンを既存shadcn/uiトークンと併存させ、段階的に置換する。

**理由:**
- 既存コンポーネント（shadcn/ui Button, Card, Input等）は現行トークンに依存
- 一括置換はリグレッションリスクが高い
- 新コンポーネント/領域から新トークンを適用し、既存を徐々に移行

**代替案:**
- 完全置換: リスク高、テスト負荷大
- Fork shadcn/ui: メンテナンス負荷大

**実装:**
```javascript
// tailwind.config.js に追加
colors: {
  // 既存トークン維持
  background: 'hsl(var(--background))',
  // 新MD3トークン追加
  surface: {
    DEFAULT: 'hsl(var(--surface))',
    container: 'hsl(var(--surface-container))',
    'container-low': 'hsl(var(--surface-container-low))',
    'container-lowest': 'hsl(var(--surface-container-lowest))',
  },
  'on-surface': 'hsl(var(--on-surface))',
  'session-active': '#2563EB',
  'session-complete': '#16A34A',
  'session-empty': '#64748B',
}
```

### Decision 2: Typography Scale Implementation

**選択:** Tailwind の `fontSize` 拡張で名前付きスタイルを定義。

```javascript
// tailwind.config.js
fontSize: {
  'headline-lg': ['1.5rem', { lineHeight: '2rem', letterSpacing: '0' }],
  'headline-md': ['1.25rem', { lineHeight: '1.75rem', letterSpacing: '0.0125em' }],
  'body-base': ['1rem', { lineHeight: '1.5rem', letterSpacing: '0.03125em' }],
  'body-sm': ['0.875rem', { lineHeight: '1.25rem', letterSpacing: '0.025em' }],
  'metadata': ['0.75rem', { lineHeight: '1rem', letterSpacing: '0.03125em' }],
  'label-caps': ['0.625rem', { lineHeight: '1rem', letterSpacing: '0.1em', fontWeight: '500' }],
}
```

**Inter フォント読み込み:**
- Next.js の `next/font/google` で Inter を読み込み（既存パターンに合わせる）
- `layout.tsx` で font className を適用

### Decision 3: Icon System Migration — Google Fonts CDN + Incremental Replacement

**選択:** Material Symbols Outlined を Google Fonts CDN経由で読み込み、新UIコンポーネントから適用。Lucide React は既存コンポーネントで併存可。

**実装:**
```html
<!-- layout.tsx の head または next/font -->
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" rel="stylesheet" />
```

使用例:
```jsx
<span className="material-symbols-outlined">home</span>
```

**マッピングテーブル（主要アイコン）:**
| Lucide React | Material Symbols |
|--------------|------------------|
| `Menu` | `menu` |
| `Plus` | `add` |
| `Trash2` | `delete` |
| `FileText` | `description` |
| `Bot` | `smart_toy` |
| `CheckCircle` | `check_circle` |
| `Loader2` | `progress_activity` |
| `Copy` | `content_copy` |
| `LogOut` | `logout` |
| `Calendar` | `calendar_today` |
| `MessageSquare` | `chat` |

### Decision 4: Layout Structure — Component-Level Refactor

**選択:** `page.tsx` 内の既存コンポーネント構造を維持しつつ、レイアウトラッパーを追加。

**現在の構造:**
```
<div className="h-screen flex flex-col">
  <Sheet (mobile sidebar)>
  <div className="flex flex-1">
    <Sidebar (desktop, collapsible)>
    <Main Content (scrollable)>
      <Logout button (fixed top-right)>
      <Session Header>
      <Grid (2 columns)>
        <Left: Text Areas>
        <Right: Suggestions + History>
```

**新構造:**
```
<div className="h-screen flex flex-col">
  <TopAppBar (fixed)>
    <Logo> <NavTabs> <NewSessionBtn> <Icons> <Avatar>
  <div className="flex flex-1 pt-topappbar">
    <LeftPane (session list + search)>
    <CenterPane (source + target cards)>
    <RightPane (job queue + suggestions)>
```

**既存ロジック/ステートは変更なし:** `sessions`, `currentSessionId`, `jobQueue`, `suggestions` 等のステート管理はそのまま維持。

### Decision 5: Offline Mode Toggle Placement

**選択:** Generate ボタンの直上、ターゲットテキストカード内に配置（現行位置を維持）。

**理由:**
- 現行UXを維持（ユーザーが慣れている位置）
- Generate操作と論理的に近い位置
- モックアップには明示されていないが、この配置が最も自然

**代替案:**
- Settings アイコンのドロップダウン内: 発見性が低下
- TopAppBar内: 頻繁に使う機能としては遠い

### Decision 6: Dashboard/Archive/Settings Stub Implementation

**選択:** Dashboard/Archive は NavTab として表示し、クリック時は「Coming Soon」コンテンツを表示。Settings アイコンもUIとして表示するが、クリック時は何も起こらない（将来の設定画面用のプレースホルダー）。ルーティングなし（同一ページ内で条件分岐）。

```jsx
const [activeNav, setActiveNav] = useState<'sessions' | 'dashboard' | 'archive'>('sessions')

{activeNav === 'sessions' && <WorkspaceContent />}
{activeNav === 'dashboard' && <ComingSoonPlaceholder title="Dashboard" />}
{activeNav === 'archive' && <ComingSoonPlaceholder title="Archive" />}

// Settings icon: 表示のみ、onClick は現時点では no-op または tooltip "Coming Soon"
<span className="material-symbols-outlined cursor-default opacity-50" title="Coming Soon">settings</span>
```

**スコープ外:** Settings アイコンクリック時の設定画面/モーダルは今回のスコープ外。

### Decision 7: docs/UI-DESIGN.md Rewrite Plan

**事前アーカイブ:** 書き換え前に現行の `docs/UI-DESIGN.md` を `docs/archive/UI-DESIGN-initial.md` にコピーして保存。`docs/archive/` ディレクトリが存在しない場合は作成。

**更新内容:**
1. Color Palette セクション: MD3トークン表を追加（既存HSLトークンと併記）
2. Typography セクション: 新typography scaleを追加、Interフォント記載
3. Spacing & Radii セクション: 新named spacingを追加
4. Component Library セクション: Material Symbols Outlinedを追加
5. Application-Specific Patterns セクション: TopAppBar、3-pane layout、session card パターンを追加

### Decision 8: Notification Bell Shake Animation

**選択:** ジョブ完了時にTopAppBarの通知ベルアイコンに短いシェイク/ウィグルアニメーションを適用。

**実装:**
```css
/* globals.css に追加 */
@keyframes bell-shake {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-15deg); }
  50% { transform: rotate(15deg); }
  75% { transform: rotate(-10deg); }
}

.bell-shake {
  animation: bell-shake 0.5s ease-in-out;
}
```

**トリガー:** ジョブ完了時（`job.status === 'completed'` への遷移時）またはトースト表示時に、ベルアイコン要素に `bell-shake` クラスを一時的に付与（300-500ms後に除去）。React state または `useEffect` で制御。

### Decision 9: Google Account Avatar in TopAppBar

**選択:** TopAppBar右端のユーザーアバターに、Supabase/Google OAuthセッションから取得したGoogleプロフィール画像を表示。

**実装:**
現在の `useAuth()` フックは `user: session?.user ?? null` を公開済み。Googleプロフィール画像は `user.user_metadata.avatar_url` または `user.user_metadata.picture` で取得可能（Supabase Google OAuth の標準メタデータ）。

```jsx
const { user } = useAuth()
const avatarUrl = user?.user_metadata?.avatar_url || user?.user_metadata?.picture

// TopAppBar内
{avatarUrl ? (
  <img src={avatarUrl} alt="User avatar" className="w-8 h-8 rounded-full" />
) : (
  <span className="material-symbols-outlined">account_circle</span>
)}
```

**現状:** 現行の `page.tsx` ではアバター画像は表示されていない（LogOutボタンのみ）。新TopAppBarで新規実装が必要。

## Risks / Trade-offs

**[Risk] 既存コンポーネントとの視覚的不整合** → 段階的移行により、一時的に新旧スタイルが混在。Mitigation: 高頻度使用エリアから優先移行、regression checklistで確認。

**[Risk] Material Symbols フォント読み込み遅延** → 初回訪問時にアイコンが一瞬表示されない可能性。Mitigation: `font-display: swap` または preload hint を使用。

**[Risk] モバイルビューでの3ペインレイアウト破綻** → 小画面では3ペイン不可。Mitigation: `lg` ブレークポイント以下では左ペインをsheet化、右ペインを縦積み。

**[Risk] docs/UI-DESIGN.md の不整合** → 実装と文書が乖離するリスク。Mitigation: 実装完了後に文書更新をタスク化、レビュー時に整合性確認。

## Migration Plan

1. **Phase 1: Token Foundation** — tailwind.config.js / globals.css にMD3トークン追加
2. **Phase 2: Font & Icon Setup** — Inter + Material Symbols 読み込み追加
3. **Phase 3: TopAppBar** — 新ナビゲーション構造を実装
4. **Phase 4: Left Pane (Session List)** — 検索＋セッションカード新デザイン
5. **Phase 5: Center Pane (Editor)** — source/target カード新デザイン
6. **Phase 6: Right Pane (Job Queue + Suggestions)** — ジョブキュー＋AI提案カード新デザイン
7. **Phase 7: Dashboard/Archive Stub** — NavTab + プレースホルダー
8. **Phase 8: Documentation** — docs/UI-DESIGN.md 更新
9. **Phase 9: Regression Check** — 既存OpenSpec changes要件との整合性確認

**Rollback:** Git revert で元の `page.tsx` / `tailwind.config.js` / `globals.css` に戻す。トークン追加はadditive なので、新トークン削除のみで既存機能に影響なし。

## Open Questions

- [ ] Interフォントのウェイト: 400/500/600/700 全て必要か、最小限（400/500/700）で良いか
- [ ] Material Symbols のアイコンサイズ統一ルール: 20px/24px/40px の使い分け基準

---

## Design Iteration 2: Brutalist Refinement (2026-08-11)

### Context

初期実装完了後のユーザーフィードバックに基づくビジュアル調整。元のHTMLモックアップのブルータリズム的高可読性スタイルへの再整合。

### Feedback Items Addressed

1. **右ペーン幅不足 + リサイズ機能**
2. **ブルータリズム的可読性への視覚調整**（glassmorphic/soft effect の削減）
3. **セクションヘッダーの英語優先バイリンガル化**（"SOURCE TEXT (原文)"、"TARGET TEXT (翻訳/編集)"）
4. **生成ボタンのsparkle アイコン + 英語テキスト化**（"Generate AI Suggestions"）
5. **MJAIワードマーク横のロゴマーク削除**

### Decision 10: Right Pane Resizable Implementation

**選択:** カスタムReact実装（pointer event + flex-basis/width state）による軽量リサイズ機能。外部依存なし。

**理由:**
- `package.json` に既存のリサイズライブラリなし
- シングルユーザー内部ツールなので、軽量なカスタム実装が適切
- `react-resizable-panels` 等の追加は過剰（1箇所のみの使用）

**デフォルト幅:** `w-96` (384px) → `w-[28rem]` (448px) へ拡大

**実装:**
- 中央ペーンと右ペーン間にドラッグハンドル（4px幅の縦線、hover で視覚フィードバック）
- React state で右ペーン幅を管理
- `onPointerDown` → `onPointerMove` → `onPointerUp` でドラッグ処理
- オプション: `localStorage` に幅を永続化（nice-to-have）

### Decision 11: Brutalist Visual Treatment

**選択:** 既存DESIGN.mdトークン値を維持しつつ、適用スタイルをシャープ/高コントラストに調整。

**変更点:**
- ソフトシャドウ（`shadow-*` with high blur）を削減または除去
- カードボーダーを明確な1px `border-outline-variant` に統一
- 背景のグラデーション/透明度を削減し、フラットな白/グレー基調に
- テキストコントラスト確保（`text-on-surface` #1c1b1b を黒に近い状態で維持）

### Decision 12: Bilingual Section Headers

**選択:** モックアップに合わせ、英語を主、日本語を括弧内に配置。

**フォーマット:**
- Source Text Card Header: `SOURCE TEXT (原文)`
- Target Text Card Header: `TARGET TEXT (翻訳/編集)`

**スタイル:** `text-label-caps` 相当（uppercase, letter-spacing, muted color）

### Decision 13: Generate Button Styling

**選択:** `auto_awesome`（sparkle/キラキラ）アイコン + 英語テキスト "Generate AI Suggestions"。

**変更:**
- `smart_toy` → `auto_awesome`
- "AI提案を生成" → "Generate AI Suggestions"
- ボタンスタイルは既存の `bg-md3-primary text-on-primary` を維持

### Decision 14: MJAI Wordmark Simplification

**選択:** TopAppBar左側のMJAIワードマークから `edit_note` アイコンを削除し、テキストのみに。

**変更:**
- Before: `<span className="material-symbols-outlined">edit_note</span> MJAI`
- After: `MJAI` (テキストのみ)

**理由:** モックアップに合わせたミニマルブランディング。
