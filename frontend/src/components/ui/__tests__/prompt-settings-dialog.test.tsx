import React from "react"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import "@testing-library/jest-dom"

import { PromptSettingsDialog } from "../prompt-settings-dialog"
import { PROMPT_COMPOSITION_STEPS } from "@/lib/promptComposition"

jest.mock("@/app/api", () => ({
  settingsAPI: {
    getPrompt: jest.fn(),
    updatePrompt: jest.fn(),
    resetPrompt: jest.fn(),
  },
}))

// eslint-disable-next-line @typescript-eslint/no-require-imports
const { settingsAPI } = require("@/app/api") as {
  settingsAPI: {
    getPrompt: jest.Mock
    updatePrompt: jest.Mock
    resetPrompt: jest.Mock
  }
}

const DEFAULT_SETTINGS = {
  systemPrompt: "既定のルール本文",
  defaultSystemPrompt: "既定のルール本文",
  isCustomized: false,
  updatedAt: null,
  updatedBy: null,
}

const CUSTOM_SETTINGS = {
  systemPrompt: "カスタムのルール本文",
  defaultSystemPrompt: "既定のルール本文",
  isCustomized: true,
  updatedAt: "2026-08-16T07:00:00+00:00",
  updatedBy: "owner@example.com",
}

const promptTextarea = () => screen.getByRole("textbox", { name: "System prompt" })

describe("PromptSettingsDialog", () => {
  beforeEach(() => {
    settingsAPI.getPrompt.mockResolvedValue(DEFAULT_SETTINGS)
    settingsAPI.updatePrompt.mockResolvedValue(CUSTOM_SETTINGS)
    settingsAPI.resetPrompt.mockResolvedValue(DEFAULT_SETTINGS)
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it("loads the effective prompt when opened", async () => {
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)

    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))
    expect(screen.getByText("Default")).toBeInTheDocument()
  })

  it("does not fetch anything while closed", () => {
    render(<PromptSettingsDialog open={false} onOpenChange={() => {}} />)

    expect(settingsAPI.getPrompt).not.toHaveBeenCalled()
  })

  it("shows who last customized the prompt", async () => {
    settingsAPI.getPrompt.mockResolvedValue(CUSTOM_SETTINGS)
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)

    await waitFor(() => expect(promptTextarea()).toHaveValue("カスタムのルール本文"))
    expect(screen.getByText("Custom")).toBeInTheDocument()
    expect(screen.getByText(/owner@example\.com/)).toBeInTheDocument()
  })

  it("keeps save disabled until the text actually changes", async () => {
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled()

    fireEvent.change(promptTextarea(), { target: { value: "編集後の本文" } })
    expect(screen.getByRole("button", { name: "Save" })).toBeEnabled()
  })

  it("saves the edited prompt and closes", async () => {
    const onOpenChange = jest.fn()
    const onSaved = jest.fn()
    render(<PromptSettingsDialog open onOpenChange={onOpenChange} onSaved={onSaved} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    fireEvent.change(promptTextarea(), { target: { value: "  編集後の本文  " } })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))

    await waitFor(() =>
      expect(settingsAPI.updatePrompt).toHaveBeenCalledWith("編集後の本文"),
    )
    expect(onSaved).toHaveBeenCalled()
    expect(onOpenChange).toHaveBeenCalledWith(false)
  })

  it("rejects an emptied prompt without calling the API", async () => {
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    fireEvent.change(promptTextarea(), { target: { value: "   " } })

    expect(screen.getByRole("alert")).toHaveTextContent("cannot be empty")
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled()
    expect(settingsAPI.updatePrompt).not.toHaveBeenCalled()
  })

  it("rejects an oversized prompt and states the limit", async () => {
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    fireEvent.change(promptTextarea(), { target: { value: "あ".repeat(20001) } })

    expect(screen.getByRole("alert")).toHaveTextContent("within 20,000 characters")
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled()
  })

  it("keeps the edited text and shows the error when saving fails", async () => {
    settingsAPI.updatePrompt.mockRejectedValue(new Error("API Error: 500"))
    const onOpenChange = jest.fn()
    render(<PromptSettingsDialog open onOpenChange={onOpenChange} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    fireEvent.change(promptTextarea(), { target: { value: "編集後の本文" } })
    fireEvent.click(screen.getByRole("button", { name: "Save" }))

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("API Error: 500"))
    expect(promptTextarea()).toHaveValue("編集後の本文")
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
  })

  it("asks for confirmation before resetting to the default", async () => {
    settingsAPI.getPrompt.mockResolvedValue(CUSTOM_SETTINGS)
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("カスタムのルール本文"))

    fireEvent.click(screen.getByRole("button", { name: "Reset to Default" }))
    expect(settingsAPI.resetPrompt).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole("button", { name: "Confirm Reset" }))
    await waitFor(() => expect(settingsAPI.resetPrompt).toHaveBeenCalled())
    expect(promptTextarea()).toHaveValue("既定のルール本文")
  })

  it("discloses where the supplied text is inserted, in assembly order", async () => {
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)

    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    const steps = screen.getAllByRole("listitem").map((li) => li.textContent ?? "")
    expect(steps).toHaveLength(PROMPT_COMPOSITION_STEPS.length)
    PROMPT_COMPOSITION_STEPS.forEach((step, index) => {
      expect(steps[index]).toContain(step.label)
      expect(steps[index]).toContain(step.detail)
    })

    // The question this section exists to answer: an operator writing a rule
    // about the exemplar needs to know it is absent unless they pasted one.
    const exemplarStep = steps.find((text) => text.includes("EXEMPLAR TEXT"))
    expect(exemplarStep).toContain("only when EXEMPLAR TEXT is filled in")
  })

  it("no longer claims that offline mode ignores this prompt", async () => {
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)

    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))
    expect(screen.queryByText(/オフラインモード/)).not.toBeInTheDocument()
  })

  it("uses only English copy", async () => {
    const { container } = render(<PromptSettingsDialog open onOpenChange={() => {}} />)

    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    // Kana in the chrome would mean a string was missed. The prompt text itself
    // and the two 原文/模範回答訳文 glosses are legitimately not English, so the
    // scan excludes the editor's value and matches kana rather than all CJK.
    promptTextarea().remove()
    const chrome = (container.textContent ?? "").replace(
      /原文|模範回答訳文|添削対象/g,
      "",
    )
    expect(chrome).not.toMatch(/[\u3040-\u30ff]/)
  })

  it("surfaces a load failure instead of showing a blank editor silently", async () => {
    settingsAPI.getPrompt.mockRejectedValue(new Error("API Error: 503"))
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("API Error: 503"))
  })
})
