# Reconcile Reconciliation Design

This document describes the reconciliation behavior currently implemented in
Reconcile.

## Current implementation status

Reconcile currently supports exact reconciliation and fuzzy reconciliation.

Exact reconciliation matches imported bank transactions to ledger cash
movements using exact signed integer cents and exact transaction dates.

Fuzzy reconciliation adds configurable amount tolerance, date windows,
description scoring, duplicate penalties, candidate scoring, and ambiguity
handling.

Split reconciliation is still future work.

## Bank transaction sign convention

Imported bank transactions use the bank-sign convention:

```text
Deposit or inflow = positive
Withdrawal or outflow = negative
```

Examples using fake/demo data only:

```text
Owner deposit: +500000 cents
Software payment: -5000 cents
```

Money uses integer cents.

## Ledger cash movement rules

Ledger cash movements are derived from journal lines that touch the selected
cash account.

Rules:

- Debit to Cash becomes a positive ledger cash movement.
- Credit to Cash becomes a negative ledger cash movement.
- Non-cash journal lines are not bank-comparable cash movements.
- Ledger cash movement records include journal entry and line references.

## Exact reconciliation

Exact reconciliation matches one bank transaction to one ledger cash movement
only when:

- The signed amount cents match exactly.
- The bank transaction date equals the ledger entry date.
- The bank transaction is not duplicate-flagged.
- The ledger cash movement has not already been consumed in the same run.

Exact auto-matches create reconciliation match rows and ledger-link rows.

Unmatched and candidate records do not create ledger-link rows.

## Fuzzy reconciliation

Fuzzy reconciliation evaluates one bank transaction against one ledger cash
movement at a time.

It considers a ledger movement only when:

- The bank amount and ledger amount have the same sign.
- The amount delta is within the configured amount tolerance.
- The date delta is within the configured date window.
- The ledger movement has not already been consumed by an auto-match.

Fuzzy reconciliation does not implement split matching.

## Fuzzy scoring formula

Fuzzy candidate scoring uses this formula:

```text
score = amount_score * 0.60
      + date_score * 0.25
      + description_score * 0.15
      - duplicate_penalty
```

Final scores are clamped between 0.0 and 100.0.

## Amount scoring

Amount scoring uses signed integer cents.

- Exact same amount scores 100.0.
- Opposite signs score 0.0.
- Amounts outside the configured tolerance score 0.0.
- Amounts within tolerance receive a partial score.
- Smaller amount deltas score higher than larger amount deltas.

The default fuzzy amount tolerance is 5 cents.

## Date scoring

Date scoring compares the bank transaction date to the ledger entry date.

- Exact same date scores 100.0.
- Dates outside the configured date window score 0.0.
- Dates inside the date window receive a partial score.
- Smaller date deltas score higher than larger date deltas.

The default fuzzy date window is 3 days.

## Description scoring

Description scoring uses deterministic standard-library text normalization.

The implementation lowercases descriptions, removes simple punctuation
differences, collapses repeated whitespace, and compares token overlap.

- Missing descriptions score 0.0.
- Exact normalized descriptions score 100.0.
- Partial token overlap receives partial credit.
- No token overlap scores 0.0.

Description scoring can improve ranking, but it cannot override an invalid
amount candidate because candidates outside the amount tolerance are not
considered.

## Duplicate penalty behavior

Duplicate-flagged bank transactions receive a score penalty.

Duplicate-flagged bank transactions cannot be auto-matched by fuzzy
reconciliation. They may become candidate, ambiguous, or unmatched records,
but they are not linked to ledger movements automatically.

## Fuzzy decision thresholds

Default thresholds:

```text
auto_match_threshold = 95.0
candidate_threshold = 80.0
ambiguity_gap = 10.0
```

Decision rules:

```text
top score >= auto_match_threshold
and gap between top and second candidate >= ambiguity_gap
and bank transaction is not duplicate-flagged:
    auto_matched

top score >= auto_match_threshold
and second candidate is too close:
    ambiguous

candidate_threshold <= top score < auto_match_threshold:
    candidate

top score < candidate_threshold:
    unmatched

no candidates:
    unmatched
```

## Ledger-link behavior

Only auto-matched records create rows in
`reconciliation_match_ledger_links`.

Candidate, ambiguous, and unmatched rows do not create ledger-link rows.

## One-to-one safety

A ledger cash movement can be consumed by at most one fuzzy auto-match in the
same reconciliation run.

Candidate and ambiguous records do not consume ledger movements.

## Explanation storage

Every reconciliation match stores JSON explanation data.

Fuzzy explanations include:

- Candidate score.
- Amount score.
- Date score.
- Description score.
- Amount delta in cents.
- Date delta in days.
- Duplicate penalty.
- Decision status.
- Whether the record was auto-matched.
- Reason text.
- Top candidate summary.
- Near candidate summary when applicable.

## Mutation safety

Fuzzy reconciliation writes only to reconciliation tables:

- `reconciliation_runs`
- `reconciliation_matches`
- `reconciliation_match_ledger_links`

It does not append ledger events.

It does not modify bank transaction rows.

It does not modify accounting projection tables.

## Future work

The following reconciliation features are not implemented yet:

- Split reconciliation matching.
- Manual confirmation and rejection workflow.
- Reconciliation review UI.
- CSV export of reconciliation results.
- Cash flow reporting.
