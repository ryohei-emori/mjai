import React from "react"
import { render, screen, waitFor, fireEvent } from "@testing-library/react"
import "@testing-library/jest-dom"

import { PromptSettingsDialog } from "../prompt-settings-dialog"

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

// By role, not by label: the dialog itself is labelled by its title, which is
// also 添削プロンプト, so getByLabelText matches two elements.
const promptTextarea = () => screen.getByRole("textbox", { name: "添削プロンプト" })

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
    expect(screen.getByText("既定")).toBeInTheDocument()
  })

  it("does not fetch anything while closed", () => {
    render(<PromptSettingsDialog open={false} onOpenChange={() => {}} />)

    expect(settingsAPI.getPrompt).not.toHaveBeenCalled()
  })

  it("shows who last customized the prompt", async () => {
    settingsAPI.getPrompt.mockResolvedValue(CUSTOM_SETTINGS)
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)

    await waitFor(() => expect(promptTextarea()).toHaveValue("カスタムのルール本文"))
    expect(screen.getByText("カスタム")).toBeInTheDocument()
    expect(screen.getByText(/owner@example\.com/)).toBeInTheDocument()
  })

  it("keeps save disabled until the text actually changes", async () => {
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    expect(screen.getByRole("button", { name: "保存" })).toBeDisabled()

    fireEvent.change(promptTextarea(), { target: { value: "編集後の本文" } })
    expect(screen.getByRole("button", { name: "保存" })).toBeEnabled()
  })

  it("saves the edited prompt and closes", async () => {
    const onOpenChange = jest.fn()
    const onSaved = jest.fn()
    render(<PromptSettingsDialog open onOpenChange={onOpenChange} onSaved={onSaved} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    fireEvent.change(promptTextarea(), { target: { value: "  編集後の本文  " } })
    fireEvent.click(screen.getByRole("button", { name: "保存" }))

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

    expect(screen.getByRole("alert")).toHaveTextContent("空にはできません")
    expect(screen.getByRole("button", { name: "保存" })).toBeDisabled()
    expect(settingsAPI.updatePrompt).not.toHaveBeenCalled()
  })

  it("rejects an oversized prompt and states the limit", async () => {
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    fireEvent.change(promptTextarea(), { target: { value: "あ".repeat(20001) } })

    expect(screen.getByRole("alert")).toHaveTextContent("20,000文字以内")
    expect(screen.getByRole("button", { name: "保存" })).toBeDisabled()
  })

  it("keeps the edited text and shows the error when saving fails", async () => {
    settingsAPI.updatePrompt.mockRejectedValue(new Error("API Error: 500"))
    const onOpenChange = jest.fn()
    render(<PromptSettingsDialog open onOpenChange={onOpenChange} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))

    fireEvent.change(promptTextarea(), { target: { value: "編集後の本文" } })
    fireEvent.click(screen.getByRole("button", { name: "保存" }))

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("API Error: 500"))
    expect(promptTextarea()).toHaveValue("編集後の本文")
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
  })

  it("asks for confirmation before resetting to the default", async () => {
    settingsAPI.getPrompt.mockResolvedValue(CUSTOM_SETTINGS)
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)
    await waitFor(() => expect(promptTextarea()).toHaveValue("カスタムのルール本文"))

    fireEvent.click(screen.getByRole("button", { name: "既定に戻す" }))
    expect(settingsAPI.resetPrompt).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole("button", { name: "本当に既定に戻す" }))
    await waitFor(() => expect(settingsAPI.resetPrompt).toHaveBeenCalled())
    expect(promptTextarea()).toHaveValue("既定のルール本文")
  })

  it("states that offline mode uses its own prompt", async () => {
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)

    await waitFor(() => expect(promptTextarea()).toHaveValue("既定のルール本文"))
    expect(screen.getByText(/オフラインモード/)).toBeInTheDocument()
  })

  it("surfaces a load failure instead of showing a blank editor silently", async () => {
    settingsAPI.getPrompt.mockRejectedValue(new Error("API Error: 503"))
    render(<PromptSettingsDialog open onOpenChange={() => {}} />)

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("API Error: 503"))
  })
})
