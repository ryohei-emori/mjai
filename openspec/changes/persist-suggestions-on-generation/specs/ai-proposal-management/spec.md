## ADDED Requirements

### Requirement: Persist Full Suggestion Set for Pending Histories
The system SHALL allow clients to create `ai_proposals` rows for a pending correction history immediately after generation, with `isSelected` defaulting to false, so another client can restore the full suggestion list without waiting for confirm/save. The system SHALL NOT store API keys or provider credentials in proposal rows.

#### Scenario: All generated suggestions stored under pending history
- **WHEN** a client creates one proposal per generated suggestion linked to a pending `historyId`, with `type` = `AI`, `originalAfterText` / `originalReason` from the model, and `isSelected` false
- **THEN** `GET /histories/{historyId}/proposals` returns the full set
- **AND** each proposal is available for right-pane restore on another environment sharing the same DB

### Requirement: Update Proposal Selection Metadata on Confirm
The system SHALL provide a way to update existing proposals' `isSelected`, `isModified`, `modifiedReason`, `selectedOrder`, and related flags when the user confirms a pending generation, without requiring delete-and-recreate of the entire proposal set for that history when those proposals already exist.

#### Scenario: Confirm updates selection flags in place
- **WHEN** a client updates proposals belonging to a pending history with the user's final selection and edited reasons
- **THEN** subsequent list responses reflect the updated flags and order
- **AND** no duplicate proposals are created for the same generation's original AI set solely due to confirm

#### Scenario: Custom proposals added at confirm time
- **WHEN** the user added custom proposals during review that were not present at generation persist time
- **THEN** the client MAY create additional `POST /proposals` rows for those customs under the same history
- **AND** existing AI proposals remain updated in place
