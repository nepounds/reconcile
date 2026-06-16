# Reconcile

Reconcile is a planned local-first, event-sourced double-entry general ledger engine in Python with SQLite storage.

## Practical problem

Small-business accounting data needs to be accurate, auditable, explainable, and reconcilable. Reconcile will model the accounting system as an append-only event log, derive balances and reports from that log, and compare ledger cash activity against imported bank-statement activity.

This repository is currently in Step 0: planning only. No implementation behavior is claimed yet.

## Planned MVP features

The MVP will include:

- A simple chart of accounts.
- Append-only accounting events.
- Balanced double-entry journal posting.
- Reversal events for corrections instead of editing posted history.
- Rebuildable account-balance projections.
- Trial balance, income statement, and balance sheet reports.
- Point-in-time reporting where practical.
- Fake/demo bank CSV import.
- Bank transaction normalization and duplicate flagging.
- Ledger cash movement extraction.
- Exact and fuzzy bank reconciliation.
- Limited split matching.
- Ambiguous match handling without unsafe auto-confirmation.
- Match scores and explanations.
- Property-based tests for accounting invariants.
- A thin CLI.
- A Streamlit dashboard after the core engine works.

## Non-goals

The MVP will not include payroll, tax filing, sales tax, inventory accounting, multi-currency accounting, invoice generation, payment processing, user accounts, authentication, cloud hosting requirements, real bank APIs, Plaid, scraping, external APIs for core functionality, LLM dependencies, or real company/bank data.

Reconcile will not allow direct mutation of posted accounting history. Corrections will happen through reversal events.

## Architecture summary

The planned architecture has four main layers:

1. **Core package** — accounting, event, projection, reporting, import, and reconciliation logic will live in `src/reconcile/`.
2. **SQLite storage** — the event store and projections will be stored locally in SQLite.
3. **Thin CLI** — command-line workflows will call tested package functions instead of owning business logic.
4. **Thin dashboard** — Streamlit will display reports, event history, and reconciliation results without becoming the accounting engine.

The event store will be the source of truth. Projections will be rebuildable derived state.

## Local-first and offline stance

Reconcile is planned as a local-first project. Core functionality will run offline using local files and a local SQLite database. Demo data will be fake and safe to commit. No external service will be required for core ledger, reporting, import, or reconciliation behavior.

## Accounting correctness emphasis

Reconcile will prioritize accounting correctness over dashboard polish. Planned rules include:

- Every posted journal entry must have at least two lines.
- Total debits must equal total credits.
- Every journal line must reference a valid active account.
- Money will use integer cents, not floats.
- Asset and expense accounts normally carry debit balances.
- Liability, equity, and revenue accounts normally carry credit balances.
- Before closing entries, the expanded accounting equation should hold:

```text
Assets + Expenses = Liabilities + Equity + Revenue
```

## Event sourcing in plain English

Instead of storing only the current state, Reconcile will store a timeline of accounting events. For example, posting a journal entry creates a `JournalEntryPosted` event. Correcting that entry creates a separate reversal event instead of editing or deleting the original event.

Balances and reports will be rebuilt by replaying the event timeline in order. This makes the audit trail easier to explain: the current state comes from a record of what happened, not from hidden edits.

## Planned quickstart

Coming after Step 1.

Step 1 will create the project skeleton, Python packaging, tooling baseline, and first smoke test. Until then, this repository is documentation/planning only.

## Portfolio value

Reconcile is designed to demonstrate:

- Double-entry accounting knowledge.
- Audit-friendly correction workflows.
- Event-sourcing architecture.
- SQLite schema design.
- Projection replay and rebuild logic.
- Financial report generation.
- Explainable bank reconciliation.
- Duplicate and ambiguity handling.
- Property-based testing for accounting invariants.
- Clean Python project structure.
- Scope control and honest documentation.

## Planning docs

- `docs/Reconcile_Project_State.md` — living source of truth.
- `docs/Architecture.md` — architecture overview.
- `docs/Event_Model.md` — planned event model.
- `docs/Accounting_Invariants.md` — accounting rules and invariant testing plan.
- `docs/Reconciliation_Design.md` — reconciliation matching design.
- `docs/Step_Plan.md` — phase-based step plan.
