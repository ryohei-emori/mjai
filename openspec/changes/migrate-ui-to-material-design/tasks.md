## 1. Token Foundation

- [x] 1.1 Add MD3 semantic color tokens to `frontend/src/app/globals.css` (surface, surface-container-*, on-surface, outline-variant, etc.)
- [x] 1.2 Add session status colors to `frontend/tailwind.config.js` (session-active, session-complete, session-empty)
- [x] 1.3 Add named spacing tokens to `frontend/tailwind.config.js` (container-margin, card-gap, gutter, section-padding)
- [x] 1.4 Add typography scale to `frontend/tailwind.config.js` (headline-lg, headline-md, body-base, body-sm, metadata, label-caps)
- [x] 1.5 Update border radius scale in `frontend/tailwind.config.js` (DEFAULT 0.25rem, lg 0.5rem, xl 0.75rem, full)

## 2. Font & Icon Setup

- [x] 2.1 Add Inter font via `next/font/google` in `frontend/src/app/layout.tsx`
- [x] 2.2 Add Material Symbols Outlined font link to `frontend/src/app/layout.tsx`
- [x] 2.3 Create utility CSS class for Material Symbols icons (`.material-symbols-outlined` styling)
- [x] 2.4 Verify fonts load correctly (no FOUT/FOIT issues)

## 3. TopAppBar Implementation

- [x] 3.1 Create TopAppBar component with MJAI logo/title on left
- [x] 3.2 Add navigation tabs (Sessions, Dashboard, Archive) to TopAppBar
- [x] 3.3 Add New Session button to TopAppBar
- [x] 3.4 Add notification bell icon button to TopAppBar (with shake animation trigger on job completion)
- [x] 3.5 Add settings icon button to TopAppBar (UI-only, no functional settings screen — display as inactive/disabled or with "Coming Soon" tooltip)
- [x] 3.7 Add logout button/area to TopAppBar right side (next to avatar)
- [x] 3.8 Add activeNav state management for tab switching
- [x] 3.9 Style TopAppBar using new MD3 tokens
- [x] 3.10 Add CSS keyframe animation for notification bell shake (`@keyframes bell-shake` in globals.css)
- [x] 3.11 Wire bell shake animation trigger on job completion state change

## 4. Left Pane (Session List)

- [x] 4.1 Restructure session list as dedicated left pane (not collapsible sidebar)
- [x] 4.2 Add search input above session list
- [x] 4.3 Implement session search/filter functionality
- [x] 4.4 Restyle session cards with status pills (saved count / Draft)
- [x] 4.5 Apply session-active/complete/empty colors to status pills
- [x] 4.6 Add visual distinction for active session card
- [x] 4.7 Ensure mobile responsive behavior (sheet on small screens)

## 5. Center Pane (Editor)

- [x] 5.1 Restructure source/target textareas as stacked cards in center pane
- [x] 5.2 Style source text card with MD3 tokens
- [x] 5.3 Style target text card with MD3 tokens
- [x] 5.4 Position "AI提案を生成" button at bottom-right of target card
- [x] 5.5 Ensure offline mode toggle remains visible near Generate button
- [x] 5.6 Apply new typography scale to card headers and descriptions

## 6. Right Pane (Job Queue + Suggestions)

- [x] 6.1 Restructure job queue and suggestions as right pane
- [x] 6.2 Add "N Active" badge to job queue panel header
- [x] 6.3 Style job items with progress indicators
- [x] 6.4 Ensure completed job click triggers HITL flow (unchanged behavior)
- [x] 6.5 Restyle AI suggestion cards with option labels (Option A, Option B style)
- [x] 6.6 Add hover-reveal action icons (copy, confirm) to suggestion cards
- [x] 6.7 Ensure suggestion card click/confirm toggles selection (unchanged behavior)
- [x] 6.8 Style overall comment section with new tokens

## 7. Dashboard/Archive Stubs

- [x] 7.1 Create ComingSoonPlaceholder component for Dashboard/Archive
- [x] 7.2 Implement conditional rendering based on activeNav state
- [x] 7.3 Style placeholder with appropriate MD3 tokens

## 8. Icon Migration

- [x] 8.1 Replace TopAppBar icons with Material Symbols (menu, add, logout, notifications, settings)
- [x] 8.2 Replace session list icons with Material Symbols (description, calendar_today, delete)
- [x] 8.3 Replace editor area icons with Material Symbols (smart_toy, content_copy)
- [x] 8.4 Replace job queue icons with Material Symbols (progress_activity, check_circle)
- [x] 8.5 Verify all icons render correctly with appropriate sizes

## 9. Toast Notifications

- [x] 9.1 Verify toast notifications continue to appear in top-right
- [x] 9.2 Ensure toasts overlay TopAppBar correctly if needed
- [x] 9.3 Style toast components with new tokens (optional refinement)

## 10. Documentation Update

- [x] 10.0 Archive current `docs/UI-DESIGN.md` to `docs/archive/UI-DESIGN-initial.md` (create `docs/archive/` dir if needed)
- [x] 10.1 Update `docs/UI-DESIGN.md` Color Palette section with MD3 tokens
- [x] 10.2 Update `docs/UI-DESIGN.md` Typography section with new scale and Inter font
- [x] 10.3 Update `docs/UI-DESIGN.md` Spacing & Radii section with new tokens
- [x] 10.4 Update `docs/UI-DESIGN.md` Component Library section to mention Material Symbols
- [x] 10.5 Add TopAppBar and 3-pane layout patterns to Application-Specific Patterns section
- [x] 10.6 Add session card and suggestion card component patterns

## 11. Regression & Compatibility Check

- [x] 11.1 Verify 実行履歴 (execution history) display and restore functionality
- [x] 11.2 Verify HITL 確認 flow works correctly (job queue → confirm → save)
- [x] 11.3 Verify ジョブキュー並列処理 (job queue parallel processing) for API mode
- [x] 11.4 Verify オフラインモード (offline mode) toggle and WebLLM fallback
- [x] 11.5 Verify top-right toast notifications for 処理開始/完了/エラー
- [x] 11.6 Verify logout button functionality in new TopAppBar position
- [x] 11.7 Verify favicon remains intact
- [x] 11.8 Test responsive behavior at lg breakpoint and below

## 12. Finalization

- [x] 12.1 Run linter and fix any errors
- [x] 12.2 Run frontend tests (if applicable)
- [x] 12.3 Manual smoke test of all major flows
- [ ] 12.4 Commit changes with descriptive message
- [ ] 12.5 Push to branch and create PR (if requested)
