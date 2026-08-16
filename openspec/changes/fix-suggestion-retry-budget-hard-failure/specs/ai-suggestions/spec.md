## ADDED Requirements

### Requirement: A generated critique MUST NOT be downgraded into a failed request by content retries

Once any pass has produced a parsed body, the system MUST return that body rather than raising, even when a later content-quality retry pass cannot complete — whether because every provider failed in that pass or because the wall-clock budget is exhausted. A hard cloud failure (HTTP 503) MUST be reserved for the case where no pass produced a body at all. The system MUST also distinguish a wall-clock abort from a provider outage in the failure it reports, since the two need different advice.

#### Scenario: Providers fail during a retry pass

- **GIVEN** an earlier pass produced a body that failed only a content check
- **WHEN** a retry pass gets no usable HTTP body from any provider
- **THEN** the earlier body is returned with its provider and model, instead of a 503

#### Scenario: Wall-clock budget runs out during a retry pass

- **GIVEN** an earlier pass produced a body that failed only a content check
- **WHEN** the wall-clock budget is exhausted before a later pass can finish
- **THEN** the earlier body is returned instead of a 503

#### Scenario: Budget runs out mid-pass after the primary answered

- **GIVEN** the primary provider returned a body that failed a content check
- **WHEN** the wall-clock budget is exhausted before the secondary provider is tried
- **THEN** the primary's body is returned and no further provider is called

#### Scenario: No body at all still fails loudly

- **WHEN** no pass produced any parsed body, because every configured provider failed or the budget ran out first
- **THEN** the request fails with the cloud-failure status, reporting each provider's error and loaded credential count

#### Scenario: A wall-clock abort is reported as such

- **WHEN** the failure is caused by the wall-clock budget rather than by every provider declining
- **THEN** the failure response marks it distinctly, and the user-facing message advises retrying rather than checking provider configuration

### Requirement: Retry passes MUST be bounded by the remaining budget and by an explicit cap for recommended-form faults

The system MUST NOT start a content-quality retry pass unless the remaining wall-clock budget still covers a pass as long as the one just measured. When the only content fault is a Chinese recommended form — a readable critique whose remaining flaw does not justify more latency or free-tier requests — the system MUST stop retrying after a bounded number of passes and accept the body. Parse failures and non-Chinese explanations keep the existing shared retry budget.

#### Scenario: A pass that cannot finish is not begun

- **GIVEN** the previous pass consumed most of the wall-clock budget
- **WHEN** the body still fails a content check
- **THEN** no further provider call is made and the best body so far is returned

#### Scenario: A persistent Chinese recommended form is accepted after the cap

- **WHEN** every pass returns a parseable Chinese critique that recommends a Chinese form
- **THEN** the number of passes spent is the cap plus the first pass, and that body is returned

### Requirement: A second in-provider model attempt MUST NOT crowd out the next provider

A provider that rotates models MAY retry once against a sibling model, but the failover chain MUST suppress that retry when the remaining wall-clock budget would not also leave the next configured provider room to answer within its timeout. A fresh secondary provider is a better use of the remaining budget than a sibling of the model that just failed, and the suppression also keeps the total request inside the platform function limit.

#### Scenario: Full budget allows the sibling model

- **WHEN** a provider call starts with enough budget for its own retry plus the next provider's timeout
- **THEN** the provider is allowed its second model attempt

#### Scenario: Tight budget suppresses the sibling model

- **WHEN** the remaining budget would not cover both the provider's retry and the next provider's timeout
- **THEN** the provider is called with its second model attempt disabled

### Requirement: A recommended form MUST NOT be reported as non-target-language when the same critique also gives a target-language form

The check that rejects a Chinese word offered as the corrected form MUST NOT fire on a reason that also introduces a Japanese recommended form, because critique prose narrates a meaning shift with the same verbs it uses to recommend one.

#### Scenario: Reason narrates a Chinese shift and recommends Japanese

- **WHEN** a reason quotes a Chinese word after a recommendation verb and also introduces a Japanese form as the correction
- **THEN** the body is not rejected for a non-target-language recommendation

### Requirement: A cloud suggestion failure MUST tell the user which provider declined and why

When cloud generation fails, the user-facing failure MUST include each provider's reported error together with the number of credentials that provider had loaded, for every provider in the chain including the primary. The explanatory text MUST be composed in the UI language from the machine-readable failure flags rather than forwarding the backend's operator-facing message. Rate-limit classification MUST consider the primary provider's error, and MUST NOT be derived from the raw response text, whose field names can match quota wording.

#### Scenario: Failure names every provider that declined

- **WHEN** cloud generation fails with per-provider errors in the response
- **THEN** the failed job and the notification both show each provider's name, loaded credential count, and reported error

#### Scenario: Failure text is in the UI language

- **WHEN** cloud generation fails with an operator-facing message in the response
- **THEN** the user reads a message in the interface language, chosen by whether the failure was rate-limited, a wall-clock abort, or a provider outage

#### Scenario: Primary-provider quota exhaustion is classified as rate-limited

- **WHEN** the only reported quota/cooldown error comes from the primary provider
- **THEN** the client classifies the failure as rate-limited

#### Scenario: Response field names are not mistaken for quota wording

- **WHEN** a failure response carries a rate-limit *flag* set to false and no quota wording in any message
- **THEN** the client does not classify the failure as rate-limited
