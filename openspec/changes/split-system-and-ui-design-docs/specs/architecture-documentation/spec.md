# architecture-documentation Specification

## MODIFIED Requirements

### Requirement: Maintain a current-architecture design document
The project SHALL maintain a Google-style **engineering** design document at `docs/SYSTEM-DESIGN.md` describing the current (as-built) system architecture (not a UI/visual design-system document — that is covered separately in `docs/UI-DESIGN.md`). The document SHALL cover, at minimum: context and goals, a system overview, and a detailed design covering components, the data model, the API surface, and deployment. System overview diagrams SHALL use Mermaid syntax for maintainability.

#### Scenario: Design document exists and describes the current system
- **WHEN** a contributor opens `docs/SYSTEM-DESIGN.md`
- **THEN** it describes the architecture of the system as currently implemented (not a proposed or future architecture), organized into clearly labeled sections covering context/goals, system overview, and detailed design (components, data model, API, deployment)

#### Scenario: Design document distinguishes current state from proposed changes
- **WHEN** an architecture change is under active proposal (e.g. an in-progress OpenSpec change) but has not yet been implemented
- **THEN** `docs/SYSTEM-DESIGN.md` SHALL describe only the currently implemented architecture, and MAY reference the proposed change as future work without describing it as already built

#### Scenario: Reader needs UI visual-identity information
- **WHEN** a contributor opens `docs/SYSTEM-DESIGN.md` looking for design tokens, color palette, typography, or component styling information
- **THEN** the document SHALL direct them to `docs/UI-DESIGN.md` for UI visual-identity content

### Requirement: Keep the design document in sync with architecture changes
Whenever a change to the project's architecture is implemented (new deployment target, database/persistence backend swap, new or removed external service dependency, new major component, or similar), `docs/SYSTEM-DESIGN.md` SHALL be reviewed and updated to match, mirroring the maintenance expectation already established for `AGENTS.md`.

#### Scenario: Architecture change lands without a design doc update
- **WHEN** a change that alters the system's architecture (e.g. swapping the database backend, changing the deployment target, or adding/removing an external service dependency) is merged
- **THEN** `docs/SYSTEM-DESIGN.md` is reviewed as part of that change and updated if it no longer accurately reflects the system, so it does not silently go stale

#### Scenario: Known inconsistencies are documented rather than hidden
- **WHEN** the current codebase contains a known inconsistency between documented intent and actual behavior (for example, a configuration mismatch already flagged in `AGENTS.md`)
- **THEN** `docs/SYSTEM-DESIGN.md` SHALL note the inconsistency as a known caveat rather than presenting an idealized architecture that does not match reality
