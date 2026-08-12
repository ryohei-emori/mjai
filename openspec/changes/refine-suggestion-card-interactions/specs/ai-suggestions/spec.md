## ADDED Requirements

### Requirement: Retry on non-Chinese reason/overallComment content

The system SHALL detect when a successfully-parsed suggestion response violates the bilingual field-content rule (`reason` on any suggestion, or `overallComment`, written in Japanese instead of the required Simplified Chinese) by checking for the presence of Hiragana (U+3040–U+309F) or Katakana (U+30A0–U+30FF) codepoints in those fields — a reliable signal that the text is Japanese rather than Chinese, since Chinese text contains neither script. WHEN this condition is detected, the system SHALL retry suggestion generation, composing with (not replacing) the existing JSON-parse-failure retry axis and bounded by the same `MAX_PARSE_RETRY_ATTEMPTS` total attempts. WHEN every attempt still fails this check, the system SHALL return the last generated result rather than raising an error, consistent with the existing parse-failure degrade-gracefully behavior. The `original` field is exempt from this check and SHALL remain unvalidated for language content, since it is required to stay in Japanese.

#### Scenario: A suggestion's reason contains Hiragana or Katakana

- **WHEN** a generated suggestion's `reason` field contains any Hiragana or Katakana codepoint
- **THEN** the system treats this attempt as failing the language check and retries generation, provided the retry budget is not yet exhausted

#### Scenario: The overallComment contains Hiragana or Katakana

- **WHEN** a generated response's `overallComment` field contains any Hiragana or Katakana codepoint
- **THEN** the system treats this attempt as failing the language check and retries generation, provided the retry budget is not yet exhausted

#### Scenario: A pure-Chinese response passes the check on the first attempt

- **WHEN** every suggestion's `reason` and the `overallComment` contain only Chinese (Hanzi/CJK ideograph) text, Japanese `original` content, or other non-Hiragana/Katakana characters
- **THEN** the system does not retry on the language-check axis and returns that result

#### Scenario: Retry axis composes with the existing JSON-parse-failure retry

- **WHEN** an attempt succeeds at JSON parsing but fails the Chinese-language check, or fails JSON parsing outright
- **THEN** both conditions consume the same shared `MAX_PARSE_RETRY_ATTEMPTS` attempt budget rather than each having an independent budget

#### Scenario: All attempts still fail the language check

- **WHEN** every attempt within the retry budget still has a non-Chinese `reason` or `overallComment`
- **THEN** the system gives up and returns the last generated result rather than raising an error

#### Scenario: The original field is not checked for language

- **WHEN** a suggestion's `original` field contains Hiragana or Katakana (as expected, since it must stay Japanese)
- **THEN** this does not count as a language-check failure and does not trigger a retry

### Requirement: Blank suggestion items are filtered out, not surfaced

The system SHALL drop a parsed suggestion item from the result when, after stripping leading/trailing whitespace, both its `original` and `reason` fields are empty, instead of including it as a blank entry. After filtering, the system SHALL re-sequence the remaining items' `id` fields contiguously starting from `"1"` so there is no gap left by a dropped item.

#### Scenario: A fully-blank item is dropped

- **WHEN** the model's response includes an item whose `original` and `reason` are both empty or whitespace-only after stripping
- **THEN** that item does not appear in the parsed `suggestions` list

#### Scenario: Remaining item ids stay contiguous after filtering

- **WHEN** a blank item occurs between two non-blank items in the model's raw response (e.g. items 1, 2-blank, 3)
- **THEN** the parsed result contains the two non-blank items with contiguous ids `"1"` and `"2"`, with no gap or reference to the dropped item's original position

#### Scenario: No blank items present is unaffected

- **WHEN** every item in the model's response has a non-empty `original` or `reason`
- **THEN** all items are retained with the same sequential `id` assignment as before this change
