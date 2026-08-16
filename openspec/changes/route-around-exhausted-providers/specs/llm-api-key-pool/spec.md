## ADDED Requirements

### Requirement: Learned credential unavailability MUST outlive the request that learned it

When a credential is refused for a reason that will still hold on the next request — a rate limit, an exhausted quota, a rejected key — the system MUST record that beyond the lifetime of the process that observed it, and MUST apply what earlier requests recorded when selecting a credential. In a deployment where each request may run in a fresh process, knowledge held only in memory is discarded between requests, so every request pays the same refusal again and spends a unit of the very quota that is exhausted.

#### Scenario: A later request does not re-learn a refusal

- **GIVEN** an earlier request was refused by a credential for a reason that persists
- **WHEN** a later request runs in a process that observed nothing itself
- **THEN** that credential is not selected while the refusal is still expected to hold

#### Scenario: A recorded refusal expires on its own

- **GIVEN** a credential was recorded as unavailable
- **WHEN** the recorded time has passed
- **THEN** the credential is selectable again without any explicit clearing step

#### Scenario: Recording is scoped as narrowly as the limit is

- **GIVEN** a limit applies to one credential and model combination rather than to the credential as a whole
- **WHEN** that limit is recorded
- **THEN** the same credential remains selectable for a different model

### Requirement: Recovery time MUST come from the provider's own hint when it gives one

When a provider states when to retry, the system MUST use that instead of a fixed duration, because a constant is wrong in both directions: it withholds a credential that has already recovered, and it re-attempts one whose limit lasts far longer. A stated hint MUST be clamped to a maximum, so that an implausible or hostile value cannot withhold a credential for an unbounded period, and a missing hint MUST fall back to the existing default duration.

#### Scenario: A short hint is honored

- **GIVEN** a provider states that the limit clears in a few seconds
- **WHEN** a later request selects a credential
- **THEN** that credential is available again after the stated time rather than after the default duration

#### Scenario: A long hint is capped

- **GIVEN** a provider states a retry time beyond the allowed maximum
- **WHEN** the refusal is recorded
- **THEN** the recorded time is the maximum, so the credential is retried periodically instead of being withheld indefinitely

#### Scenario: No hint falls back to the default

- **WHEN** a refusal carries no usable retry hint
- **THEN** the default cooldown duration applies, as before

### Requirement: The shared record MUST NOT become a way for the feature to fail

Reading or writing the shared record MUST NOT fail a request, delay it beyond a short bound, or require the record's storage to exist. When the storage is unavailable, unreachable, or slow, the system MUST behave as it does with in-process knowledge alone. Recorded values MUST NOT include credential secrets.

#### Scenario: Missing storage behaves as before

- **GIVEN** the storage for shared availability does not exist
- **WHEN** a request selects credentials and later observes a refusal
- **THEN** the request succeeds or fails exactly as it would with in-process knowledge only

#### Scenario: Slow storage does not delay generation

- **WHEN** reading shared availability takes longer than its bound
- **THEN** the request proceeds without it rather than waiting

#### Scenario: Secrets are not stored

- **WHEN** a refusal is recorded for a credential
- **THEN** the record identifies the credential without containing the credential itself
