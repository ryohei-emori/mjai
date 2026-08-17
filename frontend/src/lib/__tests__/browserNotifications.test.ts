import {
  getNotificationPermission,
  isBrowserNotificationSupported,
  requestNotificationPermission,
  shouldShowBrowserNotification,
  showJobCompletedNotification,
} from "../browserNotifications"

type NotificationStub = {
  tag?: string
  body?: string
  title: string
  close: jest.Mock
  onclick: (() => void) | null
}

const constructed: NotificationStub[] = []

/**
 * Installs a stand-in for `window.Notification` for one test. jsdom has none,
 * which is deliberately the default state here — the unsupported path is what
 * runs unless a test opts into a browser that has the API.
 */
function withNotificationApi(
  permission: NotificationPermission,
  requestResult?: NotificationPermission | Error,
  run: () => void | Promise<void> = () => {},
): void | Promise<void> {
  const original = Object.getOwnPropertyDescriptor(window, "Notification")

  class NotificationMock {
    static permission: NotificationPermission = permission
    static requestPermission = jest.fn(async () => {
      if (requestResult instanceof Error) throw requestResult
      return requestResult ?? permission
    })

    title: string
    tag?: string
    body?: string
    close = jest.fn()
    onclick: (() => void) | null = null

    constructor(title: string, options?: NotificationOptions) {
      this.title = title
      this.tag = options?.tag
      this.body = options?.body
      constructed.push(this as unknown as NotificationStub)
    }
  }

  Object.defineProperty(window, "Notification", {
    configurable: true,
    writable: true,
    value: NotificationMock,
  })

  const restore = () => {
    if (original) {
      Object.defineProperty(window, "Notification", original)
    } else {
      // @ts-expect-error - test-only cleanup when the property was absent
      delete window.Notification
    }
  }

  try {
    const result = run()
    if (result instanceof Promise) return result.finally(restore)
    restore()
  } catch (error) {
    restore()
    throw error
  }
}

beforeEach(() => {
  constructed.length = 0
})

describe("permission reading", () => {
  it("reports a browser without the Notification API as unsupported", () => {
    expect(isBrowserNotificationSupported()).toBe(false)
    expect(getNotificationPermission()).toBe("unsupported")
  })

  it("reports granted", () => {
    withNotificationApi("granted", undefined, () => {
      expect(isBrowserNotificationSupported()).toBe(true)
      expect(getNotificationPermission()).toBe("granted")
    })
  })

  it("reports denied", () => {
    withNotificationApi("denied", undefined, () => {
      expect(getNotificationPermission()).toBe("denied")
    })
  })

  it("reports an undecided permission as default", () => {
    withNotificationApi("default", undefined, () => {
      expect(getNotificationPermission()).toBe("default")
    })
  })
})

describe("permission requesting", () => {
  it("resolves to unsupported instead of throwing when there is no API", async () => {
    await expect(requestNotificationPermission()).resolves.toBe("unsupported")
  })

  it("resolves to granted when the user allows", async () => {
    await withNotificationApi("default", "granted", async () => {
      await expect(requestNotificationPermission()).resolves.toBe("granted")
    })
  })

  it("resolves to denied when the user refuses", async () => {
    await withNotificationApi("default", "denied", async () => {
      await expect(requestNotificationPermission()).resolves.toBe("denied")
    })
  })

  it("resolves to unsupported when the request itself fails", async () => {
    const warn = jest.spyOn(console, "warn").mockImplementation(() => {})
    await withNotificationApi("default", new Error("boom"), async () => {
      await expect(requestNotificationPermission()).resolves.toBe("unsupported")
    })
    expect(warn).toHaveBeenCalled()
    warn.mockRestore()
  })
})

describe("shouldShowBrowserNotification", () => {
  it("shows when enabled, granted and the tab is hidden", () => {
    expect(
      shouldShowBrowserNotification({
        enabled: true,
        permission: "granted",
        documentVisibility: "hidden",
      }),
    ).toBe(true)
  })

  it("suppresses while the tab is visible, since the bell already speaks", () => {
    expect(
      shouldShowBrowserNotification({
        enabled: true,
        permission: "granted",
        documentVisibility: "visible",
      }),
    ).toBe(false)
  })

  it("suppresses when the preference is off", () => {
    expect(
      shouldShowBrowserNotification({
        enabled: false,
        permission: "granted",
        documentVisibility: "hidden",
      }),
    ).toBe(false)
  })

  it.each(["denied", "default", "unsupported"] as const)(
    "suppresses when permission is %s",
    (permission) => {
      expect(
        shouldShowBrowserNotification({
          enabled: true,
          permission,
          documentVisibility: "hidden",
        }),
      ).toBe(false)
    },
  )

  it("shows when visibility cannot be determined", () => {
    expect(
      shouldShowBrowserNotification({
        enabled: true,
        permission: "granted",
        documentVisibility: "unknown",
      }),
    ).toBe(true)
  })
})

describe("showJobCompletedNotification", () => {
  const input = {
    label: "英雄史詩ーいかが宿命に直面",
    jobId: "job-1234",
    onActivate: jest.fn(),
  }

  beforeEach(() => {
    input.onActivate.mockReset()
  })

  it("returns null without a Notification API", () => {
    expect(showJobCompletedNotification(input)).toBeNull()
    expect(constructed).toHaveLength(0)
  })

  it("returns null when permission is not granted", () => {
    withNotificationApi("denied", undefined, () => {
      expect(showJobCompletedNotification(input)).toBeNull()
      expect(constructed).toHaveLength(0)
    })
  })

  it("shows an English notification tagged per job", () => {
    withNotificationApi("granted", undefined, () => {
      const notification = showJobCompletedNotification(input)

      expect(notification).not.toBeNull()
      expect(constructed).toHaveLength(1)
      expect(constructed[0].title).toBe("Correction suggestions ready")
      expect(constructed[0].body).toContain("open to review")
      expect(constructed[0].body).toContain(input.label)
      expect(constructed[0].tag).toBe("mjai-job-job-1234")
    })
  })

  it("closes itself and reports the job id when activated", () => {
    // jsdom does not implement window.focus and logs a "not implemented" error
    // for it; the notification treats raising the window as best-effort anyway.
    const focus = jest.spyOn(window, "focus").mockImplementation(() => {})
    withNotificationApi("granted", undefined, () => {
      showJobCompletedNotification(input)

      constructed[0].onclick?.()

      expect(focus).toHaveBeenCalled()

      expect(constructed[0].close).toHaveBeenCalled()
      expect(input.onActivate).toHaveBeenCalledWith("job-1234")
    })
    focus.mockRestore()
  })
})
