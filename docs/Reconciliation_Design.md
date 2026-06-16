# Reconcile Reconciliation Design

This document defines the planned bank reconciliation design. Step 0 does not implement reconciliation yet.

## Bank transaction sign convention

Imported bank transactions will use the bank-sign convention:

```text
Deposit or inflow = positive
Withdrawal or outflow = negative
```

Examples using fake/demo data only:

```text
Owner deposit: +500000 cents
Software payment: -5000 cents
```

Money will use integer cents.

## Ledger cash movement rules

Ledger cash movements are planned to be derived from journal lines that touch the selected cash account.

Rules:

- Debit to Cash becomes a positive ledger cash movement.
- Credit to Cash becomes a negative ledger cash movement.
- Non-cash journal lines are not bank-comparable cash movements.
- Ledger cash movement records should include the journal entry and line references.

## Exact matching plan

Exact matching will run before fuzzy matching.

A planned exact match requires:

- Same amount in cents.
- Same sign.
- Same date, or a clearly configured exact-like date tolerance.
- Unmatched bank transaction.
- Unmatched ledger cash movement.

Exact matches should still store or return an explanation.

## Fuzzy matching plan

Fuzzy matching will score candidates using amount, date, description, and duplicate information.

Amount should matter most. Description similarity should not override a poor amount match.

Default planned scoring:

```text
score = amount_score * 0.60
      + date_score * 0.25
      + description_score * 0.15
      - duplicate_penalty
```

Default planned thresholds:

```text
score >= 95 and score gap >= 10:
    auto_matched

80 <= score < 95:
    candidate

score >= 95 but top candidates are close:
    ambiguous

score < 80:
    unmatched
```

Default planned date window:

```text
3 days before/after
```

Default planned amount tolerance:

```text
1 cent for exact-like matching
5 cents for configurable fuzzy tolerance
```

## Duplicate handling

Duplicate imported bank transactions will be flagged, not deleted.

Planned duplicate signals:

- Same external ID where available.
- Same date, amount, and normalized description.
- Same row hash.

Duplicate records should include a duplicate group ID or explanation where useful.

## Split matching constraints

Split matching will support one bank transaction matched to two or three ledger cash movements.

Planned constraints:

- Only combine two or three ledger movements.
- Only combine same-sign movements.
- Only combine unmatched movements.
- Only search within the date window.
- Only accept combinations that sum to the bank amount within tolerance.
- Do not implement unlimited subset-sum search in the MVP.

Default planned split scoring:

```text
score = amount_score * 0.70
      + date_score * 0.25
      + description_score * 0.05
      - split_penalty
```

## Ambiguity handling

Ambiguous matches are not auto-confirmed.

A match should be marked ambiguous when:

- Two or more candidates have close scores.
- Two or more candidates can explain the same bank transaction equally well.
- A split and a single match both look plausible.
- Duplicate bank rows make the result unsafe.

Ambiguous results should be presented for review with explanations.

## Match scoring formula

The MVP scoring plan is:

```text
score = amount_score * 0.60
      + date_score * 0.25
      + description_score * 0.15
      - duplicate_penalty
```

Component expectations:

- `amount_score` should strongly reward exact amount matches.
- `date_score` should reward nearby dates within the configured window.
- `description_score` should help ranking but should not dominate.
- `duplicate_penalty` should reduce confidence for flagged duplicate bank rows.

## Explanation requirements

Every reconciliation decision should store or display why it was made.

Planned explanation fields:

- Match type.
- Match status.
- Amount delta in cents.
- Date delta in days.
- Amount score.
- Date score.
- Description score.
- Duplicate penalty, if any.
- Final score.
- Reason for auto-match, candidate, ambiguous, rejected, or unmatched status.
- Linked ledger movement IDs, if applicable.

The goal is not just to match transactions. The goal is to make the match reviewable.
