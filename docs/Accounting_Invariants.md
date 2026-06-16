# Reconcile Accounting Invariants

This document defines the planned accounting rules that Reconcile should protect. Step 0 does not implement these tests yet.

## Double-entry rules

Every posted journal entry must follow double-entry accounting.

Planned rules:

- A journal entry must have at least two lines.
- Each line must have one side: debit or credit.
- Each line amount must be positive integer cents.
- Each line must reference a valid active account.
- The total debit amount must equal the total credit amount.

## Debits equal credits

For every valid journal entry:

```text
total debits = total credits
```

For every valid trial balance:

```text
total debit balances = total credit balances
```

Unbalanced entries should be rejected before they reach the event store.

## Valid account rules

Planned account types:

- asset
- liability
- equity
- revenue
- expense

Planned account rules:

- Account code cannot be blank.
- Account name cannot be blank.
- Account type must be valid.
- Normal balance must be debit or credit.
- Duplicate account codes are rejected.
- Closed or inactive accounts cannot be used in new journal entries.

## Normal balance rules

Normal balances are planned as:

| Account type | Normal balance |
| --- | --- |
| Asset | Debit |
| Expense | Debit |
| Liability | Credit |
| Equity | Credit |
| Revenue | Credit |

A debit increases asset and expense accounts. A credit increases liability, equity, and revenue accounts.

## Expanded accounting equation

Before closing entries, Reconcile will use this expanded accounting equation:

```text
Assets + Expenses = Liabilities + Equity + Revenue
```

This equation is useful because revenue and expense accounts remain open during the reporting period.

## Reversal neutrality

A reversal should neutralize the original journal entry's net account impact.

Planned rule:

```text
original entry + reversal entry = zero net effect by account
```

The original entry should remain visible. The reversal should be a new event and a new reversing journal entry.

## Projection replay invariants

Projection replay should be deterministic.

Planned invariants:

- Replaying the same events in `event_sequence` order should produce the same projections.
- Clearing projections and rebuilding them from events should reproduce the same account balances.
- Reports generated from rebuilt projections should match reports generated before rebuild.
- Invalid events or invalid journal entries should not silently produce balances.

## How Hypothesis will be used later

Hypothesis will be used for property-based tests after the core engine exists.

Plain-English purpose:

> Example tests check a few known cases. Property-based tests generate many random valid ledgers and verify that accounting rules still hold.

Planned property tests:

- Generated balanced journal entries keep debits equal to credits.
- Generated invalid unbalanced entries are rejected.
- Invalid entries never enter the event store.
- Any sequence of valid posted entries keeps the trial balance balanced.
- The expanded accounting equation holds before closing entries.
- Projection replay reproduces the same account balances.
- Reversing a valid entry removes its net account impact.
- Event replay is deterministic in `event_sequence` order.
- Report totals agree with underlying account balances.
