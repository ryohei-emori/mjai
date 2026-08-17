# Design — english-ui-labels-and-chrome-polish

## Context

Four separate observations from one review pass, sharing a single theme: the chrome around the correction content is inconsistent with itself. Three of the four have a concrete root cause in the codebase rather than being a matter of taste, which is what makes them fixable at the source instead of case by case.

## Decision 1 — The black scrollbar is a `color-scheme` bug, not a missing scrollbar style

`globals.css` has carried this since the initial scaffold:

```css
@media (prefers-color-scheme: dark) {
  html { color-scheme: dark; }
}
```

`color-scheme: dark` tells the browser to paint UA-rendered surfaces — scrollbars, form controls, the canvas behind the page — for a dark interface. But nothing in this app ever applies the `.dark` class that `tailwind.config.js` (`darkMode: ["class"]`) and the `.dark` token block in `globals.css` exist for. The rendered app is light-only. On an OS in dark mode the result is dark-painted scrollbars framing light surfaces, which is exactly the reported symptom and matches no token in `docs/UI-DESIGN.md`.

So the fix is `color-scheme: light` on `html`, unconditionally. This is not "disabling dark mode" — there is no dark mode to disable; it is stating the theme the app actually renders. The `.dark` token block stays untouched, so wiring a real dark theme later remains a matter of toggling the class and revisiting this declaration.

Styling the scrollbars from tokens is the second half, and worth doing on top: the default light scrollbar is a browser grey unrelated to `--outline-variant`.

## Decision 2 — Reuse the carousel's `-webkit-` technique, do not introduce the standard properties

The Job Queue carousel already solved "style a scrollbar without losing it", and `globals.css` records why:

> `scrollbar-width`/`scrollbar-color` are deliberately omitted: setting the standard properties makes Chrome fall back to macOS overlay scrollbars, which stay invisible until the user already scrolls.

That constraint applies to the carousel because its scrollbar is an affordance the user must see before scrolling. For the panes it matters less — but adding `scrollbar-color` there would mean two different scrollbar mechanisms in one file, and the pane scrollbars would then behave differently from the carousel's on the same machine. So the new `.token-scrollbar` utility uses only `::-webkit-scrollbar*`, mirroring `.job-carousel-track`:

| Part | Value |
|---|---|
| Width/height | `10px` (panes carry more content than the carousel's `6px` rail) |
| Track | `transparent` |
| Thumb | `hsl(var(--outline-variant))`, `rounded-full`, inset via a transparent border + `background-clip: content-box` |
| Thumb hover | `hsl(var(--outline))` |

Firefox keeps its default scrollbar, now light rather than dark — the reported defect is gone there without a second mechanism. The carousel block is left byte-identical so its always-visible rail cannot regress; only `--outline-variant` / `--outline`, which it already used, are now shared vocabulary.

Applied to: the editor pane, the review pane, and the notifications list. The docked and floating session lists scroll through Radix `ScrollArea`, which hides the native scrollbar and draws its own thumb — that thumb is on `bg-border`, a legacy shadcn token, and moves to `bg-outline-variant` with `hover:bg-outline` for the same reason.

## Decision 3 — Fix the hover-goes-black at the `Badge` component, not per call site

Every darkening readout is a `Badge`. shadcn's `badgeVariants` gives `default`, `secondary` and `destructive` a `hover:bg-*/80`, and `--primary` in this project is `0 0% 9%` — near-black, a legacy shadcn token retained only for component compatibility (`docs/UI-DESIGN.md`, "Legacy Tokens"). Call sites that pass `className="bg-surface-container …"` replace the base `bg-primary` through `tailwind-merge` but not the `hover:` variant, which lives in a different modifier group. Hence a badge that looks correct at rest and turns near-black under the cursor.

Removing the hover states from the variants fixes all of them at once — the `LATEST` timer, `AVG`, `Saved: N`, the selection counter, job status and provider badges, the pane-switch count — and cannot silently miss one that is added later. No `Badge` in this codebase takes an `onClick`, and none needs to: a badge is a readout. If an interactive badge is ever wanted, hover belongs on that call site, where it is a deliberate claim about behaviour.

`transition-colors` stays in the base class: it is harmless with nothing to transition, and it still serves the badges whose colour changes with state (the `LATEST` badge switches between paused, live and completed styling).

`cursor: pointer` needs no change — no non-interactive element in the workspace sets it. The suggestion card looks like a counterexample but is genuinely activatable (double-click toggles selection).

## Decision 4 — Removing the provider badge loses nothing

`クラウドAPI` / `ローカルAI` sits beside the offline-mode checkbox and reflects `lastSuggestionSource`, set when a job is opened for review. Two surfaces already carry the same fact more precisely:

| Surface | What it says |
|---|---|
| Job card `API` / `WebLLM` badge | which provider ran that specific generation, for every job in the queue, not just the last one reviewed |
| Suggestion panel provenance caption | the exact model id (`gemini-3.7-flash used`), which the badge could not express |

The badge is therefore strictly redundant, and it is the vaguer of the three. `lastSuggestionSource` state stays — it is also what decides the `llmProvider` value written when a round is saved — so this is a JSX-only removal, with the offline-mode row keeping its `flex-wrap` layout for the label alone.

## Decision 5 — English wording follows the tone already set, and stops at the content boundary

The existing English chrome is uppercase `text-label-caps` for section headings (`SOURCE TEXT`, `JOB QUEUE`, `HISTORY`) and sentence-case for controls and prose (`Generate AI Suggestions`, `Select 3+ to save`, `N Results`). New strings follow the surface they sit on: the pane switch is a section-level chooser, so `TEXT` / `SUGGESTIONS` (the user's explicit wording); badges and counters are sentence case (`Completed`, `Selected: 0/3+`).

The exemplar card heading keeps a two-part form so its purpose survives translation: `EXEMPLAR TEXT (reference translation)` with the marker `optional` where `任意` was. The user asked for both "参考訳文" and "optional"; since the deciding rule for this change is that application-supplied chrome is English, the Japanese gloss becomes the English gloss and the marker becomes `optional` — which is also what the `任意` marker always meant.

Two categories deliberately stay Japanese, because they are not chrome:

- **Values sent to the server or matched against provider output** — `instructionPrompt: "CCTalkからの添削指示"` is persisted data; `overallComment.includes("抽出できませんでした")` matches parser output. Translating either changes behaviour, not presentation.
- **AI critique text and user input** — the reason this app exists.

Timestamps are left on `toLocaleString()` / `toLocaleTimeString()`. Pinning `en-US` would trade a label the user can now read for dates they read less easily, which is not what "make the chrome one language" was asking for.

## Decision 6 — `New Session` moves within the scale, not outside it

The button label currently inherits `text-sm` from the shadcn button base, with `font-semibold` from the call site. The typography scale in `docs/UI-DESIGN.md` offers `body-base` (16px/400) as the next step up from `body-sm` (14px/400); combined with the existing `font-semibold` that gives 16px/600. `headline-md` (20px/600) would out-shout the `MJAI` wordmark's sibling nav, so `body-base` is the right rung. No new value is introduced, and `docs/UI-DESIGN.md` records the pairing.

## Risks / Trade-offs

- **A test may assert a Japanese label.** `apiError.test.tsx` looks up the offline-mode checkbox by its Japanese label. Renaming without updating it fails the suite — which is the desired failure mode, and the update is part of this change.
- **`Badge` hover removal is global.** If a future badge is meant to be clickable it must ask for hover explicitly. That is the correct default: the component's job is to display.
- **`.token-scrollbar` is WebKit-only.** Deliberate, per Decision 2. Firefox gets a correct light default rather than a token-matched thumb.
