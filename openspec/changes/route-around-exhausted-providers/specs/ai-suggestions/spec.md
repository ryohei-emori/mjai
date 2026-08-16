## ADDED Requirements

### Requirement: A provider known to be unavailable MUST be skipped rather than called

When every credential a provider could use is already known to be refused, the system MUST skip that provider and move to the next one in preference order, rather than calling it to be told again. Skipping MUST NOT change the preference order among the providers that remain: the provider that produces the best critique stays first whenever it is usable, so this reduces waiting and wasted quota without silently lowering output quality.

#### Scenario: An exhausted primary is not called

- **GIVEN** every credential of the preferred provider is known to be rate-limited or exhausted
- **WHEN** a suggestion is generated
- **THEN** no request is sent to that provider, and the next provider in preference order is used

#### Scenario: Preference order is preserved among usable providers

- **GIVEN** a provider later in the chain answers faster than the preferred one
- **WHEN** both are usable
- **THEN** the preferred provider is still used first

#### Scenario: A partially exhausted provider is still used

- **GIVEN** some but not all of a provider's credentials are known to be refused
- **WHEN** that provider is called
- **THEN** a credential that is not known to be refused is used

### Requirement: The system MUST always make one real attempt

The system MUST NOT conclude that generation is impossible from recorded availability alone. When every provider appears unavailable, it MUST still attempt the one whose availability is expected to return soonest. Records describe the past and can be stale or wrong, so treating them as authoritative would let a single bad record take the feature offline for as long as that record lasts.

#### Scenario: Everything looks unavailable

- **GIVEN** every configured provider is recorded as unavailable
- **WHEN** a suggestion is generated
- **THEN** one attempt is still made, against the provider whose recorded unavailability ends soonest

#### Scenario: A stale record cannot disable generation

- **GIVEN** a recorded unavailability that no longer reflects the provider's actual state
- **WHEN** the attempt that record would have prevented succeeds
- **THEN** the result is returned normally

### Requirement: Availability knowledge MUST NOT add cost or risk to the generation path

Consulting recorded availability MUST NOT add a round trip to a request that already queries stored configuration, MUST be bounded so it cannot consume the generation budget, and MUST NOT introduce a failure the request would not otherwise have. Recording an observation MUST be skipped rather than allowed to push a request past its deadline.

#### Scenario: No additional round trip

- **WHEN** a generation request reads both its stored configuration and recorded availability
- **THEN** it does so without opening more connections than reading configuration alone required

#### Scenario: Recording does not overrun the deadline

- **GIVEN** a refusal is observed with little of the request budget left
- **WHEN** the request finishes
- **THEN** it does not exceed its deadline in order to record the observation

### Requirement: A skip for a known limit MUST be distinguishable from a missing configuration

The per-provider failure breakdown MUST state which kind of unavailability applied — not configured, refused and expected to recover at a stated time, or skipped for lack of remaining time — because the operator action differs for each and guessing between them requires server logs.

#### Scenario: Breakdown names a learned limit and its recovery time

- **GIVEN** a provider was skipped because its credentials are recorded as rate-limited
- **WHEN** the failure is reported
- **THEN** the breakdown says the limit was already known and when the provider is expected to be usable again

#### Scenario: Breakdown still distinguishes an unset credential

- **GIVEN** a provider has no credentials configured
- **WHEN** the failure is reported
- **THEN** the breakdown says it is not configured, not that it is rate-limited
