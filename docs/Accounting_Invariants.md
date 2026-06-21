# Accounting Invariants

Reconcile uses example-based tests and property-based tests.

Example-based tests check known scenarios. For example, one test posts a
specific journal entry and verifies the expected account balance.

Property-based tests check general rules. Instead of testing one hand-written
journal entry, they generate many small fake ledgers and verify that accounting
laws still hold.

Reconcile uses Hypothesis for property-based tests.

## Why property tests matter here

Accounting engines are rule-heavy. A few hand-written examples can pass while a
hidden edge case still breaks the ledger.

Property tests help prove that important accounting rules keep working across
many generated combinations of accounts, amounts, entries, projection rebuilds,
and reversals.

The property tests use fake generated data only. They do not use real customer
data, real bank data, external services, randomness from `random`, or network
calls.

## Integer cents

Reconcile stores and calculates money as integer cents.

This avoids floating-point rounding problems. It also makes report totals,
reconciliation tolerances, and accounting invariants easier to test.

Example:

```text
$10.25 = 1025 cents
```

## Double-entry rule

Every journal entry must satisfy:

```text
Total debits = Total credits
```

A valid journal entry must also have at least two lines. Each line must use one
side, either debit or credit, and each line amount must be a positive integer
cent value.

Generated balanced journal entries validate successfully. Generated unbalanced
journal entries raise `ValidationError` and do not reach the event store.

## Normal balances

Account types have normal debit or credit balances:

- Assets: debit
- Expenses: debit
- Liabilities: credit
- Equity: credit
- Revenue: credit

Balance projections use those normal balances when converting debit and credit
activity into account balances.

## Expanded accounting equation

Before closing entries exist, Reconcile uses the expanded accounting equation:

```text
Assets + Expenses = Liabilities + Equity + Revenue
```

Property tests generate valid ledgers and verify that the equation still holds
after posting sequences of balanced entries.

## Trial balance invariant

For valid posted journal entries, the trial balance must balance:

```text
Ending debit balances = Ending credit balances
```

Example tests check specific ledgers. Property tests generate many valid ledgers
and verify that the trial balance remains balanced.

## Projection rebuild invariant

The event log is the source of truth for implemented ledger actions. Projection
tables are derived state.

The rebuild invariant is:

```text
Incremental projections = rebuilt projections from events
```

Property tests post generated ledgers, capture balances, rebuild projections by
replaying `ledger_events`, and verify that rebuilt balances and trial balances
match the original incremental state.

## Reversal invariant

Corrections use reversal entries instead of editing posted journal entries.

For a posted journal entry, reversing it should remove the net account-balance
impact while preserving the original activity and audit trail.

Property tests verify that:

- reversing a generated valid entry creates a linked reversal entry
- the original entry remains visible
- the reversal points back to the original entry
- the net balance impact is neutralized
- trial balance remains balanced after reversal
- rebuild after reversal restores the same state
- reversing the same entry twice raises `ValidationError`

## Deterministic replay

Events replay in `event_sequence` order. Given the same event list in the same
order, projection rebuild should produce the same state every time.

This protects the central event-sourcing promise: derived state can be thrown
away and rebuilt from history.

## What the tests do not claim

The invariant tests do not prove Reconcile is production accounting software.
They prove the MVP's core accounting rules are protected across many generated
fake scenarios.

They also do not cover payroll, tax, inventory, bank APIs, authentication,
real-data workflows, or production multi-user behavior. Those are intentionally
outside the current scope.
