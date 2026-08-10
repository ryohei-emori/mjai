# Tasks: Split System and UI Design Docs

## 1. Prepare SYSTEM-DESIGN.md

- [x] 1.1 Remove §8 "Future Work / Open Questions" section from `docs/DESIGN.md`
- [x] 1.2 Rename `docs/DESIGN.md` → `docs/SYSTEM-DESIGN.md`
- [x] 1.3 Convert ASCII-art system diagram (§4) to Mermaid flowchart
- [x] 1.4 Add header clarification that this is the engineering architecture doc (not UI design — see `UI-DESIGN.md`)
- [x] 1.5 Update internal cross-reference to point to `UI-DESIGN.md` for visual identity

## 2. Create UI-DESIGN.md

- [x] 2.1 Create `docs/UI-DESIGN.md` with document structure (header, purpose statement)
- [x] 2.2 Extract and document color palette from `globals.css` `:root` CSS custom properties (light mode)
- [x] 2.3 Extract and document color palette from `globals.css` `.dark` CSS custom properties (dark mode)
- [x] 2.4 Document spacing/radius scale (`--radius` and Tailwind extensions)
- [x] 2.5 Document component library configuration from `components.json` (shadcn/ui style, base color, icon library)
- [x] 2.6 Add cross-reference to `SYSTEM-DESIGN.md` for engineering architecture

## 3. Update References

- [x] 3.1 Update `AGENTS.md` Documentation habits section: change `docs/DESIGN.md` → `docs/SYSTEM-DESIGN.md`
- [x] 3.2 Update `AGENTS.md` Never do section: change `docs/DESIGN.md` → `docs/SYSTEM-DESIGN.md`
- [x] 3.3 Update `openspec/specs/architecture-documentation/spec.md`: change all `docs/DESIGN.md` → `docs/SYSTEM-DESIGN.md`
- [x] 3.4 Search for any other references to `docs/DESIGN.md` and update if found

## 4. Validation

- [x] 4.1 Verify `docs/SYSTEM-DESIGN.md` Mermaid diagram renders correctly
- [x] 4.2 Verify `docs/UI-DESIGN.md` token values match actual `globals.css` values
- [x] 4.3 Verify all `docs/DESIGN.md` references have been updated
