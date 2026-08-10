# ai-proposal-management Specification

## Purpose

The ai-proposal-management capability stores and retrieves individual correction proposals (AI-generated or custom) that belong to a CorrectionHistory, including flags and ordering metadata used to reconstruct which suggestions a user selected or modified.

## Requirements

### Requirement: List Proposals for a Correction History
The system SHALL expose `GET /histories/{history_id}/proposals` to retrieve all `AIProposals` rows associated with the given `history_id`, without validating that the parent CorrectionHistory exists.

#### Scenario: Proposals exist for the history
- GIVEN one or more `AIProposals` rows have `historyId` equal to the requested `history_id`
- WHEN a client sends `GET /histories/{history_id}/proposals`
- THEN the system returns HTTP 200 with a JSON array of proposal objects containing `proposalId`, `historyId`, `type`, `originalAfterText`, `originalReason`, `modifiedAfterText`, `modifiedReason`, `isSelected`, `isModified`, `isCustom`, and `selectedOrder`
- AND on the SQLite-backed path the array is ordered by `selectedOrder` ascending, with rows whose `selectedOrder` is NULL sorted first

#### Scenario: History has no proposals or does not exist
- GIVEN no `AIProposals` row has the requested `historyId`, including when `history_id` does not correspond to any existing CorrectionHistory
- WHEN a client sends `GET /histories/{history_id}/proposals`
- THEN the system returns HTTP 200 with an empty JSON array
- AND no 404 is returned, since the endpoint never checks for the existence of the parent CorrectionHistory before querying proposals

#### Scenario: Default backend query failure is not recovered
- GIVEN the `USE_POSTGRESQL` environment variable is unset or set to any value other than `"false"` (the default configuration)
- WHEN a client sends `GET /histories/{history_id}/proposals` and the underlying PostgreSQL/Supabase query raises an exception
- THEN the system logs the error and re-raises it, resulting in an unhandled exception and an HTTP 500 response
- AND no automatic fallback to the local SQLite `AIProposals` table occurs in this case

### Requirement: Create a Proposal Record
The system SHALL expose `POST /proposals`, accepting an untyped JSON request body (not a strict Pydantic model), to persist a single AI-generated or custom proposal, applying default values for optional fields and generating a `proposalId` when one is not supplied.

#### Scenario: Successful creation with SQLite backend
- GIVEN `USE_POSTGRESQL` is explicitly set to `"false"`
- WHEN a client sends `POST /proposals` with a JSON body containing at least `historyId`, `type`, and `originalAfterText`
- THEN the system inserts a row into the `AIProposals` table, defaulting `isSelected`, `isModified`, and `isCustom` to `0` and `selectedOrder` to `null` when they are not present in the request
- AND the system returns HTTP 200 with a JSON object echoing the persisted proposal, including a server-generated UUID `proposalId` when none was supplied in the request

#### Scenario: Missing required field
- GIVEN the JSON request body omits `historyId`, `type`, or `originalAfterText`
- WHEN a client sends `POST /proposals`
- THEN the system raises a `KeyError` while constructing the proposal record before any database call is made
- AND this exception is unhandled, resulting in an HTTP 500 response

#### Scenario: Default PostgreSQL backend is non-functional for proposal creation
- GIVEN `USE_POSTGRESQL` is unset or set to any value other than `"false"` (the default configuration)
- WHEN a client sends `POST /proposals` with an otherwise valid payload
- THEN the system attempts to insert into a legacy `ai_proposals` table using snake_case keys (`proposal_text`, `confidence_score`, `history_id`, `proposal_id`, `created_at`) that are absent from the camelCase proposal record built from the request
- AND this raises a `KeyError`, which is logged and re-raised, resulting in an HTTP 500 response regardless of the validity of the input payload

#### Scenario: No foreign key or enum validation on write
- GIVEN a request body whose `historyId` does not correspond to any existing CorrectionHistory, or whose `type` value is neither `"AI"` nor `"Custom"`
- WHEN a client sends `POST /proposals` with `USE_POSTGRESQL` set to `"false"`
- THEN the system persists the row without error, since neither the `historyId` relationship nor the `type` value is validated at the application or SQLite level

### Requirement: Proposal Selection, Modification, and Ordering Metadata
The system SHALL persist per-proposal flags distinguishing AI-generated proposals from custom ones (`type`, `isCustom`), tracking whether a proposal was selected and/or edited by the user (`isSelected`, `isModified`), and an optional selection order (`selectedOrder`), matching the `AIProposals` table defined in `backend/db/schema.sql`.

#### Scenario: Flags and order are stored as provided
- GIVEN a `POST /proposals` request includes explicit `isSelected`, `isModified`, `isCustom`, and `selectedOrder` values
- WHEN the proposal is persisted via the SQLite backend
- THEN the stored row reflects exactly the provided values for those fields, without additional transformation or clamping

#### Scenario: Flags default when omitted
- GIVEN a `POST /proposals` request omits `isSelected`, `isModified`, and/or `isCustom`
- WHEN the proposal is persisted via the SQLite backend
- THEN the system defaults each omitted flag to `0`
- AND defaults `selectedOrder` to `null` when it is omitted from the request
