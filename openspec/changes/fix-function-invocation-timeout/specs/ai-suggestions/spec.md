## ADDED Requirements

### Requirement: A suggestion request MUST NOT be able to outlive the platform function limit

The system MUST NOT start an outbound provider call that cannot finish inside the request's remaining wall-clock budget. Sizing each call to the time that is actually left is required, not optional: a check that only asks whether the deadline has already passed permits a call whose own timeout runs well beyond it, which the platform answers with an opaque function timeout carrying none of the system's own diagnostics. The per-attempt limit MUST be a ceiling on the whole attempt, so that a transport whose timeout applies per operation cannot exceed it, and MUST be re-evaluated before every attempt, including retries against a sibling model and attempts with further pooled credentials.

#### Scenario: A call is granted only the time that remains

- **GIVEN** less of the request budget remains than a provider's own timeout
- **WHEN** that provider is called
- **THEN** the call is limited to the remaining budget rather than to the provider's timeout

#### Scenario: Every provider spends its whole slice and the request still fits

- **GIVEN** all providers are configured and each one consumes every second it is granted before failing
- **WHEN** the failover chain runs, including in-provider sibling retries
- **THEN** the total elapsed time stays within the request budget, and therefore within the platform limit

#### Scenario: Pooled credentials share one budget

- **GIVEN** a provider has several credentials loaded
- **WHEN** each credential's attempt fails and the next is tried
- **THEN** the attempts together stay inside the provider's share of the budget, rather than each receiving the provider's full timeout

### Requirement: A provider with too little remaining time MUST be skipped rather than started

Each provider declares the minimum time in which it can plausibly answer, based on measured latency. When less than that remains, the system MUST skip the provider instead of starting a call that would time out, because those seconds are needed by the faster providers later in the chain.

#### Scenario: Slice shorter than the provider needs

- **WHEN** the remaining budget is below a provider's minimum useful time
- **THEN** no call is made to that provider and the reason names the provider and the time that was left

#### Scenario: A skipped provider does not discard an existing body

- **GIVEN** an earlier provider produced a body that failed a content check
- **WHEN** the remaining providers are skipped for lack of budget
- **THEN** that body is returned rather than a failure

### Requirement: A slow provider MUST NOT consume the turn of the providers after it

The budget given to one provider MUST be short of the request deadline by what the providers still to come need in order to answer. This MUST be enforced against the clock before each attempt rather than predicted before the provider's first attempt, since a prediction cannot know how long that attempt will take.

#### Scenario: Primary times out twice and the secondary still answers

- **GIVEN** the primary provider exhausts its phase across two model attempts
- **WHEN** the chain falls over to the secondary
- **THEN** the secondary is still granted enough time to answer, and does

#### Scenario: Reserve covers only providers that are configured and still to come

- **WHEN** a provider's phase budget is computed
- **THEN** time is held back only for configured providers later in the chain, and the last provider in the chain gets the whole remaining budget

### Requirement: The request budget MUST cover the whole request and leave the platform its overhead

The wall-clock budget MUST be derived from the platform function limit with an explicit reserve for work that counts against that limit but cannot be measured inside the handler — cold start, authentication, and request/response transfer — and MUST be measured from when the request arrived rather than from the first provider call. The derivation MUST be verifiable against the deployed function configuration.

#### Scenario: Work before generation counts against the budget

- **WHEN** the request spends time on authentication and the stored-prompt lookup before generation starts
- **THEN** that time is already deducted from the budget the provider calls are sized against

#### Scenario: Budget and reserve reconcile with the deployed limit

- **WHEN** the deployed function's maximum duration is compared with the configured budget and reserve
- **THEN** they agree, so a change to one is caught rather than silently shrinking the reserve

### Requirement: A failure caused by the budget MUST be reported as a timeout

When the chain fails and any provider was skipped for lack of time, or was granted less than its own timeout, the failure MUST be marked as a timeout so the user is advised to retry rather than to check provider configuration. When the platform itself terminates the request, the interface MUST explain that in the interface language rather than showing the platform's raw error identifier.

#### Scenario: Clamped providers that fail report a timeout

- **WHEN** every provider fails after being granted less time than its own timeout
- **THEN** the failure is reported as a timeout, not only as a provider outage

#### Scenario: Platform-terminated request is explained

- **WHEN** the response is a platform-level function timeout with no application error body
- **THEN** the user reads an interface-language explanation that the server's time limit was reached, not the raw platform identifier

### Requirement: A database outage MUST NOT be reported as a platform timeout

Database connections and statements MUST be bounded well inside the platform function limit, so that an unreachable or paused database produces a fast, legible error instead of a function timeout that says nothing about the cause.

#### Scenario: Unreachable database fails fast

- **WHEN** the database cannot be reached
- **THEN** the request fails within the connection bound, rather than hanging until the platform terminates the function
