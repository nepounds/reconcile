# Reconcile

Reconcile is a local-first Python accounting engine that uses event-sourced double-entry bookkeeping, rebuildable SQLite projections, property-tested accounting invariants, and explainable bank reconciliation.

It is built as a portfolio project for accounting, finance, data, and software engineering roles.

The project focuses on a practical accounting systems problem:

> Small-business accounting data needs to be accurate, auditable, explainable, and reconcilable. Reconcile records accounting actions as immutable events, rebuilds financial state from those events, and reconciles imported bank activity against ledger cash movements.

---

## Current status

Reconcile is currently in active development.

Current completed milestone:

```text
Step 20 — Split reconciliation matching
```

Approximate project completion:

```text
66% to 68%
```

Current validation status:

```text
Tests pass locally
ruff clean locally
```

The hardest reconciliation-engine stretch is now complete. Reconcile can import bank transactions, extract ledger cash movements, run exact reconciliation, run fuzzy scoring, identify ambiguous candidates, and match one bank transaction to two or three ledger cash movements through split matching.

Still planned:

* CLI workflow
* Report exports and sample outputs
* Rule-based categorization
* Optional correction-based local classifier
* Cash flow report
* Streamlit dashboard
* CI workflow
* Final documentation and portfolio polish

---

## What Reconcile does today

Reconcile currently supports:

* Opening accounts through immutable accounting events.
* Posting balanced double-entry journal entries.
* Rejecting invalid or unbalanced journal entries.
* Building account-balance projections.
* Rebuilding projections from the append-only event log.
* Generating a trial balance.
* Generating an income statement.
* Generating a balance sheet.
* Reversing posted journal entries through immutable reversal events.
* Running property-based accounting invariant tests with Hypothesis.
* Importing fake bank statement CSV data.
* Normalizing bank transaction descriptions.
* Detecting and flagging duplicate imported bank transactions.
* Extracting ledger cash movements from selected cash accounts.
* Running exact reconciliation matching.
* Running fuzzy reconciliation scoring.
* Detecting ambiguous reconciliation candidates.
* Running limited split reconciliation matching.
* Storing reconciliation runs, match records, match explanations, and ledger-link rows.

---

## Why this project exists

Accounting systems are not just CRUD apps.

A useful accounting engine needs to preserve history, prove entries balance, rebuild derived state, explain reconciliation decisions, and avoid unsafe automatic matches.

Reconcile demonstrates those ideas in a small, local-first Python project.

The goal is not to replace QuickBooks, Xero, or an ERP. The goal is to show a clear, testable accounting engine with the kind of design choices used in real accounting and fintech systems:

* Append-only event history
* Double-entry validation
* Reversal entries instead of mutation
* Rebuildable projections
* Integer-cents money handling
* Point-in-time financial reports
* Explainable reconciliation logic
* Property-based invariant tests

---

## Portfolio summary

Resume-style summary:

> Built Reconcile, an event-sourced double-entry general ledger engine in Python and SQLite with immutable journal events, projection replay, point-in-time financial statements, bank reconciliation, and property-based accounting invariant tests.

Longer explanation:

> Reconcile is a local-first Python accounting engine that records accounting actions as append-only events, projects those events into SQL read models, generates financial statements, imports bank transactions, extracts ledger cash movements, and reconciles bank activity against the ledger with exact, fuzzy, ambiguous, and split-match explanations.

---

## Tech stack

Runtime:

* Python
* SQLite
* Standard library CSV and JSON tooling

Testing and tooling:

* pytest
* Hypothesis
* ruff

Planned later:

* Streamlit for the dashboard
* pandas only where useful for dashboard or export-facing work
* scikit-learn only if the optional local categorization classifier is implemented

---

## Design principles

Reconcile follows these project rules:

* Use integer cents for money.
* Never use floats for money.
* Keep the project local-first.
* Keep sample data fake.
* Keep the event store append-only.
* Treat projections as rebuildable derived state.
* Use reversal events for corrections.
* Do not directly mutate posted accounting history.
* Make reconciliation decisions explainable.
* Keep dashboard and CLI code thin.
* Keep business logic inside importable package modules.
* Add tests with every meaningful feature.

Core architecture rule:

```text
If a feature changes financial state, it must do so through an event.
```

Reconciliation rule:

```text
If the program makes a match decision, store why it made that decision.
```

---

## Current implemented features

### Project foundation

Implemented:

* Python package structure under `src/reconcile/`
* `pyproject.toml`
* pytest test suite
* ruff linting
* fake demo input data
* project documentation and living project state

---

### Money helpers

Implemented:

* Parse money strings into integer cents.
* Format integer cents as dollar strings.
* Reject floats and invalid money values.
* Preserve signed values for bank imports.

Examples:

```text
"50.00"  -> 5000
"-50.00" -> -5000
```

---

### Account model

Implemented account support for:

* Assets
* Liabilities
* Equity
* Revenue
* Expenses

Normal balance rules:

```text
Asset     -> debit
Expense   -> debit
Liability -> credit
Equity    -> credit
Revenue   -> credit
```

Implemented validations:

* Blank account IDs rejected.
* Blank account codes rejected.
* Blank account names rejected.
* Invalid account types rejected.
* Invalid normal balances rejected.
* Mismatched account type and normal balance rejected.

---

### Journal entry model

Implemented:

* Journal entries
* Journal lines
* Double-entry validation
* Debit and credit totals
* Balanced entry checks

Rules enforced:

* Every journal entry must have at least two lines.
* Every journal line must have a valid side: debit or credit.
* Every journal line amount must be positive integer cents.
* Total debits must equal total credits.
* Invalid entries fail before reaching the event store.

---

### SQLite schema

Implemented SQLite tables:

* `ledger_events`
* `accounts`
* `journal_entries`
* `journal_entry_lines`
* `account_balances`
* `bank_statement_imports`
* `bank_transactions`
* `reconciliation_runs`
* `reconciliation_matches`
* `reconciliation_match_ledger_links`

The schema supports the current accounting engine and reconciliation workflows.

---

### Event store

Implemented:

* `LedgerEvent` model
* Append-only event storage
* Deterministic event loading by `event_sequence`
* Event lookup by ID
* Event filtering by type
* JSON payload round trips
* Duplicate event ID protection

Current supported accounting event types:

```text
AccountOpened
JournalEntryPosted
JournalEntryReversed
```

Planned event types include:

```text
BankStatementImported
ReconciliationRunCompleted
ReconciliationMatchConfirmed
ReconciliationMatchRejected
```

---

### Account opening

Implemented:

* Open accounts through `AccountOpened` events.
* Project account events into the `accounts` table.
* Reject duplicate account IDs.
* Reject duplicate account codes.
* Look up accounts by ID.
* Look up accounts by code.
* List accounts in stable order.

---

### Journal posting

Implemented:

* Post journal entries through `JournalEntryPosted` events.
* Validate entries before appending events.
* Reject duplicate journal entry IDs.
* Reject missing account references.
* Reject inactive account references.
* Project journal headers into `journal_entries`.
* Project lines into `journal_entry_lines`.

Invalid journal entries do not enter the event store.

---

### Account balance projections

Implemented:

* Apply posted journal activity to `account_balances`.
* Track debit totals.
* Track credit totals.
* Calculate normal-balance-aware balances.
* Support asset, liability, equity, revenue, and expense accounts.
* Preserve historical debit and credit activity.
* Prevent duplicate event application from double-counting balances.

Balance rules:

```text
Debit-normal accounts:
balance = debit_total_cents - credit_total_cents

Credit-normal accounts:
balance = credit_total_cents - debit_total_cents
```

---

### Projection rebuild

Implemented:

* Clear derived projection tables.
* Preserve the append-only event store.
* Replay events in deterministic `event_sequence` order.
* Rebuild accounts from `AccountOpened`.
* Rebuild journal entries and lines from `JournalEntryPosted`.
* Rebuild account balances from journal events.
* Rebuild reversal state from `JournalEntryReversed`.
* Confirm rebuilt projections match incremental projections.

Projection rebuilds make the event log the source of truth.

---

### Trial balance report

Implemented:

* Generate trial balance rows from account projections.
* Include accounts with no activity.
* Include inactive accounts.
* Include debit totals and credit totals.
* Calculate ending debit and ending credit balances.
* Validate account and balance data read from SQLite.
* Confirm trial balance stays balanced for valid ledgers.

---

### Income statement report

Implemented:

* Generate income statements for inclusive date ranges.
* Include revenue and expense accounts.
* Calculate revenue as credits minus debits.
* Calculate expenses as debits minus credits.
* Calculate net income.
* Validate date arguments.
* Reject invalid stored account or journal-line data.

---

### Balance sheet report

Implemented:

* Generate balance sheets as of a selected date.
* Include asset, liability, and equity accounts.
* Include current period net income as an equity-like amount.
* Calculate balances from posted journal lines through the as-of date.
* Avoid relying only on cumulative account balance projections for date-filtered reporting.
* Validate stored account and journal-line data.

---

### Journal reversals

Implemented:

* Reverse posted journal entries through immutable `JournalEntryReversed` events.
* Preserve original posted journal entries.
* Preserve original journal lines.
* Create a new reversal journal entry.
* Flip debit and credit sides.
* Preserve account IDs, amount cents, line order, and line descriptions.
* Mark original entries with `reversed_by_entry_id`.
* Mark reversal entries with `reversal_of_entry_id`.
* Apply reversal activity to account balances.
* Rebuild reversal state from events.

Reversals neutralize net account impact without deleting original history.

Example:

```text
Original:
Debit Cash 100.00
Credit Revenue 100.00

Reversal:
Debit Revenue 100.00
Credit Cash 100.00
```

Historical activity remains visible.

---

### Property-based accounting invariant tests

Implemented with Hypothesis:

* Generated balanced journal entries validate successfully.
* Generated unbalanced journal entries raise validation errors.
* Invalid generated entries do not enter the event store.
* Generated valid entries keep the trial balance balanced.
* Generated valid posting sequences keep the trial balance balanced.
* The expanded accounting equation holds before closing entries.
* Projection rebuilds restore the same balances.
* Projection rebuilds restore the same trial balance.
* Projection rebuilds do not change event count, event IDs, or event sequences.
* Running rebuild twice is deterministic.
* Generated reversal entries neutralize net account impact.
* Generated reversals preserve historical debit and credit activity.
* Rebuild after reversals restores incremental reversal state.

Expanded accounting equation tested:

```text
Assets + Expenses = Liabilities + Equity + Revenue
```

---

### Bank CSV import

Implemented:

* Read fake bank statement CSV files.
* Validate required columns.
* Preserve raw descriptions.
* Normalize descriptions.
* Parse signed bank amounts into integer cents.
* Store import metadata.
* Store bank transaction rows.
* Store deterministic row hashes.
* Reject invalid files and invalid rows.
* Confirm bank imports do not mutate accounting state.

Required bank CSV columns:

```text
transaction_date
description
amount
```

Optional columns:

```text
posted_date
external_id
check_number
```

Bank sign convention:

```text
Deposit / inflow     = positive amount
Withdrawal / outflow = negative amount
```

---

### Bank duplicate detection

Implemented:

* Detect duplicate imported bank rows.
* Mark duplicates with deterministic `duplicate_group_id` values.
* Return computed duplicate reasons.
* Preserve all source rows.
* Do not delete or merge duplicates.
* Integrate duplicate marking into bank CSV import.

Duplicate rules:

1. Duplicate row hash
2. Duplicate nonblank external ID
3. Duplicate transaction fingerprint

Fingerprint fields:

```text
transaction_date
amount_cents
description_normalized
```

Duplicate rule precedence:

```text
row_hash
external_id
fingerprint
```

---

### Ledger cash movement extraction

Implemented:

* Extract ledger cash movements from journal lines touching a selected cash account.
* Convert debit-to-Cash lines into positive bank-comparable amounts.
* Convert credit-from-Cash lines into negative bank-comparable amounts.
* Ignore non-cash journal lines.
* Support inclusive date filtering.
* Validate selected cash account.
* Exclude reversed original entries and reversal entries by default.
* Optionally include reversed and reversal entries for audit review.
* Return stable movement IDs and useful journal/account metadata.
* Confirm extraction is read-only.

Bank-comparable movement convention:

```text
Debit to Cash   = positive amount
Credit to Cash  = negative amount
```

---

### Exact reconciliation matching

Implemented:

* Create reconciliation run records.
* Match bank transactions to ledger cash movements by exact amount and exact date.
* Store reconciliation match records.
* Store explanation JSON.
* Store ledger-link rows for exact auto-matches.
* Enforce one-to-one ledger movement usage within a run.
* Leave unmatched bank transactions clearly marked.
* Block duplicate-flagged bank transactions from unsafe auto-matching.
* Keep reconciliation writes limited to reconciliation tables.

Exact match rule:

```text
bank.amount_cents == ledger_cash_movement.amount_cents
bank.transaction_date == ledger_cash_movement.entry_date
```

Exact auto-match record values:

```text
match_type = exact
status = auto_matched
score = 100.0
amount_delta_cents = 0
date_delta_days = 0
```

---

### Fuzzy reconciliation scoring

Implemented:

* Score amount similarity.
* Score date proximity.
* Score description similarity.
* Apply duplicate penalties.
* Store score component explanations.
* Create fuzzy reconciliation runs.
* Store fuzzy match records.
* Distinguish auto-matched, candidate, ambiguous, and unmatched decisions.
* Prevent unsafe auto-matches when top candidates are too close.
* Block duplicate-flagged bank transactions from fuzzy auto-matching.
* Prevent ledger movement reuse across fuzzy auto-matches.

Default fuzzy score:

```text
score = amount_score * 0.60
      + date_score * 0.25
      + description_score * 0.15
      - duplicate_penalty
```

Default fuzzy decisions:

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

---

### Split reconciliation matching

Implemented:

* Match one bank transaction to two or three ledger cash movements.
* Search bounded combinations only.
* Enforce same-sign component rules.
* Enforce amount tolerance against summed component totals.
* Enforce date windows against every component movement.
* Score split candidates.
* Apply split penalty.
* Store split explanation JSON.
* Create one ledger-link row per component for split auto-matches.
* Keep candidate and ambiguous split rows non-consuming.
* Prevent component reuse across split auto-matches.
* Preserve exact and fuzzy reconciliation behavior.

Default split score:

```text
score = amount_score * 0.70
      + date_score * 0.25
      + description_score * 0.05
      - split_penalty
```

Default split rules:

```text
Only combine 2 or 3 ledger cash movements.
Only combine same-sign movements.
Only search within the date window.
Only accept combinations that sum to the bank amount within tolerance.
Do not run unlimited subset-sum search.
```

Example:

```text
Bank withdrawal:
-150.00

Ledger movements:
-50.00 Software expense
-100.00 Office supplies

Split match total:
-150.00
```

---

## Current test suite

The test suite covers:

* Money parsing and formatting
* Account model validation
* Journal model validation
* SQLite schema creation
* Event store behavior
* Account opening
* Journal posting
* Account balance projections
* Projection rebuilds
* Trial balance reports
* Income statement reports
* Balance sheet reports
* Journal reversals
* Property-based accounting invariants
* Bank CSV import
* Bank duplicate detection
* Ledger cash movement extraction
* Exact reconciliation matching
* Fuzzy reconciliation scoring
* Split reconciliation matching

Standard validation commands:

```bash
python -m pytest
python -m ruff check .
```

---

## Project structure

Current and planned project structure:

```text
reconcile/
├── docs/
│   ├── Reconcile_Project_State.md
│   ├── Architecture.md
│   ├── Event_Model.md
│   ├── Accounting_Invariants.md
│   ├── Reconciliation_Design.md
│   └── Step_Plan.md
├── examples/
│   ├── demo_company/
│   │   ├── chart_of_accounts.csv
│   │   ├── journal_entries.csv
│   │   └── bank_statement.csv
│   └── sample_output/
├── exports/
├── scripts/
│   └── rebuild_projections.py
├── src/
│   └── reconcile/
│       ├── __init__.py
│       ├── db.py
│       ├── exceptions.py
│       ├── money.py
│       ├── accounts/
│       ├── events/
│       ├── imports/
│       ├── journal/
│       ├── projections/
│       ├── reconciliation/
│       └── reports/
├── tests/
│   ├── property/
│   ├── test_account_service.py
│   ├── test_account_balances.py
│   ├── test_bank_duplicate_detection.py
│   ├── test_bank_import.py
│   ├── test_cash_movements.py
│   ├── test_db_schema.py
│   ├── test_event_store.py
│   ├── test_journal_models.py
│   ├── test_journal_posting.py
│   ├── test_journal_reversals.py
│   ├── test_money.py
│   ├── test_projection_rebuild.py
│   ├── test_reconciliation_exact.py
│   ├── test_reconciliation_fuzzy.py
│   ├── test_reconciliation_splits.py
│   └── test_reports.py
├── pyproject.toml
└── README.md
```

Some planned modules are intentionally not implemented yet.

---

## Setup

From the project root:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest
```

Run linting:

```bash
python -m ruff check .
```

Run projection rebuild script:

```bash
python scripts/rebuild_projections.py --db-path exports/reconcile.db
```

---

## Sample data

Fake sample input files live under:

```text
examples/demo_company/
```

Current sample files:

```text
examples/demo_company/chart_of_accounts.csv
examples/demo_company/journal_entries.csv
examples/demo_company/bank_statement.csv
```

All sample data is fake and safe to commit.

No real bank data, customer data, private financial data, or credentials should be added to this repository.

---

## Roadmap

### Completed

* Step 0 — Planning and project state
* Step 1 — Project skeleton and tooling baseline
* Step 2 — Exceptions and money helpers
* Step 3 — Account models and chart validation
* Step 4 — Journal entry models and validation
* Step 5 — SQLite schema initialization
* Step 6 — Event models and append-only event store
* Step 7 — Account service and AccountOpened projection
* Step 8 — Journal posting service and journal projections
* Step 9 — Account balance projections
* Step 10 — Projection rebuild workflow
* Step 11 — Trial balance report
* Step 12 — Income statement and balance sheet reports
* Step 13 — Journal reversal behavior
* Step 14 — Property-based accounting invariant tests
* Step 15 — Bank CSV import and normalization
* Step 16 — Bank duplicate detection
* Step 17 — Ledger cash movement extraction
* Step 18 — Exact reconciliation matching
* Step 19 — Fuzzy reconciliation scoring and ambiguity handling
* Step 20 — Split reconciliation matching

---

### Next planned work

#### Step 21 — CLI workflow

Planned:

* Add a thin command-line interface.
* Initialize databases.
* Seed demo data.
* Rebuild projections.
* Generate reports.
* Import bank statements.
* Run reconciliation workflows.

The CLI should call package functions and keep business logic out of script wrappers.

---

#### Step 22 — Report exports and sample outputs

Planned:

* Export trial balance.
* Export income statement.
* Export balance sheet.
* Export reconciliation results.
* Generate fake sample output files.
* Add tests that inspect export contents.

---

#### Step 23 — Rule-based categorization

Planned:

* Add deterministic category rules.
* Apply rules by priority.
* Return or store category source and reason.
* Keep unmatched transactions uncategorized.

---

#### Step 24 — Correction storage and optional local classifier

Planned:

* Store user category corrections.
* Extract training examples from corrections.
* Optionally train a local scikit-learn classifier.
* Use confidence thresholds.
* Keep rules above ML predictions.
* Keep all categorization local.

No LLM or external API categorization is planned.

---

#### Step 25 — Cash flow report

Planned:

* Add direct-method cash flow report.
* Calculate beginning cash.
* Calculate cash inflows.
* Calculate cash outflows.
* Calculate net cash change.
* Calculate ending cash.

---

#### Step 26 — Streamlit dashboard foundation

Planned:

* Add Streamlit app shell.
* Add database path selector or default demo path.
* Add overview page.
* Show basic account balances and project status.
* Keep dashboard logic thin.

---

#### Step 27 — Dashboard report pages and event timeline

Planned:

* Add trial balance page.
* Add income statement page.
* Add balance sheet page.
* Add cash flow page if available.
* Add event timeline page.
* Add date or event-sequence selectors.

---

#### Step 28 — Dashboard reconciliation and categorization review

Planned:

* Show imported bank transactions.
* Show matched ledger movements.
* Show reconciliation status.
* Show scores and explanations.
* Show ambiguous candidates.
* Show split components.
* Show categorization decisions and reasons.

---

#### Step 29 — CI workflow

Planned:

* Add GitHub Actions.
* Run pytest.
* Run ruff.
* Confirm CI passes.

---

#### Step 30 — README and architecture documentation polish

Planned:

* Polish README quickstart.
* Update architecture docs.
* Update event model docs.
* Update accounting invariant docs.
* Update reconciliation design docs.
* Add screenshots if dashboard exists.
* Make docs match actual behavior.

---

#### Step 31 — Final portfolio cleanup

Planned:

* Final README review.
* Final docs review.
* Final CHANGELOG update.
* Final CONTRIBUTING update.
* Final smoke checks.
* Final sample outputs.
* Confirm no secrets or real data.
* Mark project complete.

---

## Non-goals

The MVP does not include:

* Payroll
* Tax engine
* Sales tax logic
* Income tax logic
* Inventory accounting
* Multi-currency
* Bank APIs
* Plaid integration
* External APIs
* Scraping
* LLM dependencies
* Cloud database
* Production deployment requirement
* Authentication
* User accounts
* Full AR/AP subledger
* Invoice generation
* Payment processing
* Real company data
* Real bank data
* Direct mutation of posted accounting history
* Unlimited subset-sum reconciliation search

---

## Current limitations

Current limitations are intentional while the project is still under development:

* CLI workflow is not implemented yet.
* CSV report exports are not implemented yet.
* Cash flow report is not implemented yet.
* Rule-based categorization is not implemented yet.
* Correction storage and classifier workflow are not implemented yet.
* Streamlit dashboard is not implemented yet.
* Reconciliation confirmation/rejection events are not implemented yet.
* Bank import currently writes directly to bank tables instead of using bank import events.
* Split reconciliation intentionally supports only two or three ledger components.
* README quickstart will need final polish after CLI and dashboard work exist.

---

## Development workflow

Typical validation loop:

```bash
python -m pytest
python -m ruff check .
git status
```

One completed build step should usually become one atomic commit.

Example commit messages:

```text
Add trial balance report
Add journal reversal events
Add property-based accounting invariant tests
Add bank CSV import and normalization
Add bank duplicate detection
Add ledger cash movement extraction
Add exact reconciliation matching
Add fuzzy reconciliation scoring
Add split reconciliation matching
```

---

## Safety and data rules

This project should never include:

* Real bank statements
* Real customer data
* Real company data
* API credentials
* Secrets
* Private financial records

All examples should use fake demo data only.

---

## License

License decision is not finalized yet.

---

## Project state

The living source of truth for project progress is:

```text
docs/Reconcile_Project_State.md
```

That file should be updated after every completed build step.
