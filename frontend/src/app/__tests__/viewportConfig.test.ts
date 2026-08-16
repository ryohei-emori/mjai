/**
 * The document's viewport declaration.
 *
 * Two things about it are easy to break by accident and expensive to notice: the
 * keyboard-aware layout the workspace's `dvh` height depends on, and the absence
 * of a zoom lock. Suppressing pinch zoom is the routine collateral damage of a
 * mobile pass, and this app shows dense CJK text that people need to magnify.
 */
// `next/font/google` is a build-time transform, not a runtime module, so it has
// to be stubbed to import the layout at all.
jest.mock("next/font/google", () => ({
  Inter: () => ({ variable: "--font-inter" }),
  Geist_Mono: () => ({ variable: "--font-geist-mono" }),
}))

import { viewport } from "../layout"

test("the layout viewport resizes for the on-screen keyboard", () => {
  expect(viewport.width).toBe("device-width")
  expect(viewport.initialScale).toBe(1)
  // Without this only the visual viewport shrinks, so `dvh` keeps reporting the
  // full height and the focused field can sit behind the keyboard.
  expect(viewport.interactiveWidget).toBe("resizes-content")
})

test("zoom is not suppressed", () => {
  expect(viewport.maximumScale).toBeUndefined()
  expect(viewport.userScalable).toBeUndefined()
})
