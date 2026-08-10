# ui-design-documentation Specification

## Purpose

Ensures the project maintains a visual-identity / design-token document that describes the UI's actual color palette, typography, spacing, and component patterns as extracted from the frontend codebase — complementing the engineering architecture document.

## ADDED Requirements

### Requirement: Maintain a UI visual-identity design document
The project SHALL maintain a UI visual-identity design document at `docs/UI-DESIGN.md` that describes the design tokens and patterns actually used in the frontend (not invented or aspirational). The document SHALL cover, at minimum: color palette (CSS custom properties), typography, spacing scale, border radii, and component library configuration.

#### Scenario: UI design document exists and reflects actual frontend tokens
- **WHEN** a contributor opens `docs/UI-DESIGN.md`
- **THEN** it describes design tokens (colors, typography, spacing, radii) that match the values defined in `frontend/src/app/globals.css`, `frontend/tailwind.config.js`, and `frontend/components.json`

#### Scenario: UI design document distinguishes light and dark mode tokens
- **WHEN** the frontend defines separate CSS custom properties for light and dark modes
- **THEN** `docs/UI-DESIGN.md` SHALL document both mode variants and their HSL values

### Requirement: Keep the UI design document in sync with frontend changes
Whenever design tokens in the frontend are changed (new colors, typography updates, spacing scale modifications, component library config changes), `docs/UI-DESIGN.md` SHALL be reviewed and updated to match.

#### Scenario: Frontend token change lands without a doc update
- **WHEN** a change that alters `globals.css` CSS custom properties, `tailwind.config.js` theme extensions, or `components.json` configuration is merged
- **THEN** `docs/UI-DESIGN.md` is reviewed as part of that change and updated if it no longer accurately reflects the frontend tokens

### Requirement: UI design document is distinct from engineering design document
The UI design document at `docs/UI-DESIGN.md` SHALL focus exclusively on visual identity (design tokens, patterns, component styling) and SHALL NOT duplicate the engineering architecture content in `docs/SYSTEM-DESIGN.md`.

#### Scenario: Reader needs engineering architecture
- **WHEN** a contributor opens `docs/UI-DESIGN.md` looking for system architecture, API design, or deployment information
- **THEN** the document SHALL direct them to `docs/SYSTEM-DESIGN.md` for engineering architecture content
