# Reconcile

Reconcile is a local-first, event-sourced double-entry general ledger engine in Python with SQLite storage.

It is being built as a portfolio project to demonstrate accounting domain knowledge, audit-friendly system design, and disciplined Python engineering.

## Current status

Reconcile is currently complete through **Step 10: projection rebuild workflow**.

Implemented so far:

* Python package skeleton under `src/reconcile/`
* pytest and ruff tooling
* Fake demo CSV inputs
* Custom project exceptions
* Integer-cents money parsing and formatting
* Account models and normal-balance validation
* Journal entry and journal line models
* Double-entry journal validation
* SQLite schema initialization
* Append-only ledger event store
* Account opening through `AccountOpened` events
* Journal posting through `JournalEntryPosted` events
* Account, journal entry, journal line, and account balance projections
* Deterministic projection rebuilds from the event log
* Thin projection rebuild script at `scripts/rebuild_projections.py`

Current verification:

```text
python -m pytest        # 246 passed
python -m ruff check .  # All checks passed
```

Not implemented yet:

* Trial balance report
* Income statement
* Balance sheet
* Journal reversals
* Bank CSV import
* Bank reconciliation
* Categorization
* Full CLI workflow
* Streamlit dashboard
* Property-based invariant tests

## Practical problem

Small-business accounting data needs to be accurate, auditable, explainable, and reconcilable.

Reconcile models accounting activity as an append-only event log. Current account, journal, and balance tables are derived projections that can be cleared and rebuilt from the event history.

The long-term goal is to support financial reports and bank reconciliation from a clear audit trail instead of hidden edits.

## Core design

Reconcile uses an event-sourced architecture:

1. Accounting actions are stored as immutable events.
2. Projection tables are derived from those events.
3. Projection tables can be cleared and rebuilt.
4. Corrections will use reversal events instead of mutating posted history.

The event store is the source of truth. Projections are disposable read models.

## Implemented architecture milestone

Reconcile can now:

* Open accounts through events.
* Post balanced journal entries through events.
* Project account rows, journal entries, journal lines, and account balances into SQLite.
* Rebuild those projections from the append-only event log.
* Preserve `ledger_events` while clearing derived tables.
* Replay events in deterministic `event_sequence` order.
* Run projection rebuilds repeatedly without duplicating rows or changing event history.

This proves the main event-sourcing foundation before report and reconciliation work begins.

## Planned MVP features

The MVP will include:

* A simple chart of accounts
* Append-only accounting events
* Balanced double-entry journal posting
* Reversal events for corrections
* Rebuildable account-balance projections
* Trial balance, income statement, and balance sheet reports
* Point-in-time reporting where practical
* Fake/demo bank CSV import
* Bank transaction normalization and duplicate flagging
* Ledger cash movement extraction
* Exact and fuzzy bank reconciliation
* Limited split matching
* Ambiguous match handling without unsafe auto-confirmation
* Match scores and explanations
* Property-based tests for accounting invariants
* A thin CLI
* A Streamlit dashboard after the core engine works

## Non-goals

The MVP will not include payroll, tax filing, sales tax, inventory accounting, multi-currency accounting, invoice generation, payment processing, user accounts, authentication, cloud hosting requirements, real bank APIs, Plaid, scraping, external APIs for core functionality, LLM dependencies, or real company/bank data.

Reconcile will not allow direct mutation of posted accounting history. Corrections will happen through reversal events.

## Architecture summary

The architecture has four main layers:

1. **Core package** — accounting, event, projection, reporting, import, and reconciliation logic lives in `src/reconcile/`.
2. **SQLite storage** — the event store and projections are stored locally in SQLite.
3. **Thin CLI/scripts** — command-line workflows call tested package functions instead of owning business logic.
4. **Thin dashboard** — Streamlit will eventually display reports, event history, and reconciliation results without becoming the accounting engine.

## Local-first and offline stance

Reconcile is local-first. Core functionality runs offline using local files and a local SQLite database.

Demo data is fake and safe to commit. No external service is required for core ledger behavior.

## Accounting correctness emphasis

Reconcile prioritizes accounting correctness over dashboard polish.

Current and planned rules include:

* Every posted journal entry must have at least two lines.
* Total debits must equal total credits.
* Every journal line must reference a valid active account.
* Money uses integer cents, not floats.
* Asset and expense accounts normally carry debit balances.
* Liability, equity, and revenue accounts normally carry credit balances.
* Before closing entries, the expanded accounting equation should hold:

```text
Assets + Expenses = Liabilities + Equity + Revenue
```

## Event sourcing in plain English

Instead of storing only the current state, Reconcile stores a timeline of accounting events.

For example, posting a journal entry creates a `JournalEntryPosted` event. Current journal tables and account balances are then built from that event.

If projection tables are deleted or become stale, they can be rebuilt by replaying the event timeline in order.

That means the current state comes from a record of what happened, not from hidden edits.

## Current developer commands

Install in editable mode with development tools:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest
```

Run lint checks:

```bash
python -m ruff check .
```

Rebuild projections for the default demo database path:

```bash
python scripts/rebuild_projections.py --db-path exports/reconcile.db
```

## Next planned step

Next up: **Step 11 — Add trial balance report**.

That step will begin the reporting layer by generating trial balance data from existing account-balance projections.

## Portfolio value

Reconcile is designed to demonstrate:

* Double-entry accounting knowledge
* Audit-friendly correction workflows
* Event-sourcing architecture
* SQLite schema design
* Projection replay and rebuild logic
* Financial report generation
* Explainable bank reconciliation
* Duplicate and ambiguity handling
* Property-based testing for accounting invariants
* Clean Python project structure
* Scope control and honest documentation

## Planning docs

* `docs/Reconcile_Project_State.md` — living source of truth
* `docs/Architecture.md` — architecture overview
* `docs/Event_Model.md` — planned event model
* `docs/Accounting_Invariants.md` — accounting rules and invariant testing plan
* `docs/Reconciliation_Design.md` — reconciliation matching design
* `docs/Step_Plan.md` — phase-based step plan
