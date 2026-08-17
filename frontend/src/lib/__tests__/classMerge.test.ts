import { cn } from "../utils"

// A custom scale value tailwind-merge does not know is merged as a colour, so
// composing `text-body-base` with `text-on-primary` used to drop the colour and
// leave the New Session button's icon and label on the default body foreground.
describe("cn", () => {
  it("keeps a typography token and a text colour together", () => {
    const merged = cn(
      "bg-primary text-primary-foreground h-8 px-3 text-xs",
      "bg-md3-primary text-on-primary font-semibold text-body-base"
    )

    expect(merged).toContain("text-on-primary")
    expect(merged).toContain("text-body-base")
    expect(merged).toContain("font-semibold")
    expect(merged).not.toContain("text-primary-foreground")
  })

  it("lets a typography token override the base font size", () => {
    expect(cn("text-sm", "text-metadata")).toBe("text-metadata")
    expect(cn("text-label-caps", "text-headline-lg")).toBe("text-headline-lg")
  })

  it("lets a custom spacing value override a default-scale one", () => {
    expect(cn("p-6", "p-gutter")).toBe("p-gutter")
    expect(cn("h-16", "h-topappbar")).toBe("h-topappbar")
  })

  it("still resolves conflicts within a single group", () => {
    expect(cn("text-on-surface", "text-on-primary")).toBe("text-on-primary")
  })
})
