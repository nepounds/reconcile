# Reconcile Step Plan

This plan tracks the implemented Reconcile build steps and the remaining final
release cleanup.

## Current status

Steps 0 through 29 are complete.

Step 30 is the current documentation-polish step. When Step 30 changes are
applied and validated, Step 30 is complete.

Step 31 remains the final portfolio polish and release cleanup step.

The project is not marked complete yet.

## Step history

### Step 0 — README-driven planning and Project State

Status: Complete.

Defined the project goal, scope, non-goals, architecture plan, event model plan,
accounting rules, reconciliation rules, and project state file.

### Step 1 — Create project skeleton and tooling baseline

Status: Complete.

Created the Python package structure, `pyproject.toml`, `.gitignore`, fake demo
CSV files, and the package import smoke test.

### Step 2 — Add core exceptions and money helpers

Status: Complete.

Added custom exceptions and integer-cent money parsing/formatting helpers.

### Step 3 — Add account models and chart of accounts validation

Status: Complete.

Added account type definitions, normal balance rules, and the validated account
model.

### Step 4 — Add journal entry models and validation

Status: Complete.

Added journal entry and journal line models with double-entry validation.

### Step 5 — Add SQLite schema initialization

Status: Complete.

Added SQLite connection helpers and the MVP schema.

### Step 6 — Add event models and append-only event store

Status: Complete.

Added validated ledger event models, append-only event storage, and deterministic
loading by `event_sequence`.

### Step 7 — Add account service and AccountOpened projection

Status: Complete.

Added account opening through `AccountOpened` events and account projection
updates.

### Step 8 — Add journal posting service and journal projections

Status: Complete.

Added posting of balanced journal entries through `JournalEntryPosted` events and
journal entry/line projections.

### Step 9 — Add account balance projections

Status: Complete.

Added balance projections from posted journal entry activity.

### Step 10 — Add projection rebuild workflow

Status: Complete.

Added projection clearing and deterministic rebuild from the event log.

### Step 11 — Add trial balance report

Status: Complete.

Added trial balance report generation from account projections.

### Step 12 — Add income statement and balance sheet reports

Status: Complete.

Added inclusive date-range income statements and as-of-date balance sheets.

### Step 13 — Add journal reversal behavior

Status: Complete.

Added immutable journal reversals through `JournalEntryReversed` events.

### Step 14 — Add property-based accounting invariant tests

Status: Complete.

Added Hypothesis property tests for double-entry rules, projection replay,
expanded accounting equation behavior, and reversals.

### Step 15 — Add bank CSV import and normalization

Status: Complete.

Added fake bank CSV import, raw description preservation, normalized
descriptions, signed integer amounts, row hashes, and import metadata.

### Step 16 — Add bank duplicate detection

Status: Complete.

Added duplicate detection and duplicate marking for imported bank rows.

### Step 17 — Add ledger cash movement extraction

Status: Complete.

Added bank-comparable cash movement extraction from selected cash-account journal
lines.

### Step 18 — Add exact reconciliation matching

Status: Complete.

Added exact amount/date reconciliation matching with run records, match records,
ledger-link rows, and explanation JSON.

### Step 19 — Add fuzzy reconciliation scoring and ambiguity handling

Status: Complete.

Added fuzzy amount/date/description scoring, duplicate penalties, candidate
thresholds, ambiguity handling, and fuzzy explanation JSON.

### Step 20 — Add split reconciliation matching

Status: Complete.

Added limited split matching for one bank transaction against two or three ledger
cash movements.

### Step 21 — Add CLI workflow

Status: Complete.

Added a thin `argparse` CLI and script wrapper for database setup, demo seeding,
reports, bank import, reconciliation, and projection rebuilds.

### Step 22 — Add report exports and sample outputs

Status: Complete.

Added CSV export helpers, coordinated report export behavior, CLI export support,
and fake sample outputs.

### Step 23 — Add rule-based categorization

Status: Complete.

Added deterministic rule-based categorization for imported bank transactions.

### Step 24 — Add correction storage and optional local classifier

Status: Complete.

Added append-only category correction storage and an optional standard-library
local classifier trained from corrections.

### Step 25 — Add cash flow report

Status: Complete.

Added a direct-method cash flow report, cash-flow CSV export, CLI support, and
focused tests.

### Step 26 — Add Streamlit dashboard foundation

Status: Complete.

Added the local read-only Streamlit dashboard shell, database path input, setup
instructions, summary metrics, and helper tests.

### Step 27 — Add dashboard report pages and event timeline

Status: Complete.

Added Streamlit pages for Overview, Trial Balance, Income Statement, Balance
Sheet, Cash Flow, and Event Timeline.

### Step 28 — Add dashboard reconciliation and categorization review

Status: Complete.

Added read-only Streamlit review pages for Bank Reconciliation and Categorization
Review.

### Step 29 — Add CI workflow

Status: Complete.

Added GitHub Actions CI that installs dev dependencies, runs Ruff, and runs the
full pytest suite on pushes and pull requests.

### Step 30 — Polish README and architecture docs

Status: Complete after applying and validating this step.

Scope:

- Polish README and architecture documentation.
- Update event model documentation to distinguish event-sourced ledger behavior
  from table-backed MVP workflows.
- Update accounting invariant documentation.
- Update reconciliation documentation for implemented exact, fuzzy, split,
  export, and read-only dashboard review behavior.
- Update project state and step plan.
- Refine AR/AP cash-flow classification with focused tests.

Expected files:

```text
README.md
docs/Architecture.md
docs/Event_Model.md
docs/Accounting_Invariants.md
docs/Reconciliation_Design.md
docs/Step_Plan.md
docs/Reconcile_Project_State.md
src/reconcile/reports/cash_flow.py
tests/test_cash_flow_report.py
```

Validation commands:

```bash
python -m pytest tests/test_cash_flow_report.py
python -m pytest
python -m ruff check .
python scripts/run_reconcile.py --help
python scripts/run_reconcile.py report cash-flow --db-path exports/reconcile.db --from 2026-01-01 --to 2026-01-31
git status
```

Suggested commit message:

```text
Polish docs and refine cash flow classification
```

### Step 31 — Final portfolio polish and release cleanup

Status: Not started.

Remaining scope:

- Final README pass after Step 30 is validated.
- Optional screenshots if available.
- Final smoke checks.
- Final git status cleanup.
- Final project-complete marking only after validation.

Do not mark Step 31 complete until that final pass is actually done.
