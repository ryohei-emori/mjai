import React from "react"
import { render, screen, fireEvent } from "@testing-library/react"
import "@testing-library/jest-dom"
import { JobQueueCarousel } from "../job-queue-carousel"

// jsdom はレイアウトを実装しないため clientWidth/scrollWidth/scrollBy はすべて
// スタブ。ここでは「オーバーフローしている/していない」を実測値として注入し、
// 実際のスナップ挙動はブラウザでの手動確認に委ねる（design.md Risks参照）。
type TrackMetrics = { clientWidth: number; scrollWidth: number; scrollLeft?: number }

function stubTrackMetrics({ clientWidth, scrollWidth, scrollLeft = 0 }: TrackMetrics) {
  Object.defineProperty(HTMLElement.prototype, "clientWidth", {
    configurable: true,
    get() {
      return this.getAttribute("role") === "group" ? clientWidth : 0
    },
  })
  Object.defineProperty(HTMLElement.prototype, "scrollWidth", {
    configurable: true,
    get() {
      return this.getAttribute("role") === "group" ? scrollWidth : 0
    },
  })
  Object.defineProperty(HTMLElement.prototype, "scrollLeft", {
    configurable: true,
    get() {
      return scrollLeft
    },
    set() {},
  })
}

const items = [
  { id: "a", label: "ジョブA" },
  { id: "b", label: "ジョブB" },
  { id: "c", label: "ジョブC" },
]

function renderCarousel(list = items) {
  return render(
    <JobQueueCarousel
      items={list}
      getKey={(item) => item.id}
      ariaLabel="Job queue (slides horizontally)"
      renderItem={(item) => <div>{item.label}</div>}
    />,
  )
}

describe("JobQueueCarousel", () => {
  let scrollBy: jest.Mock

  beforeEach(() => {
    scrollBy = jest.fn()
    Object.defineProperty(HTMLElement.prototype, "scrollBy", {
      configurable: true,
      value: scrollBy,
    })
  })

  it("renders every item inside a labelled scroll region", () => {
    stubTrackMetrics({ clientWidth: 300, scrollWidth: 300 })
    renderCarousel()

    expect(screen.getByRole("group", { name: "Job queue (slides horizontally)" })).toBeInTheDocument()
    expect(screen.getByText("ジョブA")).toBeInTheDocument()
    expect(screen.getByText("ジョブB")).toBeInTheDocument()
    expect(screen.getByText("ジョブC")).toBeInTheDocument()
  })

  it("hides navigation controls when the track does not overflow", () => {
    stubTrackMetrics({ clientWidth: 900, scrollWidth: 900 })
    renderCarousel()

    expect(screen.queryByRole("button", { name: "Next jobs" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Previous jobs" })).not.toBeInTheDocument()
  })

  it("exposes labelled arrows and disables the one at the current edge", () => {
    stubTrackMetrics({ clientWidth: 300, scrollWidth: 900 })
    renderCarousel()

    expect(screen.getByRole("button", { name: "Previous jobs" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Next jobs" })).toBeEnabled()
  })

  it("scrolls forward by about one visible width when next is activated", () => {
    stubTrackMetrics({ clientWidth: 300, scrollWidth: 900 })
    renderCarousel()

    fireEvent.click(screen.getByRole("button", { name: "Next jobs" }))
    expect(scrollBy).toHaveBeenCalledWith({ left: 300, behavior: "smooth" })
  })

  it("slides the track with ArrowRight / ArrowLeft", () => {
    stubTrackMetrics({ clientWidth: 300, scrollWidth: 900 })
    renderCarousel()
    const track = screen.getByRole("group", { name: "Job queue (slides horizontally)" })

    fireEvent.keyDown(track, { key: "ArrowRight" })
    expect(scrollBy).toHaveBeenLastCalledWith({ left: 300, behavior: "smooth" })

    fireEvent.keyDown(track, { key: "ArrowLeft" })
    expect(scrollBy).toHaveBeenLastCalledWith({ left: -300, behavior: "smooth" })
  })

  it("ignores arrow keys that originate from a text field", () => {
    stubTrackMetrics({ clientWidth: 300, scrollWidth: 900 })
    render(
      <JobQueueCarousel
        items={items}
        getKey={(item) => item.id}
        ariaLabel="Job queue (slides horizontally)"
        renderItem={(item) => <textarea defaultValue={item.label} aria-label={item.label} />}
      />,
    )

    fireEvent.keyDown(screen.getByLabelText("ジョブA"), { key: "ArrowRight" })
    expect(scrollBy).not.toHaveBeenCalled()
  })

  it("keeps item-level keyboard activation working", () => {
    stubTrackMetrics({ clientWidth: 300, scrollWidth: 900 })
    const onConfirm = jest.fn()
    render(
      <JobQueueCarousel
        items={items}
        getKey={(item) => item.id}
        ariaLabel="Job queue (slides horizontally)"
        renderItem={(item) => (
          <div
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter") onConfirm(item.id)
            }}
          >
            {item.label}
          </div>
        )}
      />,
    )

    fireEvent.keyDown(screen.getByRole("button", { name: "ジョブB" }), { key: "Enter" })
    expect(onConfirm).toHaveBeenCalledWith("b")
  })
})
