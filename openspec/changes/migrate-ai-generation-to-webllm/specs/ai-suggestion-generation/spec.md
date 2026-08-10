## Purpose

Generates AI-based correction suggestions for a Japanese-Chinese (or Chinese-Japanese) translation attempt by running LLM inference entirely client-side in the user's authenticated browser session via WebLLM, comparing an original text against a target (translated) text and returning a list of pointed-out issues plus an overall comment, without any server-side model call.

## ADDED Requirements

### Requirement: Client-Side Model Loading and Initialization
The system SHALL load and initialize a WebLLM model entirely within the authenticated user's browser session before any suggestion generation is attempted, and SHALL NOT send `originalText`/`targetText` content to any server-side AI/model endpoint. The system SHALL present progress feedback to the user while the model is downloading/initializing, and SHALL cache the loaded model in the browser so that subsequent suggestion requests in the same session do not require re-downloading it.

#### Scenario: First-time model load shows progress
- GIVEN an authenticated user with no WebLLM model yet loaded in the browser
- WHEN the user requests AI correction suggestions
- THEN the system begins downloading/initializing the model and displays progress feedback to the user until it is ready

#### Scenario: Subsequent generation reuses the cached model
- GIVEN an authenticated user whose browser already has a WebLLM model loaded from earlier in the same session
- WHEN the user requests AI correction suggestions again
- THEN the system reuses the already-loaded model without re-downloading it before generating suggestions

### Requirement: In-Browser Suggestion Generation
The system SHALL generate correction suggestions by running inference on the loaded WebLLM model entirely within the browser, given the current `originalText`, `targetText`, and an optional instruction, and SHALL produce a result consisting of a list of suggestions (each with an identifier, an `original` excerpt, and a `reason`) and an `overallComment`, matching the shape the correction workspace UI already consumes.

#### Scenario: Generating suggestions from an original/target pair
- GIVEN an authenticated user with a loaded WebLLM model and a given `originalText`/`targetText` pair
- WHEN the user requests suggestions
- THEN the system runs in-browser inference and returns a list of correction suggestions and an overall comment derived from that input
- AND no network call is made to a suggestion-generation backend endpoint

#### Scenario: Optional instruction influences generation
- GIVEN an authenticated user supplies an optional instruction alongside `originalText` and `targetText`
- WHEN the system builds the in-browser generation prompt
- THEN the constructed prompt incorporates that instruction

### Requirement: Unsupported Browser/Device Fallback
WHEN the user's browser or device does not support WebGPU, or WebLLM model loading/initialization otherwise fails, the system SHALL NOT crash or block the rest of the correction workflow. Instead, it SHALL present a clear, non-blocking message indicating that in-browser AI suggestions are unavailable in the current environment, and SHALL still allow the user to manually add custom correction proposals.

#### Scenario: WebGPU is unavailable
- GIVEN an authenticated user on a browser/device without WebGPU support
- WHEN the user requests AI correction suggestions
- THEN the system does not attempt to load the WebLLM model and instead shows a message that in-browser AI suggestions are unavailable
- AND the user can still create and submit custom correction proposals manually

#### Scenario: Model load fails unexpectedly
- GIVEN WebGPU is reported as supported but WebLLM model download/initialization fails or errors
- WHEN the user requests AI correction suggestions
- THEN the system surfaces a non-blocking error state indicating AI suggestions could not be generated in this session
- AND the rest of the correction workspace remains usable

### Requirement: Unchanged Downstream Persistence
The system SHALL persist correction suggestions the user selects, edits, or authors exactly as today: via the existing `POST /proposals` endpoint, unchanged by the move to client-side generation. Suggestion generation SHALL be decoupled from persistence — a suggestion produced by in-browser inference SHALL be submitted through the same proposal-creation flow as a manually authored custom correction.

#### Scenario: Selecting an AI-generated suggestion persists it via the existing endpoint
- GIVEN an authenticated user has a suggestion produced by in-browser WebLLM inference
- WHEN the user selects and confirms that suggestion
- THEN the system submits it to `POST /proposals` using the same request shape already used for existing (`AI` or `Custom` type) proposals

### Requirement: Authentication Precondition
The system SHALL only attempt WebLLM model loading and in-browser suggestion generation when the user has an authenticated session (as established by the separate Google authentication flow). The system SHALL NOT attempt to load a model or generate suggestions for an unauthenticated user.

#### Scenario: Unauthenticated user cannot trigger generation
- GIVEN a user without an authenticated session
- WHEN the user attempts to request AI correction suggestions
- THEN the system does not initiate WebLLM model loading or in-browser generation

### Requirement: Server-Side Generation Removal
The system SHALL NOT expose any server-side HTTP endpoint that generates AI correction suggestions (including any Gemini-backed or mock-backed generation path), and the backend SHALL NOT read or depend on a Gemini API key or Gemini model configuration for suggestion generation. All suggestion generation SHALL occur exclusively within the client's browser via WebLLM.

#### Scenario: No server-side suggestion-generation endpoint exists
- GIVEN the backend application as deployed after this change
- WHEN a client sends a request attempting to generate AI correction suggestions server-side (e.g., the previously existing `POST /suggestions` route)
- THEN the backend does not provide any such endpoint
- AND no server-side code path calls an external LLM API (Gemini or otherwise) to produce correction suggestions

#### Scenario: Backend has no Gemini configuration
- GIVEN the backend application starts after this change
- WHEN its configuration/environment is read
- THEN it does not read or depend on a `GEMINI_API_KEY` or `GEMINI_MODEL` environment variable for suggestion generation
