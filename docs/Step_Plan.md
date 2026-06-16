# Reconcile Step Plan

This plan is phase-based and should be updated when the Project State changes. Step 0 is planning only; no implementation exists yet.

## Phase 0 — Planning

### Step 0 — README-driven planning and Project State

Goal: Define the project before implementation begins.

Major files expected:

- `README.md`
- `docs/Reconcile_Project_State.md`
- `docs/Architecture.md`
- `docs/Event_Model.md`
- `docs/Accounting_Invariants.md`
- `docs/Reconciliation_Design.md`
- `docs/Step_Plan.md`

What not to implement yet:

- Python package structure.
- SQLite schema.
- Event store.
- Tests.
- CLI.
- Dashboard.

Suggested commit message:

```text
Add Reconcile planning docs
```

## Phase 1 — Foundation

### Step 1 — Create project skeleton and tooling baseline

Goal: Create the official folder structure and confirm the basic package imports.

Major files expected:

- `.gitignore`
- `.python-version`, if used
- `pyproject.toml`
- `src/reconcile/__init__.py`
- `tests/test_package_import.py`
- `examples/demo_company/*.csv`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- SQL schema.
- Event store.
- Accounting models.
- Reconciliation logic.
- Dashboard.

Suggested commit message:

```text
Add Reconcile project skeleton and tooling baseline
```

## Phase 2 — Core accounting model

### Step 2 — Add core exceptions and money helpers

Goal: Add custom exceptions and safe integer-cent money parsing/formatting.

Major files expected:

- `src/reconcile/exceptions.py`
- `src/reconcile/money.py`
- `tests/test_money.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Accounts.
- Journal entries.
- Event store.
- Reports.
- Reconciliation.

Suggested commit message:

```text
Add money helpers and custom exceptions
```

### Step 3 — Add account models and chart of accounts validation

Goal: Define account types, normal balance rules, and account validation.

Major files expected:

- `src/reconcile/accounts/__init__.py`
- `src/reconcile/accounts/models.py`
- `tests/test_accounts.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- SQLite account table.
- Account events.
- Journal posting.

Suggested commit message:

```text
Add account models and validation
```

### Step 4 — Add journal entry models and validation

Goal: Define journal entries and protect double-entry rules.

Major files expected:

- `src/reconcile/journal/__init__.py`
- `src/reconcile/journal/models.py`
- `src/reconcile/journal/validation.py`
- `tests/test_journal_models.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Event store.
- SQL persistence.
- Reversals.
- Reports.

Suggested commit message:

```text
Add journal entry models and double-entry validation
```

## Phase 3 — Event store and SQL schema

### Step 5 — Add SQLite schema initialization

Goal: Create database connection helpers and planned MVP tables.

Major files expected:

- `src/reconcile/db.py`
- `tests/test_db_schema.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Event append logic.
- Account service.
- Journal posting service.
- Reconciliation engine.

Suggested commit message:

```text
Add SQLite schema initialization
```

### Step 6 — Add event models and append-only event store

Goal: Implement event append/load behavior and deterministic ordering.

Major files expected:

- `src/reconcile/events/__init__.py`
- `src/reconcile/events/models.py`
- `src/reconcile/events/store.py`
- `tests/test_event_store.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Event handlers.
- Projection rebuild.
- Journal posting.

Suggested commit message:

```text
Add append-only event store
```

## Phase 4 — Chart of accounts

### Step 7 — Add account service and AccountOpened projection

Goal: Open accounts through events and project them into account read models.

Major files expected:

- `src/reconcile/accounts/service.py`
- `src/reconcile/accounts/chart.py`
- `src/reconcile/events/handlers.py`
- `tests/test_account_service.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Journal posting.
- Balance projections.
- Reports.

Suggested commit message:

```text
Add account opening events and projection
```

## Phase 5 — Journal posting and balances

### Step 8 — Add journal posting service and journal projections

Goal: Post valid balanced journal entries through events.

Major files expected:

- `src/reconcile/journal/service.py`
- `src/reconcile/events/handlers.py`
- `tests/test_journal_posting.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Balance projections.
- Reversals.
- Reports.
- Bank reconciliation.

Suggested commit message:

```text
Add journal posting events and projections
```

### Step 9 — Add account balance projections

Goal: Apply posted journal entries to account-balance projections.

Major files expected:

- `src/reconcile/projections/__init__.py`
- `src/reconcile/projections/balances.py`
- `src/reconcile/events/handlers.py`
- `tests/test_account_balances.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Projection rebuild.
- Reports.
- Reversals.

Suggested commit message:

```text
Add account balance projections
```

### Step 10 — Add projection rebuild workflow

Goal: Clear projections and rebuild them from the event log.

Major files expected:

- `src/reconcile/projections/rebuild.py`
- `scripts/rebuild_projections.py`
- `tests/test_projection_rebuild.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Reports.
- Reversals.
- Bank import.

Suggested commit message:

```text
Add projection rebuild workflow
```

## Phase 6 — Reports and reversals

### Step 11 — Add trial balance report

Goal: Generate trial balance data from projections.

Major files expected:

- `src/reconcile/reports/__init__.py`
- `src/reconcile/reports/trial_balance.py`
- `tests/test_reports.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Income statement.
- Balance sheet.
- Cash flow.
- Dashboard.

Suggested commit message:

```text
Add trial balance report
```

### Step 12 — Add income statement and balance sheet reports

Goal: Generate basic financial statements.

Major files expected:

- `src/reconcile/reports/income_statement.py`
- `src/reconcile/reports/balance_sheet.py`
- `tests/test_reports.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Cash flow.
- Dashboard.
- Reconciliation.

Suggested commit message:

```text
Add income statement and balance sheet reports
```

### Step 13 — Add journal reversal behavior

Goal: Reverse posted journal entries through reversal events.

Major files expected:

- `src/reconcile/journal/service.py`
- `src/reconcile/events/handlers.py`
- `tests/test_journal_reversals.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Bank reconciliation.
- Dashboard.
- ML categorization.

Suggested commit message:

```text
Add journal reversal events
```

### Step 14 — Add property-based accounting invariant tests

Goal: Use Hypothesis to test accounting laws across generated ledgers.

Major files expected:

- `tests/property/test_accounting_invariants.py`
- `tests/property/test_replay_invariants.py`
- `tests/property/test_reversal_invariants.py`
- `docs/Accounting_Invariants.md`
- `docs/Reconcile_Project_State.md`
- `pyproject.toml`

What not to implement yet:

- Bank import.
- Reconciliation.
- Dashboard.

Suggested commit message:

```text
Add property-based accounting invariant tests
```

## Phase 7 — Bank import and reconciliation

### Step 15 — Add bank CSV import and normalization

Goal: Import fake bank CSV data and normalize descriptions.

Major files expected:

- `src/reconcile/imports/__init__.py`
- `src/reconcile/imports/bank_csv.py`
- `src/reconcile/imports/normalization.py`
- `tests/test_bank_import.py`
- `examples/demo_company/bank_statement.csv`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Reconciliation matching.
- Categorization.
- Dashboard.

Suggested commit message:

```text
Add bank CSV import and normalization
```

### Step 16 — Add bank duplicate detection

Goal: Detect duplicate imported bank rows without deleting them.

Major files expected:

- `src/reconcile/imports/duplicate_detection.py`
- `src/reconcile/imports/bank_csv.py`
- `tests/test_bank_duplicate_detection.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Reconciliation matching.
- Categorization.
- Dashboard.

Suggested commit message:

```text
Add bank duplicate detection
```

### Step 17 — Add ledger cash movement extraction

Goal: Convert cash-account journal lines into bank-comparable movements.

Major files expected:

- `src/reconcile/reconciliation/__init__.py`
- `src/reconcile/reconciliation/cash_movements.py`
- `tests/test_cash_movements.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Match scoring.
- Split matching.
- Dashboard.

Suggested commit message:

```text
Add ledger cash movement extraction
```

### Step 18 — Add exact reconciliation matching

Goal: Match bank transactions to ledger cash movements using exact amount/date logic.

Major files expected:

- `src/reconcile/reconciliation/models.py`
- `src/reconcile/reconciliation/matcher.py`
- `src/reconcile/reconciliation/explanations.py`
- `tests/test_reconciliation_exact.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Fuzzy scoring.
- Split matching.
- Categorization.

Suggested commit message:

```text
Add exact reconciliation matching
```

### Step 19 — Add fuzzy reconciliation scoring and ambiguity handling

Goal: Score amount/date/description candidates and prevent unsafe auto-matches.

Major files expected:

- `src/reconcile/reconciliation/scoring.py`
- `src/reconcile/reconciliation/matcher.py`
- `src/reconcile/reconciliation/explanations.py`
- `tests/test_reconciliation_fuzzy.py`
- `docs/Reconciliation_Design.md`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Split matching.
- Manual review UI.
- ML categorization.

Suggested commit message:

```text
Add fuzzy reconciliation scoring
```

### Step 20 — Add split reconciliation matching

Goal: Match one bank transaction to two or three ledger cash movements.

Major files expected:

- `src/reconcile/reconciliation/splits.py`
- `src/reconcile/reconciliation/matcher.py`
- `tests/test_reconciliation_splits.py`
- `docs/Reconciliation_Design.md`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Unlimited subset-sum.
- Many bank transactions to one ledger entry.
- Dashboard.

Suggested commit message:

```text
Add split reconciliation matching
```

## Phase 8 — Interfaces, categorization, and dashboard

### Step 21 — Add CLI workflow

Goal: Add a thin CLI that wires together tested workflows.

Major files expected:

- `src/reconcile/cli.py`
- `scripts/run_reconcile.py`
- `tests/test_cli.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Streamlit dashboard.
- Rule-based categorization.
- ML classifier.

Suggested commit message:

```text
Add Reconcile CLI workflow
```

### Step 22 — Add report exports and sample outputs

Goal: Export reports and reconciliation results to stable output files.

Major files expected:

- `src/reconcile/reports/export.py`
- `examples/sample_output/`
- `tests/test_report_exports.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Dashboard.
- Cash flow.
- ML categorization.

Suggested commit message:

```text
Add report exports and sample outputs
```

### Step 23 — Add rule-based categorization

Goal: Add deterministic category rules for imported bank transactions.

Major files expected:

- `src/reconcile/categorization/__init__.py`
- `src/reconcile/categorization/rules.py`
- `tests/test_categorization_rules.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- scikit-learn classifier.
- Dashboard categorization review.

Suggested commit message:

```text
Add rule-based categorization
```

### Step 24 — Add correction storage and optional local classifier

Goal: Add user correction tracking and optional local ML categorization.

Major files expected:

- `src/reconcile/categorization/corrections.py`
- `src/reconcile/categorization/classifier.py`
- `tests/test_categorization_classifier.py`
- `pyproject.toml`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- External APIs.
- LLM categorization.
- Cloud model calls.

Suggested commit message:

```text
Add local categorization corrections and classifier
```

### Step 25 — Add cash flow report

Goal: Add a direct-method cash flow report.

Major files expected:

- `src/reconcile/reports/cash_flow.py`
- `tests/test_cash_flow_report.py`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- Complex indirect-method cash flow.
- Statement of retained earnings.

Suggested commit message:

```text
Add direct-method cash flow report
```

### Step 26 — Add Streamlit dashboard foundation

Goal: Add a basic Streamlit dashboard shell connected to fake demo data.

Major files expected:

- `dashboard/streamlit_app.py`
- `docs/Reconcile_Project_State.md`
- `pyproject.toml`

What not to implement yet:

- Full report pages.
- Reconciliation review UI.
- Categorization review UI.

Suggested commit message:

```text
Add Streamlit dashboard foundation
```

### Step 27 — Add dashboard report pages and event timeline

Goal: Display point-in-time reports and event history in Streamlit.

Major files expected:

- `dashboard/streamlit_app.py`
- `docs/Reconcile_Project_State.md`
- `README.md`

What not to implement yet:

- Reconciliation review UI.
- Categorization review UI.
- Cloud deployment.

Suggested commit message:

```text
Add Streamlit reports and event timeline
```

### Step 28 — Add dashboard reconciliation and categorization review

Goal: Add review screens for reconciliation matches and categorization decisions.

Major files expected:

- `dashboard/streamlit_app.py`
- `docs/Reconcile_Project_State.md`
- `README.md`

What not to implement yet:

- Production user workflow.
- Auth.
- Real bank APIs.

Suggested commit message:

```text
Add Streamlit reconciliation and categorization review
```

## Phase 9 — CI and final polish

### Step 29 — Add CI workflow

Goal: Add GitHub Actions for automated tests and linting.

Major files expected:

- `.github/workflows/ci.yml`
- `docs/Reconcile_Project_State.md`
- `README.md`

What not to implement yet:

- Deployment automation.
- Production hosting.

Suggested commit message:

```text
Add CI workflow
```

### Step 30 — Polish README and architecture docs

Goal: Make docs match the actual behavior after implementation exists.

Major files expected:

- `README.md`
- `docs/Architecture.md`
- `docs/Event_Model.md`
- `docs/Accounting_Invariants.md`
- `docs/Reconciliation_Design.md`
- `docs/Step_Plan.md`
- `docs/Reconcile_Project_State.md`

What not to implement yet:

- New major features.
- README fiction.

Suggested commit message:

```text
Polish Reconcile documentation
```

### Step 31 — Final portfolio polish and release cleanup

Goal: Prepare Reconcile as a finished portfolio project.

Major files expected:

- `README.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `docs/Reconcile_Project_State.md`
- `examples/sample_output/`

What not to implement yet:

- New major features outside the accepted scope.
- Real bank data.
- Production-only features.

Suggested commit message:

```text
Finalize Reconcile portfolio project
```
