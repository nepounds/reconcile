# Accounting Invariants

Reconcile uses example-based tests and property-based tests.

Example-based tests check known scenarios. For example, one test can post a specific journal entry and verify the expected account balance.

Property-based tests check general rules. Instead of testing one hand-written journal entry, they generate many small fake ledgers and verify that accounting laws still hold.

Reconcile uses Hypothesis for property-based tests.

---

## Why property tests matter here

Accounting engines are rule-heavy. A few hand-written examples can pass while a hidden edge case still breaks the ledger.

Property tests help prove that the important accounting rules keep working across many generated combinations of accounts, amounts, entries, projection rebuilds, and reversals.

The property tests use fake generated data only. They do not use real customer data, real bank data, external services, randomness from `random`, or network calls.

---

## Tested invariant groups

### Balanced journal entries

Generated balanced two-line journal entries validate successfully.

Generated unbalanced journal entries raise `ValidationError`.

This protects the double-entry rule:

```text
Total debits = Total credits