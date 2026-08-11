## Purpose

MJAIフロントエンドで使用するMaterial Design 3インスパイアードなデザイントークン（カラー、タイポグラフィ、スペーシング、ボーダーラディウス）を定義し、一貫したビジュアル言語を確立する。

## ADDED Requirements

### Requirement: Semantic Color Token System
The system SHALL provide a semantic color token system using CSS custom properties with MD3-style naming conventions (primary, on-primary, surface, surface-container-*, outline-variant, error, tertiary, etc.).

#### Scenario: Color tokens are available via Tailwind utilities
- **WHEN** a component uses Tailwind color classes (e.g., `bg-surface`, `text-on-primary`)
- **THEN** the classes resolve to the defined CSS custom property values

#### Scenario: Color tokens support light mode
- **WHEN** the document is in light mode (default)
- **THEN** all semantic color tokens SHALL resolve to their light-mode HSL values

### Requirement: Typography Scale
The system SHALL provide a named typography scale using Inter font with the following text styles: headline-lg, headline-md, body-base, body-sm, metadata, label-caps.

#### Scenario: Typography styles are applied via Tailwind utilities
- **WHEN** a component uses typography classes (e.g., `text-headline-lg`, `text-body-sm`)
- **THEN** the element SHALL have the correct font-size, line-height, letter-spacing, and font-weight for that style

#### Scenario: Typography token font-weight is explicit
- **GIVEN** the typography token definitions in `tailwind.config.js`
- **THEN** each token SHALL include an explicit `fontWeight` value:
  - `headline-lg`: 700 (bold)
  - `headline-md`: 600 (semibold)
  - `body-base`: 400 (normal)
  - `body-sm`: 400 (normal)
  - `metadata`: 500 (medium)
  - `label-caps`: 600 (semibold)

#### Scenario: Inter font is loaded
- **WHEN** the application loads
- **THEN** the Inter font family SHALL be available via Google Fonts or local hosting

### Requirement: Spacing Scale
The system SHALL provide named spacing tokens: container-margin (1.5rem), card-gap (1.25rem), gutter (1rem), section-padding (2rem).

#### Scenario: Spacing tokens are usable in Tailwind
- **WHEN** a component uses spacing classes (e.g., `p-section`, `gap-card`)
- **THEN** the spacing value SHALL match the defined token value

### Requirement: Border Radius Scale
The system SHALL provide a border radius scale with values: DEFAULT (0.25rem), lg (0.5rem), xl (0.75rem), full (9999px for pill shapes).

#### Scenario: Border radius tokens are applied correctly
- **WHEN** a component uses radius classes (e.g., `rounded-lg`, `rounded-xl`, `rounded-full`)
- **THEN** the border-radius value SHALL match the defined token value

### Requirement: Session Status Colors
The system SHALL provide semantic colors for session status indicators: session-active (blue, e.g., #2563EB), session-complete (green, e.g., #16A34A), session-empty (gray, e.g., #64748B).

#### Scenario: Session status colors are available
- **WHEN** a session card displays a status pill
- **THEN** the pill background color SHALL use the appropriate session-status color token
