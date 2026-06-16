# Reconcile Architecture

Reconcile is planned as a local-first accounting engine built around an append-only event log, SQLite storage, rebuildable projections, and thin user interfaces.

This document describes planned architecture only. Step 0 does not implement code.

## Plain-English overview

Reconcile will store accounting activity as events. Events describe what happened, such as an account being opened, a journal entry being posted, a journal entry being reversed, or a bank statement being imported.

The current state of the ledger will be calculated from those events. Account balances, journal views, reports, and reconciliation results are planned as derived state. They should be explainable from the event history.

## Event store as source of truth

The event store will be the authoritative record of accounting activity.

Planned rules:

- Events are append-only.
- Events are ordered by `event_sequence`.
- Events should have stable IDs.
- Event payloads should contain enough data to replay the business action.
- Financial state changes must happen through events.
- Posted accounting history should not be edited or deleted.

The planned SQLite table for this is `ledger_events`.

## Projections as rebuildable derived state

Projections are planned read models built from events. Examples include:

- `accounts`
- `journal_entries`
- `journal_entry_lines`
- `account_balances`
- reconciliation result tables

A projection should be disposable. The project should eventually be able to clear projections and rebuild them by replaying events in `event_sequence` order.

This matters because it proves that reports are derived from the ledger history instead of from hidden balance edits.

## Why corrections use reversal events

Accounting corrections should preserve the audit trail. Reconcile will not edit a posted journal entry to make it look like the mistake never happened.

Instead, the planned correction flow is:

1. Keep the original posted journal entry.
2. Create a reversal event.
3. Create reversing journal lines that neutralize the original entry.
4. Optionally post a corrected replacement entry later.

This keeps history visible and makes it easier to explain how a balance changed.

## Why SQLite is used

SQLite is planned for the MVP because it is local, simple to set up, and good for a portfolio project. It avoids requiring a database server while still allowing real SQL schema design.

SQLite also fits the local-first goal:

- No cloud database required.
- No external service required.
- A demo database can be created locally.
- Tests can use temporary local databases.

A future project could migrate the schema to Postgres, but that is not part of the MVP.

## Separation between core package, CLI, and dashboard

The planned package structure keeps business logic in `src/reconcile/`.

The CLI should:

- Parse arguments.
- Validate paths and user options.
- Call package services.
- Return clear user-facing errors.

The dashboard should:

- Display reports and reconciliation results.
- Show event history and explanations.
- Call tested package functions or read safe projections.
- Avoid owning accounting or reconciliation logic.

This keeps the core engine testable without needing a terminal UI or Streamlit app.

## Scope boundaries

The MVP will focus on:

- Event-sourced ledger mechanics.
- Double-entry journal posting.
- Reversals.
- Rebuildable projections.
- Trial balance, income statement, and balance sheet.
- Fake/demo bank CSV import.
- Explainable reconciliation.
- Tests, including property-based accounting invariant tests.

The MVP will not include payroll, tax filing, inventory accounting, bank APIs, Plaid, real company data, real bank data, authentication, production deployment, or LLM behavior.
