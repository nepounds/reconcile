# Reconcile Architecture

Reconcile is a local-first Python accounting engine built around an append-only
ledger event log, SQLite storage, rebuildable projections, point-in-time reports,
explainable reconciliation, deterministic categorization, and a thin read-only
Streamlit dashboard.

The project is a portfolio/demo system. It is not production accounting software
and does not claim cloud deployment, external bank integrations, authentication,
or real-data support.

## Plain-English overview

Reconcile stores core accounting activity as events. An event records something
that happened, such as opening an account, posting a journal entry, or reversing
a posted journal entry.

SQLite tables then serve two roles:

1. The append-only `ledger_events` table stores the ledger source of truth.
2. Projection and workflow tables make the ledger easy to query, report, and
   review locally.

Reports and dashboard pages read from the SQLite database and existing package
functions. They do not own accounting logic.

## Local-first design

Reconcile runs locally with Python and SQLite.

The default generated demo database is:

```text
exports/reconcile.db
```

That database is local output and should not be committed. The committed demo
data is fake CSV input under `examples/demo_company/`, plus fake sample CSV
outputs under `examples/sample_output/`.

The local-first design keeps the project easy to clone, run, inspect, and test
without secrets, network calls, hosted services, or customer data.

## SQLite storage

SQLite is used because it keeps setup simple while still supporting real schema
design, constraints, joins, and deterministic tests.

Important table groups:

- `ledger_events` stores append-only accounting events.
- `accounts`, `journal_entries`, and `journal_entry_lines` are accounting
  projections.
- `account_balances` stores rebuildable balance projections.
- `bank_statement_imports` and `bank_transactions` store imported fake bank CSV
  data.
- `reconciliation_runs`, `reconciliation_matches`, and
  `reconciliation_match_ledger_links` store reconciliation workflow output.
- `category_corrections` stores user category corrections for imported bank
  rows.

## Append-only event store

The `ledger_events` table is the source of truth for implemented ledger actions.
Events are loaded and replayed in deterministic `event_sequence` order.

Implemented ledger event types:

- `AccountOpened`
- `JournalEntryPosted`
- `JournalEntryReversed`

Posted journal entries are not edited in place. Corrections use reversal events
and reversing journal lines so the audit trail remains visible.

## Projections

Projections are derived tables used for fast reads and simple reports.

Current projections include:

- account rows
- journal entry rows
- journal line rows
- account balances

Projection tables are disposable. They can be cleared and rebuilt by replaying
`ledger_events` in `event_sequence` order. This proves that balances and journal
views are derived from event history rather than hidden manual edits.

## Projection rebuild

The rebuild workflow clears derived tables and replays supported ledger events.
It rebuilds accounts, journal entries, journal lines, reversal state, and account
balances.

Bank import, reconciliation, and categorization tables are MVP workflow tables.
They are not currently rebuilt from ledger events.

## Report generation

Reports are read-only package functions. They do not append events, rebuild
projections, write files, print, or mutate SQLite state.

Implemented reports:

- Trial balance
- Income statement
- Balance sheet
- Direct-method cash flow

The cash flow report uses direct-method cash movement rules. Step 30 refined the
simple classification logic so customer receivable collections and ordinary
vendor payable payments classify as operating cash flow.

## Bank import and reconciliation

Bank CSV import stores fake/demo bank statements directly in bank tables. It
preserves raw descriptions, normalized descriptions, signed integer-cent amounts,
row hashes, and duplicate flags.

Reconciliation compares imported bank transactions to ledger cash movements
extracted from cash-account journal lines.

Implemented reconciliation modes:

- exact amount/date matching
- fuzzy amount/date/description scoring
- limited split matching for two or three ledger movements

Reconciliation writes only to reconciliation tables and stores explanation JSON
for review. It does not mutate ledger history.

Manual match confirmation/rejection is future work.

## Categorization

Categorization is local and explainable.

Implemented behavior:

- deterministic rule-based categorization
- append-only correction storage
- optional standard-library local classifier trained from corrections

The classifier is not an external service and does not use LLM behavior.

## Streamlit dashboard

`dashboard/streamlit_app.py` is a thin read-only local dashboard.

Implemented pages:

- Overview
- Trial Balance
- Income Statement
- Balance Sheet
- Cash Flow
- Event Timeline
- Bank Reconciliation
- Categorization Review

The dashboard reads from SQLite and existing package functions. It does not
import bank files, run reconciliation, rebuild projections, write category
corrections, confirm/reject matches, train models, or write exports.

## CLI

The CLI lives in `src/reconcile/cli.py` with a thin script wrapper at
`scripts/run_reconcile.py`.

The CLI handles local demo setup, projection rebuilds, reports, bank import,
reconciliation runs, and report exports. Business logic stays inside the package
modules.

## CI

GitHub Actions runs Ruff and the full pytest suite on pushes and pull requests.
The CI workflow is intentionally simple: no deployment, coverage service, mypy,
Docker, caching, secrets, or Streamlit launch job.

## Scope boundaries

Reconcile intentionally excludes:

- payroll
- tax filing or tax calculation
- bank APIs and Plaid
- real bank data or real company data
- authentication and user accounts
- production multi-user workflows
- full AR/AP subledgers
- invoice and bill-pay workflows
- dashboard writeback
- manual reconciliation confirmation/rejection
- LLM behavior
