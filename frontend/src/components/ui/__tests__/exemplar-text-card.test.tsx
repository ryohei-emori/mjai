import React from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import "@testing-library/jest-dom"
import { ExemplarTextCard } from "../exemplar-text-card"

describe("ExemplarTextCard", () => {
  it("renders the bilingual English-primary header and an optional marker", () => {
    render(<ExemplarTextCard value="" onChange={() => {}} />)

    expect(screen.getByText(/EXEMPLAR TEXT \(REFERENCE TRANSLATION\)/)).toBeInTheDocument()
    expect(screen.getByText("optional")).toBeInTheDocument()
  })

  it("reports every keystroke to onChange so no explicit save is needed", () => {
    const onChange = jest.fn()
    render(<ExemplarTextCard value="" onChange={onChange} open />)

    fireEvent.change(screen.getByRole("textbox"), { target: { value: "模範の訳文" } })

    expect(onChange).toHaveBeenCalledWith("模範の訳文")
  })

  it("shows the current value", () => {
    render(<ExemplarTextCard value="既存の模範訳" onChange={() => {}} open />)

    expect(screen.getByRole("textbox")).toHaveValue("既存の模範訳")
  })

  it("omits the copy button when no onCopy handler is given", () => {
    render(<ExemplarTextCard value="模範の訳文" onChange={() => {}} open />)

    expect(screen.queryByTitle("Copy")).not.toBeInTheDocument()
  })

  it("copies the current value when the copy button is used", () => {
    const onCopy = jest.fn()
    render(<ExemplarTextCard value="模範の訳文" onChange={() => {}} onCopy={onCopy} open />)

    fireEvent.click(screen.getByTitle("Copy"))

    expect(onCopy).toHaveBeenCalledWith("模範の訳文")
  })

  it("does not call onCopy for an empty field", () => {
    const onCopy = jest.fn()
    render(<ExemplarTextCard value="" onChange={() => {}} onCopy={onCopy} open />)

    fireEvent.click(screen.getByTitle("Copy"))

    expect(onCopy).not.toHaveBeenCalled()
  })

  describe("disclosure", () => {
    it("is collapsed by default, hiding the textarea while keeping the header", () => {
      render(<ExemplarTextCard value="" onChange={() => {}} />)

      expect(screen.getByText(/EXEMPLAR TEXT/)).toBeInTheDocument()
      expect(screen.queryByRole("textbox")).not.toBeInTheDocument()
    })

    it("exposes its state on the header disclosure control", () => {
      const { rerender } = render(<ExemplarTextCard value="" onChange={() => {}} />)

      const collapsedToggle = screen.getByRole("button", { expanded: false })
      expect(collapsedToggle).toHaveAttribute("aria-controls", "exemplar-text-card-content")

      rerender(<ExemplarTextCard value="" onChange={() => {}} open />)
      expect(screen.getByRole("button", { expanded: true })).toBeInTheDocument()
    })

    it("requests expansion when collapsed and collapse when expanded", () => {
      const onOpenChange = jest.fn()
      const { rerender } = render(
        <ExemplarTextCard value="" onChange={() => {}} onOpenChange={onOpenChange} />,
      )

      fireEvent.click(screen.getByRole("button", { expanded: false }))
      expect(onOpenChange).toHaveBeenLastCalledWith(true)

      rerender(
        <ExemplarTextCard value="" onChange={() => {}} onOpenChange={onOpenChange} open />,
      )
      fireEvent.click(screen.getByRole("button", { expanded: true }))
      expect(onOpenChange).toHaveBeenLastCalledWith(false)
    })

    it("indicates entered content while collapsed", () => {
      render(<ExemplarTextCard value="模範の訳文" onChange={() => {}} />)

      expect(screen.getByText("Filled")).toBeInTheDocument()
      expect(screen.getByText("5 chars")).toBeInTheDocument()
    })

    it("shows no content indicator for a blank field", () => {
      render(<ExemplarTextCard value="   " onChange={() => {}} />)

      expect(screen.queryByText("Filled")).not.toBeInTheDocument()
    })

    it("drops the content indicator once expanded, where the text itself is visible", () => {
      render(<ExemplarTextCard value="模範の訳文" onChange={() => {}} open />)

      expect(screen.queryByText("Filled")).not.toBeInTheDocument()
      expect(screen.getByRole("textbox")).toHaveValue("模範の訳文")
    })

    it("keeps the value intact across a collapse and re-expand", () => {
      const { rerender } = render(
        <ExemplarTextCard value="模範の訳文" onChange={() => {}} open />,
      )
      expect(screen.getByRole("textbox")).toHaveValue("模範の訳文")

      rerender(<ExemplarTextCard value="模範の訳文" onChange={() => {}} />)
      expect(screen.queryByRole("textbox")).not.toBeInTheDocument()

      rerender(<ExemplarTextCard value="模範の訳文" onChange={() => {}} open />)
      expect(screen.getByRole("textbox")).toHaveValue("模範の訳文")
    })

    it("keeps the copy button usable while collapsed", () => {
      const onCopy = jest.fn()
      render(<ExemplarTextCard value="模範の訳文" onChange={() => {}} onCopy={onCopy} />)

      fireEvent.click(screen.getByTitle("Copy"))

      expect(onCopy).toHaveBeenCalledWith("模範の訳文")
    })
  })
})
