# Reconcile

Reconcile is a local-first Python accounting engine that uses
event-sourced double-entry bookkeeping, rebuildable SQLite projections,
property-tested accounting invariants, explainable bank reconciliation,
deterministic categorization, and financial statement exports.

It is built as a portfolio project for accounting, finance, data, and
software engineering roles.

The project focuses on a practical accounting systems problem:

> Small-business accounting data needs to be accurate, auditable,
> explainable, and reconcilable. Reconcile records accounting actions as
> immutable events, rebuilds financial state from those events, and
> reconciles imported bank activity against ledger cash movements.

---

## Current status

Reconcile is in active development.

Current completed milestone:

```text
Step 25 — Add cash flow report
```

Approximate project completion:

```text
83% to 85%
```

Current validation status:

```text
709 tests passed locally
ruff clean locally
```

The core Python engine is largely complete. Reconcile now has the
event-sourced ledger, accounting projections, financial reports, bank
import, exact/fuzzy/split reconciliation, categorization, correction
storage, local classifier behavior, CLI workflows, CSV exports, fake
sample outputs, and direct-method cash flow reporting.

Remaining planned work is mostly dashboard, CI, documentation, and final
portfolio polish.

---

## What Reconcile does today

Reconcile currently supports:

- Opening accounts through immutable accounting events.
- Posting balanced double-entry journal entries.
- Rejecting invalid or unbalanced journal entries.
- Building account-balance projections.
- Rebuilding projections from the append-only event log.
- Generating a trial balance.
- Generating an income statement.
- Generating a balance sheet.
- Generating a direct-method cash flow statement.
- Reversing posted journal entries through immutable reversal events.
- Running property-based accounting invariant tests with Hypothesis.
- Importing fake bank statement CSV data.
- Normalizing bank transaction descriptions.
- Detecting and flagging duplicate imported bank transactions.
- Extracting ledger cash movements from selected cash accounts.
- Running exact reconciliation matching.
- Running fuzzy reconciliation scoring.
- Detecting ambiguous reconciliation candidates.
- Running limited split reconciliation matching.
- Storing reconciliation runs, match records, match explanations, and
  ledger-link rows.
- Applying deterministic rule-based categorization.
- Recording append-only categorization corrections.
- Training a small local standard-library classifier from corrections.
- Applying categorization precedence:
  correction, then rule, then confident classifier, then uncategorized.
- Exporting trial balance, income statement, balance sheet, cash flow,
  and reconciliation results to CSV.
- Running core workflows through a thin `argparse` CLI.

---

## Why this project exists

Accounting systems are not just CRUD apps.

A useful accounting engine needs to preserve history, prove entries
balance, rebuild derived state, explain reconciliation decisions, and
avoid unsafe automatic matches.

Reconcile demonstrates those ideas in a small, local-first Python project.

The goal is not to replace QuickBooks, Xero, or an ERP. The goal is to
show a clear, testable accounting engine with the kind of design choices
used in real accounting and fintech systems:

- Append-only event history
- Double-entry validation
- Reversal entries instead of mutation
- Rebuildable projections
- Integer-cents money handling
- Point-in-time financial reports
- Direct-method cash flow reporting
- Explainable reconciliation logic
- Deterministic categorization with correction precedence
- Property-based invariant tests

---

## Portfolio summary

Resume-style summary:

> Built Reconcile, an event-sourced double-entry general ledger engine in
> Python and SQLite with immutable journal events, projection replay,
> point-in-time financial statements, direct-method cash flow reporting,
> bank reconciliation, categorization correction tracking, and
> property-based accounting invariant tests.

Longer explanation:

> Reconcile is a local-first Python accounting engine that records
> accounting actions as append-only events, projects those events into SQL
> read models, generates financial statements, imports bank transactions,
> extracts ledger cash movements, reconciles bank activity against the
> ledger with exact/fuzzy/split explanations, and exports fake sample
> outputs for portfolio review.

---

## Tech stack

Runtime:

- Python
- SQLite
- Standard library CSV, JSON, argparse, pathlib, and datetime tooling

Testing and tooling:

- pytest
- Hypothesis
- ruff

Planned for remaining work:

- Streamlit for the dashboard
- pandas only where useful for dashboard display
- plotly only if dashboard charts justify it

Not currently used:

- scikit-learn
- LLMs
- external APIs
- cloud database

Step 24 intentionally used a small standard-library classifier instead
of adding scikit-learn.

---

## Design principles

Reconcile follows these project rules:

- Use integer cents for money.
- Never use floats for money.
- Keep the project local-first.
- Keep sample data fake.
- Keep the event store append-only.
- Treat projections as rebuildable derived state.
- Use reversal events for accounting corrections.
- Do not directly mutate posted accounting history.
- Make reconciliation decisions explainable.
- Keep dashboard and CLI code thin.
- Keep business logic inside importable package modules.
- Add tests with every meaningful feature.

Core architecture rule:

```text
If a feature changes financial state, it must do so through an event.
```

Reconciliation rule:

```text
If the program makes a match decision, store why it made that decision.
```

---

## Quickstart

Install the project in editable mode with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the test suite:

```bash
python -m pytest
```

Run linting:

```bash
python -m ruff check .
```

Create a fresh local demo database:

```bash
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db
```

Seed fake demo accounting data:

```bash
python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db
```

Rebuild projections from the event log:

```bash
python scripts/run_reconcile.py rebuild-projections --db-path exports/reconcile.db
```

Run reports:

```bash
python scripts/run_reconcile.py report trial-balance --db-path exports/reconcile.db
python scripts/run_reconcile.py report income-statement --db-path exports/reconcile.db --from 2026-01-01 --to 2026-01-31
python scripts/run_reconcile.py report balance-sheet --db-path exports/reconcile.db --as-of 2026-01-31
python scripts/run_reconcile.py report cash-flow --db-path exports/reconcile.db --from 2026-01-01 --to 2026-01-31
```

Import the fake demo bank statement:

```bash
python scripts/run_reconcile.py import-bank examples/demo_company/bank_statement.csv --db-path exports/reconcile.db
```

Run reconciliation:

```bash
python scripts/run_reconcile.py reconcile exact --db-path exports/reconcile.db --cash-account-id acct-cash --from 2026-01-01 --to 2026-01-31
python scripts/run_reconcile.py reconcile fuzzy --db-path exports/reconcile.db --cash-account-id acct-cash --from 2026-01-01 --to 2026-01-31
python scripts/run_reconcile.py reconcile split --db-path exports/reconcile.db --cash-account-id acct-cash --from 2026-01-01 --to 2026-01-31
```

Export fake sample reports:

```bash
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output --from 2026-01-01 --to 2026-01-31 --as-of 2026-01-31
```

Do not commit `exports/reconcile.db`. It is a local generated database.

---

## CLI commands

Current CLI commands:

```text
init-db
seed-demo
rebuild-projections
report trial-balance
report income-statement
report balance-sheet
report cash-flow
import-bank
reconcile exact
reconcile fuzzy
reconcile split
export-reports
```

The CLI is intentionally thin. It parses arguments, opens the database,
calls package functions, and prints concise plain-text output.

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

Fake sample output files live under:

```text
examples/sample_output/
```

Current sample outputs:

```text
examples/sample_output/trial_balance.csv
examples/sample_output/income_statement.csv
examples/sample_output/balance_sheet.csv
examples/sample_output/cash_flow.csv
```

All sample data is fake and safe to commit.

No real bank data, customer data, private financial data, or credentials
should be added to this repository.

---

## Implemented modules

Core modules currently include:

```text
src/reconcile/db.py
src/reconcile/exceptions.py
src/reconcile/money.py
src/reconcile/cli.py
src/reconcile/accounts/
src/reconcile/events/
src/reconcile/journal/
src/reconcile/projections/
src/reconcile/imports/
src/reconcile/reconciliation/
src/reconcile/reports/
src/reconcile/categorization/
```

Important package responsibilities:

- `events/` owns append-only event models and event storage.
- `accounts/` owns account models and account-opening behavior.
- `journal/` owns journal models, posting, validation, and reversals.
- `projections/` owns derived account balance and rebuild behavior.
- `reports/` owns trial balance, income statement, balance sheet, cash
  flow, and CSV exports.
- `imports/` owns bank CSV import, normalization, hashing, and duplicate
  detection.
- `reconciliation/` owns cash movement extraction and exact/fuzzy/split
  reconciliation.
- `categorization/` owns deterministic rules, corrections, and the local
  classifier.
- `cli.py` owns command-line argument parsing and workflow coordination.

---

## Current test suite

The test suite currently covers:

- Package import smoke test
- Money parsing and formatting
- Account model validation
- Journal model validation
- SQLite schema creation
- Event store behavior
- Account opening
- Journal posting
- Account balance projections
- Projection rebuilds
- Trial balance reports
- Income statement reports
- Balance sheet reports
- Journal reversals
- Property-based accounting invariants
- Bank CSV import
- Bank duplicate detection
- Ledger cash movement extraction
- Exact reconciliation matching
- Fuzzy reconciliation scoring
- Split reconciliation matching
- CLI workflows
- Report exports
- Rule-based categorization
- Categorization corrections
- Local categorization classifier behavior
- Direct-method cash flow reporting

Standard validation commands:

```bash
python -m pytest
python -m ruff check .
```

Latest local Step 25 validation:

```text
python -m pytest        # 709 passed
python -m ruff check .  # All checks passed
```

---

## Accounting behavior

### Double-entry accounting

Every posted journal entry must:

- have at least two lines,
- use only debit or credit sides,
- use positive integer-cent line amounts,
- reference valid active accounts,
- balance total debits and total credits.

Invalid entries fail before reaching the event store.

### Reversals

Posted entries are corrected through reversing entries, not mutation.

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

### Reports

Implemented reports:

- Trial balance
- Income statement
- Balance sheet
- Direct-method cash flow statement

Reports read existing ledger projections and journal lines. They do not
append events, rebuild projections, import files, run reconciliation, or
mutate accounting tables.

---

## Reconciliation behavior

Bank transactions use bank-sign convention:

```text
Deposit / inflow     = positive amount
Withdrawal / outflow = negative amount
```

Ledger cash movements use bank-comparable convention:

```text
Debit to Cash   = positive amount
Credit from Cash = negative amount
```

Implemented reconciliation modes:

- Exact matching
- Fuzzy amount/date/description matching
- Ambiguous candidate handling
- Limited split matching for one bank transaction to two or three ledger
  cash movements

Match records include:

- match type,
- status,
- score,
- amount delta,
- date delta,
- explanation JSON,
- ledger-link rows for auto-matches.

Duplicate-flagged bank transactions are not unsafe auto-matched.

---

## Categorization behavior

Implemented categorization layers:

```text
1. Latest user correction
2. Rule-based categorization
3. Confident local classifier prediction
4. Uncategorized
```

The classifier is local-only, deterministic, standard-library based, and
not persisted to disk.

Categorization does not mutate imported bank transaction rows.

---

## Known accounting refinement before final polish

The current direct-method cash flow classifier follows the Step 25 rule:

```text
Revenue and expense counterparties -> operating
Non-cash asset counterparties      -> investing
Liability counterparties           -> financing
Equity counterparties              -> financing
```

That rule is simple and deterministic, but it creates one accounting
refinement to address before the final release:

> Accounts Receivable collections should usually be operating cash flow,
> not investing cash flow.

In the current sample output, a customer payment or receivable collection
may appear as investing because Accounts Receivable is an asset account.
Before the final documentation/dashboard polish, the cash flow
classification should be refined so ordinary operating working-capital
asset accounts, especially Accounts Receivable, classify as operating.

This is not a ledger integrity issue. It is a cash-flow presentation
refinement.

---

## Current limitations

Current limitations are intentional while the project is still under
development:

- Streamlit dashboard is not implemented yet.
- Dashboard report pages are not implemented yet.
- Dashboard reconciliation and categorization review are not implemented
  yet.
- GitHub Actions CI is not implemented yet.
- Manual reconciliation confirmation/rejection events are not implemented
  yet.
- Bank import currently writes directly to bank tables instead of using
  bank import events.
- Split reconciliation intentionally supports only two or three ledger
  components.
- Cash flow classification needs a final accounting refinement for
  Accounts Receivable and similar operating working-capital accounts.
- README and architecture docs need final polish after dashboard work
  exists.

---

## Roadmap

### Completed

- Step 0 — Planning and project state
- Step 1 — Project skeleton and tooling baseline
- Step 2 — Exceptions and money helpers
- Step 3 — Account models and chart validation
- Step 4 — Journal entry models and validation
- Step 5 — SQLite schema initialization
- Step 6 — Event models and append-only event store
- Step 7 — Account service and AccountOpened projection
- Step 8 — Journal posting service and journal projections
- Step 9 — Account balance projections
- Step 10 — Projection rebuild workflow
- Step 11 — Trial balance report
- Step 12 — Income statement and balance sheet reports
- Step 13 — Journal reversal behavior
- Step 14 — Property-based accounting invariant tests
- Step 15 — Bank CSV import and normalization
- Step 16 — Bank duplicate detection
- Step 17 — Ledger cash movement extraction
- Step 18 — Exact reconciliation matching
- Step 19 — Fuzzy reconciliation scoring and ambiguity handling
- Step 20 — Split reconciliation matching
- Step 21 — CLI workflow
- Step 22 — Report exports and sample outputs
- Step 23 — Rule-based categorization
- Step 24 — Correction storage and local classifier
- Step 25 — Direct-method cash flow report

### Remaining

#### Step 26 — Streamlit dashboard foundation

Planned:

- Add Streamlit dependency.
- Add dashboard shell.
- Add database path selector or default demo database.
- Add overview page.
- Show high-level account balances and project status.
- Keep dashboard logic thin.

#### Step 27 — Dashboard report pages and event timeline

Planned:

- Trial balance page
- Income statement page
- Balance sheet page
- Cash flow page
- Event timeline page
- Date or event-sequence selectors

#### Step 28 — Dashboard reconciliation and categorization review

Planned:

- Bank transaction review
- Reconciliation match review
- Score and explanation display
- Ambiguous candidate display
- Categorization source and reason display

#### Step 29 — CI workflow

Planned:

- Add GitHub Actions.
- Run pytest.
- Run ruff.
- Confirm CI passes.

#### Step 30 — README and architecture documentation polish

Planned:

- Polish README quickstart.
- Update architecture docs.
- Update event model docs.
- Update accounting invariant docs.
- Update reconciliation design docs.
- Add screenshots if dashboard exists.
- Make docs match actual behavior.

#### Step 31 — Final portfolio cleanup

Planned:

- Final README review.
- Final docs review.
- Final CHANGELOG update.
- Final CONTRIBUTING update.
- Final smoke checks.
- Final sample outputs.
- Confirm no secrets or real data.
- Mark project complete.

---

## Non-goals

The MVP does not include:

- Payroll
- Tax engine
- Sales tax logic
- Income tax logic
- Inventory accounting
- Multi-currency
- Bank APIs
- Plaid integration
- External APIs
- Scraping
- LLM dependencies
- Cloud database
- Production deployment requirement
- Authentication
- User accounts
- Full AR/AP subledger
- Invoice generation
- Payment processing
- Real company data
- Real bank data
- Direct mutation of posted accounting history
- Unlimited subset-sum reconciliation search

---

## Development workflow

Typical validation loop:

```bash
python -m pytest
python -m ruff check .
git status
```

One completed build step should usually become one atomic commit.

Recent commit message examples:

```text
Add report exports and sample outputs
Add rule-based categorization
Add categorization corrections and local classifier
Add direct-method cash flow report
```

---

## Safety and data rules

This project should never include:

- Real bank statements
- Real customer data
- Real company data
- API credentials
- Secrets
- Private financial records
- Pickled model files
- Local generated SQLite databases

All examples should use fake demo data only.

Do not commit:

```text
exports/reconcile.db
.pytest_cache/
__pycache__/
*.pyc
*.pkl
*.joblib
.env
```

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
