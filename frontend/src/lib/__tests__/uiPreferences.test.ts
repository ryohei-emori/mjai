import {
  EXEMPLAR_CARD_STORAGE_KEY,
  LG_BREAKPOINT_PX,
  SESSION_PANE_STORAGE_KEY,
  defaultSessionPaneMode,
  dockSessionPaneState,
  isPaneDocked,
  loadExemplarCardOpen,
  loadSessionPaneMode,
  resolveSessionPaneMode,
  saveExemplarCardOpen,
  saveSessionPaneMode,
  toggleSessionPaneState,
} from "../uiPreferences"

function setViewportWidth(width: number) {
  Object.defineProperty(window, "innerWidth", {
    configurable: true,
    writable: true,
    value: width,
  })
}

/** Replaces `window.localStorage` for one test, restoring it afterwards. */
function withBrokenStorage(run: () => void) {
  const original = Object.getOwnPropertyDescriptor(window, "localStorage")
  Object.defineProperty(window, "localStorage", {
    configurable: true,
    get() {
      throw new Error("localStorage is disabled")
    },
  })
  try {
    run()
  } finally {
    if (original) {
      Object.defineProperty(window, "localStorage", original)
    } else {
      // @ts-expect-error - test-only cleanup when the property was absent
      delete window.localStorage
    }
  }
}

describe("session pane mode preference", () => {
  beforeEach(() => {
    window.localStorage.clear()
    setViewportWidth(1440)
  })

  describe("defaultSessionPaneMode", () => {
    it("docks at and above the lg breakpoint", () => {
      expect(defaultSessionPaneMode(LG_BREAKPOINT_PX)).toBe("docked")
      expect(defaultSessionPaneMode(1920)).toBe("docked")
    })

    it("floats below the lg breakpoint", () => {
      expect(defaultSessionPaneMode(LG_BREAKPOINT_PX - 1)).toBe("floating")
      expect(defaultSessionPaneMode(390)).toBe("floating")
    })
  })

  describe("resolveSessionPaneMode", () => {
    it("honours a recognised stored value regardless of viewport", () => {
      expect(resolveSessionPaneMode("floating", 1920)).toBe("floating")
      expect(resolveSessionPaneMode("docked", 390)).toBe("docked")
    })

    it("falls back to the viewport default when nothing is stored", () => {
      expect(resolveSessionPaneMode(null, 1920)).toBe("docked")
      expect(resolveSessionPaneMode(null, 390)).toBe("floating")
    })

    it("treats a malformed stored value as nothing stored", () => {
      expect(resolveSessionPaneMode("", 1920)).toBe("docked")
      expect(resolveSessionPaneMode("DOCKED", 1920)).toBe("docked")
      expect(resolveSessionPaneMode('{"mode":"floating"}', 390)).toBe("floating")
    })
  })

  describe("loadSessionPaneMode", () => {
    it("restores a previously saved choice", () => {
      saveSessionPaneMode("floating")

      expect(window.localStorage.getItem(SESSION_PANE_STORAGE_KEY)).toBe("floating")
      expect(loadSessionPaneMode()).toBe("floating")
    })

    it("round-trips a re-docked choice", () => {
      saveSessionPaneMode("floating")
      saveSessionPaneMode("docked")

      expect(loadSessionPaneMode()).toBe("docked")
    })

    it("defaults by viewport on a first visit", () => {
      expect(loadSessionPaneMode()).toBe("docked")

      setViewportWidth(390)
      expect(loadSessionPaneMode()).toBe("floating")
    })

    it("falls back to the viewport default when storage throws", () => {
      withBrokenStorage(() => {
        expect(loadSessionPaneMode()).toBe("docked")
        setViewportWidth(390)
        expect(loadSessionPaneMode()).toBe("floating")
      })
    })
  })

  describe("saveSessionPaneMode", () => {
    it("does not throw when storage is unavailable", () => {
      const warn = jest.spyOn(console, "warn").mockImplementation(() => {})
      withBrokenStorage(() => {
        expect(() => saveSessionPaneMode("floating")).not.toThrow()
      })
      expect(warn).toHaveBeenCalled()
      warn.mockRestore()
    })
  })
})

describe("session pane transitions", () => {
  const DOCKED = { mode: "docked" as const, overlayOpen: false }
  const FLOATING_CLOSED = { mode: "floating" as const, overlayOpen: false }
  const FLOATING_OPEN = { mode: "floating" as const, overlayOpen: true }

  describe("isPaneDocked", () => {
    it("renders the column only when docked at a wide viewport", () => {
      expect(isPaneDocked(DOCKED, true)).toBe(true)
      expect(isPaneDocked(DOCKED, false)).toBe(false)
      expect(isPaneDocked(FLOATING_CLOSED, true)).toBe(false)
    })
  })

  describe("toggleSessionPaneState", () => {
    it("floats a docked pane without reopening the list", () => {
      expect(toggleSessionPaneState(DOCKED, true)).toEqual(FLOATING_CLOSED)
    })

    it("opens the overlay when the pane is already floating", () => {
      expect(toggleSessionPaneState(FLOATING_CLOSED, true)).toEqual(FLOATING_OPEN)
    })

    it("closes an open overlay", () => {
      expect(toggleSessionPaneState(FLOATING_OPEN, true)).toEqual(FLOATING_CLOSED)
    })

    it("never re-docks, so the same button works below the lg breakpoint", () => {
      expect(toggleSessionPaneState(FLOATING_OPEN, false)).toEqual(FLOATING_CLOSED)
      expect(toggleSessionPaneState(FLOATING_CLOSED, false)).toEqual(FLOATING_OPEN)
    })

    it("opens the overlay for a stored docked preference at a narrow viewport", () => {
      // The column is not rendered there, so the trigger must show the overlay
      // rather than pointlessly rewriting the stored mode.
      expect(toggleSessionPaneState(DOCKED, false)).toEqual({
        mode: "docked",
        overlayOpen: true,
      })
    })
  })

  describe("dockSessionPaneState", () => {
    it("docks and closes the overlay", () => {
      expect(dockSessionPaneState()).toEqual(DOCKED)
    })

    it("completes a float-and-redock round trip", () => {
      const floated = toggleSessionPaneState(DOCKED, true)
      expect(floated.mode).toBe("floating")
      expect(dockSessionPaneState()).toEqual(DOCKED)
    })
  })
})

describe("exemplar card disclosure preference", () => {
  beforeEach(() => {
    window.localStorage.clear()
  })

  it("is collapsed when nothing has been stored", () => {
    expect(loadExemplarCardOpen()).toBe(false)
  })

  it("restores an expanded card", () => {
    saveExemplarCardOpen(true)

    expect(window.localStorage.getItem(EXEMPLAR_CARD_STORAGE_KEY)).toBe("1")
    expect(loadExemplarCardOpen()).toBe(true)
  })

  it("restores a re-collapsed card", () => {
    saveExemplarCardOpen(true)
    saveExemplarCardOpen(false)

    expect(loadExemplarCardOpen()).toBe(false)
  })

  it("treats a malformed stored value as collapsed", () => {
    window.localStorage.setItem(EXEMPLAR_CARD_STORAGE_KEY, "true")

    expect(loadExemplarCardOpen()).toBe(false)
  })

  it("falls back to collapsed and does not throw when storage is unavailable", () => {
    const warn = jest.spyOn(console, "warn").mockImplementation(() => {})
    withBrokenStorage(() => {
      expect(loadExemplarCardOpen()).toBe(false)
      expect(() => saveExemplarCardOpen(true)).not.toThrow()
    })
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })
})
