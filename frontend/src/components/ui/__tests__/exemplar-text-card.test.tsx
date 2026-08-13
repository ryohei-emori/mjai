import React from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import "@testing-library/jest-dom"
import { ExemplarTextCard } from "../exemplar-text-card"

describe("ExemplarTextCard", () => {
  it("renders the bilingual English-primary header and an optional marker", () => {
    render(<ExemplarTextCard value="" onChange={() => {}} />)

    expect(screen.getByText(/EXEMPLAR TEXT \(模範回答訳文\)/)).toBeInTheDocument()
    expect(screen.getByText("任意")).toBeInTheDocument()
  })

  it("reports every keystroke to onChange so no explicit save is needed", () => {
    const onChange = jest.fn()
    render(<ExemplarTextCard value="" onChange={onChange} />)

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "模範の訳文" } })

    expect(onChange).toHaveBeenCalledWith("模範の訳文")
  })

  it("shows the current value", () => {
    render(<ExemplarTextCard value="既存の模範訳" onChange={() => {}} />)

    expect(screen.getByRole("textbox")).toHaveValue("既存の模範訳")
  })

  it("omits the copy button when no onCopy handler is given", () => {
    render(<ExemplarTextCard value="模範の訳文" onChange={() => {}} />)

    expect(screen.queryByTitle("コピー")).not.toBeInTheDocument()
  })

  it("copies the current value when the copy button is used", () => {
    const onCopy = jest.fn()
    render(<ExemplarTextCard value="模範の訳文" onChange={() => {}} onCopy={onCopy} />)

    fireEvent.click(screen.getByTitle("コピー"))

    expect(onCopy).toHaveBeenCalledWith("模範の訳文")
  })

  it("does not call onCopy for an empty field", () => {
    const onCopy = jest.fn()
    render(<ExemplarTextCard value="" onChange={() => {}} onCopy={onCopy} />)

    fireEvent.click(screen.getByTitle("コピー"))

    expect(onCopy).not.toHaveBeenCalled()
  })
})
