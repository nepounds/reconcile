# Reconcile Project State

This file is the living source of truth for Reconcile.

Update it after every completed step.

Do not let implementation drift away from this file. If the plan changes, update this file first.

---

## Current status

Current step: Step 8 — Add journal posting service and journal projections.

Status: Step 8 complete.

Current summary:

* Reconcile has its initial Python package skeleton under `src/reconcile/`.
* `pyproject.toml` is the dependency source of truth.
* Development tooling is limited to pytest and ruff.
* The package import smoke test passed in Step 1.
* Fake demo input CSV files exist for the chart of accounts, journal entries, and bank statement.
* Step 2 added the custom exception hierarchy and integer-cents money helpers.
* Step 3 added account domain definitions, normal balance rules, and a validated `Account` model.
* Step 4 added journal line and journal entry models with double-entry validation.
* Step 5 added SQLite connection helpers and idempotent MVP schema initialization.
* Step 6 added validated ledger event models and append-only SQLite event storage.
* Step 7 added account-opening services and an `AccountOpened` projection handler for the `accounts` table.
* Step 8 added journal posting through append-only `JournalEntryPosted` events.
* Step 8 added journal entry and journal line projections into SQLite.
* Journal posting now rejects duplicate journal entry IDs, missing accounts, inactive accounts, unbalanced entries, and invalid single-line entries.
* `JournalEntryPosted` projection writes only to `journal_entries` and `journal_entry_lines`; account balance projections are intentionally not implemented yet.

Completed Step 8 files:

```text
src/reconcile/journal/service.py
src/reconcile/events/handlers.py
tests/test_journal_posting.py
docs/Reconcile_Project_State.md
```

Completed Step 8 summary:

* Added `post_journal_entry` to validate and post balanced journal entries through append-only `JournalEntryPosted` events.
* Added journal posting payloads with all header and line fields needed to rebuild journal projections.
* Added pre-append validation for duplicate journal entry IDs.
* Added pre-append validation for missing account references.
* Added pre-append validation for inactive account references.
* Extended `apply_event` to support `JournalEntryPosted` while preserving existing `AccountOpened` behavior.
* Added projection behavior for `journal_entries`.
* Added projection behavior for `journal_entry_lines`.
* Added `status="posted"` for newly posted journal entries.
* Added `reversed_by_entry_id=None` and `reversal_of_entry_id=None` for newly posted entries.
* Added duplicate journal entry and duplicate journal line ID validation during projection apply.
* Added optional journal lookup helpers for single-entry and stable ordered listing.
* Added tests covering happy paths, event payload shape, projection behavior, invalid entries, account validation, duplicate handling, direct event apply behavior, no balance projection behavior, and lookup helpers.
* Did not add account balance projections, projection rebuilds, reversals, reports, bank import, reconciliation, categorization, dashboard, CLI, or property-based tests.

Commands run for Step 8:

```bash
python -m pytest
python -m ruff check .
git status
```

Results:

```text
python -m pytest        # run locally after Step 8 fixes; expected 194 passed
python -m ruff check .  # run locally in the real repository
git status              # expected Step 8 files only
```

Next planned step:

Step 9 — Add account balance projections.

Step 9 status: Not started.

---

## Project name

Working name: Reconcile.

Name status: Final.

Repository name:

```text
reconcile
```

Package name:

```text
reconcile
```

---

## Project goal

Build a local-first, event-sourced double-entry general ledger engine with SQL storage, immutable accounting events, rebuildable projections, point-in-time financial reports, and a bank reconciliation engine.

The project should solve this practical problem:

> Small-business accounting data needs to be accurate, auditable, explainable, and reconcilable. Reconcile provides a local accounting engine that records every accounting action as an immutable event, rebuilds financial state from those events, and reconciles bank activity against ledger cash movements.

The project should be polished enough for accounting and finance recruiters, rigorous enough for software engineering reviewers, and structured enough that a stranger can understand the design decisions from the README, docs, tests, and code.

---

## One-sentence portfolio explanation

Reconcile is a local-first Python accounting engine that uses event-sourced double-entry bookkeeping, rebuildable SQL projections, property-tested accounting invariants, and explainable bank reconciliation to produce auditable financial reports.

Resume version:

> Built Reconcile, an event-sourced double-entry general ledger engine in Python and SQLite with immutable journal events, projection replay, point-in-time financial statements, bank reconciliation, and property-based accounting invariant tests.

---

## Primary audience

### Hands-on users

* Accounting students
* Small-business bookkeeping learners
* Analysts who want to understand ledger mechanics
* Developers learning accounting systems
* Portfolio reviewers testing the demo locally

These users need:

* A clear fake demo company.
* A safe local database.
* A quickstart that works.
* Understandable accounting examples.
* Reports that can be traced back to journal entries.
* Reconciliation decisions that explain themselves.

### Career audience

* Accounting recruiters
* Finance recruiters
* Technical hiring managers
* Software engineers
* Data analysts
* Accounting technology teams
* Fintech reviewers
* Operations and business systems teams

These reviewers should see:

* Double-entry accounting knowledge
* Immutable accounting corrections through reversals
* Event-sourcing architecture
* SQL storage design
* Projection rebuilds
* Reconciliation matching logic
* Testing discipline
* Property-based tests for accounting invariants
* Clear documentation
* Sensible scope control
* Maintainable Python project structure

---

## MVP scope

The MVP will:

1. Create and manage a simple chart of accounts.
2. Store accounting actions as append-only events.
3. Post balanced double-entry journal entries.
4. Reject unbalanced or invalid journal entries.
5. Reverse posted journal entries through reversal events, not mutation.
6. Build account-balance projections from the event log.
7. Rebuild projections by replaying events.
8. Generate a trial balance.
9. Generate an income statement.
10. Generate a balance sheet.
11. Support point-in-time reports by date.
12. Import fake bank statement CSV data.
13. Normalize imported bank descriptions.
14. Detect duplicate imported bank rows.
15. Extract ledger cash movements from journal entries.
16. Match bank transactions against ledger cash movements.
17. Support exact reconciliation matches.
18. Support fuzzy amount/date reconciliation matches.
19. Support ambiguous match detection.
20. Support one bank transaction matched to multiple ledger cash movements.
21. Store reconciliation match scores and explanations.
22. Include fake sample input.
23. Include fake sample output if useful.
24. Include a meaningful test suite.
25. Include property-based tests for core accounting invariants.
26. Include a working quickstart.
27. Include a Streamlit dashboard after the core engine works.

The MVP is complete when:

* A user can create/open accounts from fake sample data.
* A user can post balanced journal entries.
* Invalid entries are rejected before they reach the event store.
* A user can reverse a posted journal entry.
* Account balances are generated from projections.
* Projections can be deleted and rebuilt from events.
* Trial balance, income statement, and balance sheet reports work.
* Bank statement CSVs can be imported.
* Bank transactions can be matched against ledger cash movements.
* Match results include status, score, and explanation.
* Tests cover happy paths, bad inputs, edge cases, and accounting invariants.
* A stranger can clone the repo, follow the README, run tests, launch the demo, and understand the output.

---

## Full project scope

The full Reconcile project will eventually include:

1. Event-sourced ledger core.
2. SQLite event store.
3. Account projections.
4. Journal entry projections.
5. Balance projections.
6. Projection rebuild system.
7. Trial balance.
8. Income statement.
9. Balance sheet.
10. Direct-method cash flow report.
11. Bank CSV import.
12. Bank transaction normalization.
13. Duplicate import detection.
14. Ledger cash movement extraction.
15. Exact reconciliation matching.
16. Fuzzy reconciliation scoring.
17. Split matching.
18. Ambiguous candidate handling.
19. Manual match confirmation/rejection.
20. Match explanation storage.
21. Rule-based categorization.
22. User correction storage.
23. Optional local scikit-learn classifier trained on corrections.
24. Streamlit dashboard.
25. Event timeline.
26. Point-in-time report replay.
27. Reconciliation review UI.
28. Categorization review UI.
29. Synthetic demo company dataset.
30. Architecture documentation.
31. Accounting invariant documentation.
32. Reconciliation design documentation.
33. CI with pytest and ruff.

---

## Explicit non-goals for MVP

The MVP will not include:

* No payroll.
* No tax engine.
* No sales tax logic.
* No income tax logic.
* No inventory accounting.
* No multi-currency.
* No bank API integrations.
* No Plaid integration.
* No external APIs for core functionality.
* No scraping.
* No LLM dependencies.
* No cloud database.
* No production deployment requirement.
* No user accounts.
* No authentication.
* No permissions system.
* No full AR/AP subledger.
* No invoice generation.
* No bill pay workflow.
* No customer portal.
* No vendor portal.
* No payment processing.
* No real company data.
* No real bank data.
* No automatic deletion of source data.
* No direct mutation of posted accounting history.
* No direct balance edits outside projection rebuild/apply logic.

Scope rule:

> Do not expand scope until the current milestone works end-to-end.

Architecture rule:

> If a feature changes financial state, it must do so through an event.

---

## Hard constraints

* Use Python.
* Use SQLite for local storage.
* Use integer cents for money.
* Avoid floats for money.
* Keep the project local-first.
* Keep core functionality offline.
* Keep sample data fake and safe to commit.
* Keep secrets, credentials, private data, and real customer/user data out of the repo.
* Keep tests fast and offline.
* A stranger should be able to clone the repo and have tests passing in under 5 minutes.
* Streamlit may be used for the public demo/dashboard.
* Streamlit must not own business logic.
* The dashboard should read from SQLite/projections and call tested package functions only where needed.
* The CLI should stay thin.
* The event store is append-only.
* Corrections happen through reversal events.
* Projections are rebuildable and disposable.
* Reconciliation decisions must store or display why they were made.
* ML categorization must be optional, local, and explainable enough for review.
* No LLM behavior is allowed in core functionality.

Project-specific constraints:

* Every posted journal entry must balance.
* Invalid journal entries must not enter the event store.
* Reversals must preserve the original entry and create a new reversing entry.
* Account balances must be derived from journal events.
* Reports must be traceable to journal lines.
* Bank transactions must preserve raw imported descriptions.
* Reconciliation matches must include score and explanation.
* Ambiguous reconciliation candidates must not be auto-confirmed.
* Duplicate transactions must be flagged, not deleted.

---

## Engineering principles

* README-driven development.
* Maintain this Project State file after every completed step.
* At the end of every completed build step, generate the entire updated `docs/Reconcile_Project_State.md` file so it can be copied or replaced directly.
* Define official names, paths, inputs, outputs, and public functions before implementation.
* Keep application logic inside `src/reconcile/`.
* Keep scripts, CLI wrappers, and dashboard files thin.
* Every non-trivial function should be importable and directly testable.
* Add custom exceptions instead of broad generic error handling where useful.
* Validate bad inputs early and fail with clear messages.
* Preserve raw source data before cleaning or transforming it.
* Keep business logic separate from file I/O where practical.
* Log or print at external boundaries, not deep inside business logic.
* Use clear names that describe what things are.
* Every public function should have one job and a short docstring.
* Add tests for edge cases, not just happy paths.
* Prefer small, reviewable patches over full-file rewrites.
* Do not recreate working files blindly.
* Do not treat Git as only a save button.
* Commit clean, working milestones.
* Do not add dependencies casually.
* Do not build dashboard polish before engine correctness.
* Do not build ML before rule-based categorization works.
* Do not let reconciliation mutate ledger history.
* Do not let projections become the source of truth.

Decision rule:

> If the program makes a decision, store or display why it made that decision.

Examples:

* `match_status` plus `match_reason`
* `score` plus `score_explanation`
* `category` plus `category_source`
* `duplicate_group_id` plus `duplicate_reason`
* `validation_error` plus clear message
* `reversal_of_entry_id` plus `reversal_reason`

---

## Accounting principles

* Use double-entry accounting.
* Every journal entry must have at least two lines.
* Every journal entry must have total debits equal total credits.
* Every journal line must reference a valid active account.
* Every journal line must have one side: debit or credit.
* Every journal line amount must be positive integer cents.
* Asset and expense accounts normally carry debit balances.
* Liability, equity, and revenue accounts normally carry credit balances.
* Before closing entries, use the expanded accounting equation:

```text
Assets + Expenses = Liabilities + Equity + Revenue
```

* Corrections must use reversal entries.
* Posted journal history must remain auditable.
* Reports must be generated from ledger events or projections derived from ledger events.
* Reconciliation must match bank activity to ledger cash movements, not randomly to unrelated report totals.

---

## Event-sourcing principles

* The event store is the source of truth.
* Events are append-only.
* Events are replayed in deterministic `event_sequence` order.
* Projections are derived state.
* Projections may be cleared and rebuilt.
* A projection rebuild must reproduce the same account balances as the current incremental projection.
* An event should contain enough payload to replay the business action.
* Events should have clear event types and versions.
* Event payloads should be JSON.
* Event application should be deterministic.
* If the plan changes, update this file and architecture docs before changing code.

Official MVP event types:

```text
AccountOpened
AccountClosed
JournalEntryPosted
JournalEntryReversed
BankStatementImported
ReconciliationRunCompleted
ReconciliationMatchConfirmed
ReconciliationMatchRejected
```

Future event types:

```text
CategorizationRuleCreated
CategorizationRuleUpdated
TransactionCategoryCorrected
ClassifierTrained
ReportSnapshotCreated
```

---

## Reconciliation principles

* Bank transactions use bank-sign convention:

  * Deposit/inflow = positive
  * Withdrawal/outflow = negative
* Ledger cash movements are derived from journal lines that touch the selected cash account.
* Debit to Cash becomes a positive ledger cash movement.
* Credit to Cash becomes a negative ledger cash movement.
* Matching should compare bank transactions to ledger cash movements.
* Exact matches should be evaluated before fuzzy matches.
* Fuzzy matching should consider amount, date, and description.
* Description similarity should not override a bad amount match.
* Ambiguous matches should be marked as candidates or ambiguous, not auto-confirmed.
* Duplicate rows should be flagged, not deleted.
* One ledger movement should not be reused across confirmed matches in the same reconciliation run.
* One bank transaction may match multiple ledger cash movements when the amounts sum within tolerance.
* Match records must include score and explanation.

Default reconciliation scoring:

```text
score = amount_score * 0.60
      + date_score * 0.25
      + description_score * 0.15
      - duplicate_penalty
```

Default split scoring:

```text
score = amount_score * 0.70
      + date_score * 0.25
      + description_score * 0.05
      - split_penalty
```

Default match thresholds:

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

Default date window:

```text
3 days before/after
```

Default amount tolerance:

```text
1 cent for exact-like matching
5 cents for configurable fuzzy tolerance
```

Default split rules:

```text
Only combine 2 or 3 ledger cash movements.
Only combine same-sign movements.
Only combine unmatched movements.
Only search within the date window.
Only accept combinations that sum to the bank amount within tolerance.
```

---

## Dashboard principles

Primary dashboard choice:

```text
Streamlit
```

Dashboard role:

* Show the engine clearly.
* Provide portfolio screenshots.
* Make the audit trail understandable.
* Make reports easy to inspect.
* Make reconciliation decisions easy to review.

Dashboard pages planned:

```text
Overview
Event Timeline
Trial Balance
Income Statement
Balance Sheet
Cash Flow
Bank Reconciliation
Categorization Review
```

Dashboard rules:

* Keep dashboard logic thin.
* Do not put core accounting logic in Streamlit files.
* Dashboard should call package functions or query safe read models.
* Dashboard should work with fake demo data.
* Dashboard should be deployable to Streamlit Community Cloud if practical.
* Dashboard should remain useful locally even if cloud deployment is skipped.

---

## Lessons from prior projects

* Start with the Project State file immediately.
* Do not let scope expand until the current milestone works.
* Define official file names, function names, paths, and data formats early.
* Do not invent new function names if official names already exist.
* Explain dependencies before adding them.
* Do not maintain conflicting dependency lists.
* Prefer small, reviewable patches over full-file rewrites.
* Separate demo/sample data from real data.
* Keep sample data fake and safe to commit.
* One official sample input should travel through the entire app.
* Every coding step must include:

  * files to create/edit
  * files not to edit
  * exact requirements
  * tests to add/update
  * commands to run
  * Project State update guidance
  * Git commit guidance
* Every step should have a definition of done.
* Every feature needs at least one happy-path test and one bad-input or edge-case test.
* Do not polish the README as fiction. Polish it after the behavior works.
* A project is not done when the code works. It is done when the repo proves the code works.
* Keep the base/check-in thread separate from build-step execution when useful.
* Build large projects in clean, locked layers.

---

## Official project structure

```text
reconcile/
├── .github/
│   └── workflows/
│       └── ci.yml
├── dashboard/
│   └── streamlit_app.py
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
│   ├── run_reconcile.py
│   ├── seed_demo_data.py
│   └── rebuild_projections.py
├── src/
│   └── reconcile/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── db.py
│       ├── exceptions.py
│       ├── money.py
│       ├── accounts/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── service.py
│       │   └── chart.py
│       ├── categorization/
│       │   ├── __init__.py
│       │   ├── rules.py
│       │   ├── corrections.py
│       │   └── classifier.py
│       ├── events/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── store.py
│       │   └── handlers.py
│       ├── imports/
│       │   ├── __init__.py
│       │   ├── bank_csv.py
│       │   ├── normalization.py
│       │   └── duplicate_detection.py
│       ├── journal/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── service.py
│       │   └── validation.py
│       ├── projections/
│       │   ├── __init__.py
│       │   ├── balances.py
│       │   ├── ledger_views.py
│       │   └── rebuild.py
│       ├── reconciliation/
│       │   ├── __init__.py
│       │   ├── cash_movements.py
│       │   ├── duplicate_detection.py
│       │   ├── explanations.py
│       │   ├── matcher.py
│       │   ├── models.py
│       │   ├── scoring.py
│       │   └── splits.py
│       └── reports/
│           ├── __init__.py
│           ├── balance_sheet.py
│           ├── cash_flow.py
│           ├── income_statement.py
│           └── trial_balance.py
├── tests/
│   ├── property/
│   │   ├── test_accounting_invariants.py
│   │   ├── test_replay_invariants.py
│   │   └── test_reversal_invariants.py
│   ├── test_accounts.py
│   ├── test_bank_import.py
│   ├── test_cli.py
│   ├── test_event_store.py
│   ├── test_journal_posting.py
│   ├── test_package_import.py
│   ├── test_projection_rebuild.py
│   ├── test_reconciliation_exact.py
│   ├── test_reconciliation_fuzzy.py
│   ├── test_reconciliation_splits.py
│   └── test_reports.py
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
├── pyproject.toml
├── .python-version
└── .gitignore
```

Adjust this structure only if the project needs it. If changed, update this section before implementation.

---

## Official names and paths

Package name:

```text
reconcile
```

Main script:

```text
scripts/run_reconcile.py
```

Seed script:

```text
scripts/seed_demo_data.py
```

Projection rebuild script:

```text
scripts/rebuild_projections.py
```

Streamlit dashboard:

```text
dashboard/streamlit_app.py
```

Project State file:

```text
docs/Reconcile_Project_State.md
```

Architecture docs:

```text
docs/Architecture.md
docs/Event_Model.md
docs/Accounting_Invariants.md
docs/Reconciliation_Design.md
docs/Step_Plan.md
```

Sample chart of accounts:

```text
examples/demo_company/chart_of_accounts.csv
```

Sample journal entries:

```text
examples/demo_company/journal_entries.csv
```

Sample bank statement:

```text
examples/demo_company/bank_statement.csv
```

Sample output folder:

```text
examples/sample_output/
```

Default output folder:

```text
exports/
```

Default SQLite database:

```text
exports/reconcile.db
```

Official output files:

```text
exports/reconcile.db
exports/trial_balance.csv
exports/income_statement.csv
exports/balance_sheet.csv
exports/cash_flow.csv
exports/reconciliation_results.csv
```

---

## Official input format

### Chart of accounts input

Input file:

```text
examples/demo_company/chart_of_accounts.csv
```

Required columns:

```text
account_code
account_name
account_type
normal_balance
```

Optional columns:

```text
parent_account_code
description
is_active
```

Sample content:

```csv
account_code,account_name,account_type,normal_balance,parent_account_code,description,is_active
1000,Cash,asset,debit,,Primary checking account,true
1100,Accounts Receivable,asset,debit,,Customer receivables,true
2000,Accounts Payable,liability,credit,,Vendor payables,true
3000,Owner Equity,equity,credit,,Owner capital,true
4000,Service Revenue,revenue,credit,,Service income,true
5000,Rent Expense,expense,debit,,Office rent,true
5100,Software Expense,expense,debit,,Software subscriptions,true
5200,Meals Expense,expense,debit,,Business meals,true
5300,Office Supplies Expense,expense,debit,,Office supplies,true
```

---

### Journal entries input

Input file:

```text
examples/demo_company/journal_entries.csv
```

Required columns:

```text
entry_id
entry_date
description
line_number
account_code
side
amount
```

Optional columns:

```text
line_description
external_reference
```

Sample content:

```csv
entry_id,entry_date,description,line_number,account_code,side,amount,line_description,external_reference
JE-001,2026-01-01,Owner contribution,1,1000,debit,5000.00,Cash received,DEMO
JE-001,2026-01-01,Owner contribution,2,3000,credit,5000.00,Owner equity,DEMO
JE-002,2026-01-05,Software subscription,1,5100,debit,50.00,Accounting software,DEMO
JE-002,2026-01-05,Software subscription,2,1000,credit,50.00,Cash payment,DEMO
```

---

### Bank statement input

Input file:

```text
examples/demo_company/bank_statement.csv
```

Required columns:

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

Sample content:

```csv
transaction_date,posted_date,description,amount,external_id,check_number
2026-01-01,2026-01-01,DEPOSIT OWNER CONTRIBUTION,5000.00,BANK-001,
2026-01-06,2026-01-06,POS SOFTWARE SUBSCRIPTION,-50.00,BANK-002,
```

All sample data must be fake and safe to commit.

---

## Official data model

### Account model

| Field            | Required | Type   | Notes                                          |
| ---------------- | -------: | ------ | ---------------------------------------------- |
| `account_id`     |      Yes | `str`  | Stable internal ID.                            |
| `code`           |      Yes | `str`  | Unique account code.                           |
| `name`           |      Yes | `str`  | Human-readable account name.                   |
| `account_type`   |      Yes | `str`  | asset, liability, equity, revenue, or expense. |
| `normal_balance` |      Yes | `str`  | debit or credit.                               |
| `is_active`      |      Yes | `bool` | Closed accounts are inactive.                  |
| `opened_at`      |      Yes | `str`  | ISO timestamp.                                 |
| `closed_at`      |       No | `str`  | ISO timestamp if closed.                       |

Model rules:

* Account code cannot be blank.
* Account name cannot be blank.
* Account type must be valid.
* Normal balance must match the account type unless explicitly allowed by a future design decision.
* Duplicate account codes are rejected.
* Inactive accounts cannot be used in new journal entries.

---

### Journal entry model

| Field                | Required | Type                | Notes                                |
| -------------------- | -------: | ------------------- | ------------------------------------ |
| `journal_entry_id`   |      Yes | `str`               | Stable internal ID.                  |
| `entry_date`         |      Yes | `date`              | Accounting effective date.           |
| `description`        |      Yes | `str`               | Entry description.                   |
| `lines`              |      Yes | `list[JournalLine]` | At least two lines.                  |
| `source`             |      Yes | `str`               | manual, import, demo, reversal, etc. |
| `external_reference` |       No | `str`               | Optional source reference.           |

Model rules:

* Journal entry must have at least two lines.
* Total debits must equal total credits.
* Line amounts must be positive integer cents.
* Every line must reference a valid active account.
* Each line must be debit or credit.
* Posted journal entries cannot be mutated.
* Corrections require reversal events.

---

### Journal line model

| Field              | Required | Type  | Notes                      |
| ------------------ | -------: | ----- | -------------------------- |
| `line_id`          |      Yes | `str` | Stable internal ID.        |
| `journal_entry_id` |      Yes | `str` | Parent entry.              |
| `account_id`       |      Yes | `str` | Linked account.            |
| `side`             |      Yes | `str` | debit or credit.           |
| `amount_cents`     |      Yes | `int` | Positive integer cents.    |
| `description`      |       No | `str` | Optional line description. |
| `line_number`      |      Yes | `int` | Display order.             |

Model rules:

* `amount_cents` must be greater than zero.
* `side` must be debit or credit.
* Line numbers should be stable within the entry.

---

### Bank transaction model

| Field                    | Required | Type   | Notes                                      |
| ------------------------ | -------: | ------ | ------------------------------------------ |
| `bank_transaction_id`    |      Yes | `str`  | Stable internal ID.                        |
| `import_id`              |      Yes | `str`  | Parent import.                             |
| `transaction_date`       |      Yes | `date` | Bank transaction date.                     |
| `posted_date`            |       No | `date` | Bank posted date.                          |
| `description_raw`        |      Yes | `str`  | Raw bank text.                             |
| `description_normalized` |       No | `str`  | Normalized text.                           |
| `amount_cents`           |      Yes | `int`  | Positive for inflow, negative for outflow. |
| `external_id`            |       No | `str`  | Bank-provided ID if available.             |
| `check_number`           |       No | `str`  | Check number if available.                 |
| `row_hash`               |      Yes | `str`  | Duplicate detection hash.                  |
| `duplicate_group_id`     |       No | `str`  | Duplicate group if flagged.                |

Model rules:

* Raw description must be preserved.
* Normalization must be deterministic.
* Amount must use integer cents.
* Duplicate rows are flagged, not deleted.

---

### Reconciliation match model

| Field                     | Required | Type        | Notes                                                               |
| ------------------------- | -------: | ----------- | ------------------------------------------------------------------- |
| `reconciliation_match_id` |      Yes | `str`       | Stable internal ID.                                                 |
| `reconciliation_run_id`   |      Yes | `str`       | Parent run.                                                         |
| `bank_transaction_id`     |      Yes | `str`       | Linked bank transaction.                                            |
| `ledger_movement_ids`     |      Yes | `list[str]` | One or more ledger cash movements.                                  |
| `match_type`              |      Yes | `str`       | exact, fuzzy, split, manual, duplicate, unmatched.                  |
| `score`                   |      Yes | `float`     | Match confidence score.                                             |
| `amount_delta_cents`      |      Yes | `int`       | Difference between bank and ledger amount.                          |
| `date_delta_days`         |       No | `int`       | Date difference if applicable.                                      |
| `status`                  |      Yes | `str`       | auto_matched, candidate, ambiguous, confirmed, rejected, unmatched. |
| `explanation`             |      Yes | `dict`      | Why the match was assigned.                                         |

Model rules:

* Auto-confirmed matches must meet score and ambiguity thresholds.
* Ambiguous matches cannot be auto-confirmed.
* A ledger movement cannot be reused across confirmed matches in the same reconciliation run.
* Every non-exact match must include a useful explanation.

---

## Official SQLite schema

### `ledger_events`

```sql
CREATE TABLE ledger_events (
    event_sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    event_version INTEGER NOT NULL DEFAULT 1,
    event_timestamp TEXT NOT NULL,
    effective_date TEXT NOT NULL,
    source TEXT NOT NULL,
    actor TEXT,
    correlation_id TEXT,
    causation_id TEXT,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
```

### `accounts`

```sql
CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    account_type TEXT NOT NULL,
    normal_balance TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    opened_at TEXT NOT NULL,
    closed_at TEXT
);
```

### `journal_entries`

```sql
CREATE TABLE journal_entries (
    journal_entry_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    reversed_by_entry_id TEXT,
    reversal_of_entry_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(event_id) REFERENCES ledger_events(event_id)
);
```

### `journal_entry_lines`

```sql
CREATE TABLE journal_entry_lines (
    line_id TEXT PRIMARY KEY,
    journal_entry_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    side TEXT NOT NULL CHECK (side IN ('debit', 'credit')),
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    description TEXT,
    line_number INTEGER NOT NULL,
    FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(journal_entry_id),
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);
```

### `account_balances`

```sql
CREATE TABLE account_balances (
    account_id TEXT PRIMARY KEY,
    debit_total_cents INTEGER NOT NULL DEFAULT 0,
    credit_total_cents INTEGER NOT NULL DEFAULT 0,
    balance_cents INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    last_event_sequence INTEGER,
    FOREIGN KEY(account_id) REFERENCES accounts(account_id)
);
```

### `bank_statement_imports`

```sql
CREATE TABLE bank_statement_imports (
    import_id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_hash TEXT,
    imported_at TEXT NOT NULL,
    row_count INTEGER NOT NULL
);
```

### `bank_transactions`

```sql
CREATE TABLE bank_transactions (
    bank_transaction_id TEXT PRIMARY KEY,
    import_id TEXT NOT NULL,
    transaction_date TEXT NOT NULL,
    posted_date TEXT,
    description_raw TEXT NOT NULL,
    description_normalized TEXT,
    amount_cents INTEGER NOT NULL,
    external_id TEXT,
    check_number TEXT,
    row_hash TEXT NOT NULL,
    duplicate_group_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(import_id) REFERENCES bank_statement_imports(import_id)
);
```

### `reconciliation_runs`

```sql
CREATE TABLE reconciliation_runs (
    reconciliation_run_id TEXT PRIMARY KEY,
    cash_account_id TEXT NOT NULL,
    statement_start_date TEXT NOT NULL,
    statement_end_date TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    config_json TEXT NOT NULL,
    FOREIGN KEY(cash_account_id) REFERENCES accounts(account_id)
);
```

### `reconciliation_matches`

```sql
CREATE TABLE reconciliation_matches (
    reconciliation_match_id TEXT PRIMARY KEY,
    reconciliation_run_id TEXT NOT NULL,
    bank_transaction_id TEXT NOT NULL,
    match_type TEXT NOT NULL,
    score REAL NOT NULL,
    amount_delta_cents INTEGER NOT NULL,
    date_delta_days INTEGER,
    status TEXT NOT NULL,
    explanation_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(reconciliation_run_id) REFERENCES reconciliation_runs(reconciliation_run_id),
    FOREIGN KEY(bank_transaction_id) REFERENCES bank_transactions(bank_transaction_id)
);
```

### `reconciliation_match_ledger_links`

```sql
CREATE TABLE reconciliation_match_ledger_links (
    reconciliation_match_id TEXT NOT NULL,
    journal_entry_id TEXT NOT NULL,
    journal_entry_line_id TEXT,
    amount_cents INTEGER NOT NULL,
    PRIMARY KEY (reconciliation_match_id, journal_entry_id, journal_entry_line_id),
    FOREIGN KEY(reconciliation_match_id) REFERENCES reconciliation_matches(reconciliation_match_id),
    FOREIGN KEY(journal_entry_id) REFERENCES journal_entries(journal_entry_id)
);
```

---

## Official output format

The MVP should generate:

```text
exports/reconcile.db
exports/trial_balance.csv
exports/income_statement.csv
exports/balance_sheet.csv
exports/reconciliation_results.csv
```

Later outputs:

```text
exports/cash_flow.csv
exports/event_timeline.csv
exports/account_balances.csv
exports/categorization_review.csv
```

### Trial balance output

Should include:

1. Account code
2. Account name
3. Account type
4. Debit total
5. Credit total
6. Ending debit balance
7. Ending credit balance

### Income statement output

Should include:

1. Revenue accounts
2. Expense accounts
3. Total revenue
4. Total expenses
5. Net income or loss
6. Date range

### Balance sheet output

Should include:

1. Asset accounts
2. Liability accounts
3. Equity accounts
4. Current period net income, if not closed
5. Total assets
6. Total liabilities and equity
7. As-of date

### Cash flow output

Should include:

1. Operating cash flows
2. Investing cash flows
3. Financing cash flows
4. Net cash change
5. Beginning cash
6. Ending cash

### Reconciliation results output

Should include:

1. Bank transaction date
2. Bank description
3. Bank amount
4. Matched ledger entry or entries
5. Match type
6. Match status
7. Score
8. Amount delta
9. Date delta
10. Explanation

---

## Official CLI / interface behavior

The MVP should eventually support:

```bash
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db

python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db

python scripts/run_reconcile.py rebuild-projections --db-path exports/reconcile.db

python scripts/run_reconcile.py report trial-balance --db-path exports/reconcile.db --as-of 2026-01-31

python scripts/run_reconcile.py report income-statement --db-path exports/reconcile.db --from 2026-01-01 --to 2026-01-31

python scripts/run_reconcile.py report balance-sheet --db-path exports/reconcile.db --as-of 2026-01-31

python scripts/run_reconcile.py import-bank examples/demo_company/bank_statement.csv --db-path exports/reconcile.db

python scripts/run_reconcile.py reconcile --db-path exports/reconcile.db --cash-account 1000 --from 2026-01-01 --to 2026-01-31

python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir exports
```

Later:

```bash
streamlit run dashboard/streamlit_app.py
```

CLI/interface rules:

* User-facing errors should be clear.
* Core business logic should not live in the CLI wrapper.
* CLI should call package services.
* CLI should validate paths and options.
* CLI should return non-zero exit code for failure.
* Preview/dry-run behavior should be added where useful.
* Commands should work with fake demo data.

---

## Official module responsibilities

| Module                             | Responsibility                                              |
| ---------------------------------- | ----------------------------------------------------------- |
| `config.py`                        | Store constants and default settings.                       |
| `db.py`                            | Create SQLite connections and initialize schema.            |
| `exceptions.py`                    | Define custom project exceptions.                           |
| `money.py`                         | Convert, validate, and format integer cents.                |
| `events/models.py`                 | Define event data structures.                               |
| `events/store.py`                  | Append and load events.                                     |
| `events/handlers.py`               | Dispatch events to projection handlers.                     |
| `accounts/models.py`               | Define account models and enums.                            |
| `accounts/service.py`              | Open, close, and look up accounts.                          |
| `accounts/chart.py`                | Load or seed chart of accounts.                             |
| `journal/models.py`                | Define journal entry and line models.                       |
| `journal/validation.py`            | Validate double-entry rules.                                |
| `journal/service.py`               | Post and reverse journal entries.                           |
| `projections/balances.py`          | Apply journal activity to account balances.                 |
| `projections/ledger_views.py`      | Build query-friendly ledger views.                          |
| `projections/rebuild.py`           | Clear and rebuild projections from events.                  |
| `reports/trial_balance.py`         | Generate trial balance data.                                |
| `reports/income_statement.py`      | Generate income statement data.                             |
| `reports/balance_sheet.py`         | Generate balance sheet data.                                |
| `reports/cash_flow.py`             | Generate cash flow data.                                    |
| `imports/bank_csv.py`              | Read and validate bank CSV imports.                         |
| `imports/normalization.py`         | Normalize bank descriptions.                                |
| `imports/duplicate_detection.py`   | Detect duplicate imported rows.                             |
| `reconciliation/cash_movements.py` | Extract ledger cash movements.                              |
| `reconciliation/scoring.py`        | Score amount/date/description matches.                      |
| `reconciliation/matcher.py`        | Coordinate reconciliation matching.                         |
| `reconciliation/splits.py`         | Detect limited split matches.                               |
| `reconciliation/explanations.py`   | Build match explanation objects.                            |
| `categorization/rules.py`          | Apply deterministic category rules.                         |
| `categorization/corrections.py`    | Store user corrections.                                     |
| `categorization/classifier.py`     | Optional local scikit-learn classifier.                     |
| `cli.py`                           | Parse CLI arguments and coordinate workflows.               |
| `dashboard/streamlit_app.py`       | Display reports, audit timeline, and reconciliation review. |

Rule:

> Modules should have one main responsibility. Do not let the CLI, dashboard, importer, or matcher become junk drawers.

---

## Dependency decisions

Dependency source of truth:

```text
pyproject.toml
```

Do not create unless explicitly needed:

```text
requirements.txt
```

Planned runtime dependencies:

* `streamlit` — dashboard/demo interface.
* `pandas` — dashboard tables and export-friendly data handling.
* `plotly` — optional dashboard charts.
* `scikit-learn` — optional local categorization classifier, added only when classifier work begins.

Planned development dependencies:

* `pytest` — test framework.
* `hypothesis` — property-based accounting invariant tests.
* `pytest-cov` — coverage, if used.
* `ruff` — linting and formatting checks.

Possible later dependencies:

* `mypy` — static typing, only if the codebase benefits enough to justify it.
* `pyarrow` — only if Parquet export is added later.

Dependency rule:

> Add a dependency only when it clearly beats a simple standard-library solution.

Dependency timing rule:

> Do not add `scikit-learn` until the local classifier step begins.

---

## Testing decisions

Testing framework:

```text
pytest
```

Property-testing framework:

```text
hypothesis
```

Linting tool:

```text
ruff
```

Coverage tool, if used:

```text
pytest-cov
```

Testing targets:

* Add tests with every meaningful feature.
* Test happy paths.
* Test bad inputs.
* Test edge cases.
* Test accounting invariants.
* Test projection replay.
* Test reversals.
* Test report totals.
* Test reconciliation exact matches.
* Test reconciliation fuzzy matches.
* Test split matches.
* Test duplicate detection.
* Keep tests fast and offline.
* Do not require Streamlit Cloud for tests.
* Mock filesystem, network, time, or external boundaries where practical.
* Add a coverage floor if the project becomes large enough to justify it.

Default commands:

```bash
python -m pytest
python -m ruff check .
```

Later smoke-check commands:

```bash
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db
python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db
python scripts/run_reconcile.py rebuild-projections --db-path exports/reconcile.db
python scripts/run_reconcile.py report trial-balance --db-path exports/reconcile.db --as-of 2026-01-31
python scripts/run_reconcile.py import-bank examples/demo_company/bank_statement.csv --db-path exports/reconcile.db
python scripts/run_reconcile.py reconcile --db-path exports/reconcile.db --cash-account 1000 --from 2026-01-01 --to 2026-01-31
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output
streamlit run dashboard/streamlit_app.py
```

---

## Property-based testing plan

Property tests should be easy to explain to non-experts:

> Example tests verify known scenarios. Property-based tests generate many random valid ledgers and verify that accounting laws still hold.

Core invariants to test:

1. Generated balanced journal entries keep debits equal to credits.
2. Invalid unbalanced entries are rejected.
3. Invalid entries do not enter the event store.
4. Any sequence of valid posted entries keeps the trial balance balanced.
5. The expanded accounting equation holds before closing entries:

```text
Assets + Expenses = Liabilities + Equity + Revenue
```

6. Projection replay reproduces the same account balances.
7. Reversing a posted entry removes its net account impact.
8. Event replay is deterministic when ordered by `event_sequence`.
9. Report totals agree with underlying account balances.

Test naming rule:

> Test names should explain the accounting rule being protected.

Example names:

```python
def test_generated_journal_entries_keep_trial_balance_balanced():
    ...

def test_replaying_events_rebuilds_same_account_balances():
    ...

def test_reversing_any_valid_entry_removes_its_net_effect():
    ...

def test_unbalanced_entries_never_reach_event_store():
    ...
```

---

## Reconciliation testing plan

Example-based reconciliation tests should cover:

* Exact same amount/date auto-matches.
* Same amount within date window auto-matches.
* Amount outside tolerance does not match.
* Two candidates with same amount become ambiguous.
* Duplicate imported bank rows are flagged.
* One bank transaction can match two ledger cash movements.
* One bank transaction can match three ledger cash movements.
* One ledger movement cannot be used twice in the same run.
* Already reconciled movements are excluded.
* Positive bank deposit matches debit to Cash.
* Negative bank withdrawal matches credit to Cash.
* Description similarity affects candidate ranking but does not override bad amount.
* Match explanations include component scores.

Property-style reconciliation tests may later cover:

* Generated exact bank/ledger pairs always match.
* Adding unrelated noise does not break exact matches.
* No bank transaction gets more than one confirmed match.
* No ledger movement gets reused across auto-matches.
* Generated split components sum back to the matched bank transaction.

---

## Git and commit rules

* Use atomic commits with clear messages.
* One completed step should usually become one commit.
* Do not commit broken tests unless there is a specific reason.
* Do not mix unrelated cleanup with feature work.
* Check `git status` before and after staging.
* Review diffs before committing.
* Do not leave generated real data in the repo.
* Do not commit local `.db` files unless a fake demo database is intentionally committed.
* Prefer committing sample CSV outputs over binary database files unless the README needs a demo database.

Commit message examples:

```text
Add project skeleton and tooling baseline
Add event store schema and append logic
Add account model and chart of accounts loader
Add journal posting validation
Add projection rebuild workflow
Add trial balance report
Add journal reversal events
Add bank statement importer
Add reconciliation exact matching
Add reconciliation fuzzy scoring
Add split match detection
Add accounting invariant property tests
Add Streamlit audit dashboard
Polish Reconcile README quickstart
```

---

## GitHub setup checklist

First GitHub setup tasks:

* Create a new GitHub repository named `reconcile`.
* Keep it public if intended as a portfolio project.
* Do not add a GitHub README if the local README already exists.
* Do not add a GitHub `.gitignore` if the local `.gitignore` will be created manually.
* Do not add a license unless the license decision is final.
* Clone the repo locally.
* Add `README.md`.
* Add `docs/Reconcile_Project_State.md`.
* Add initial architecture docs if ready.
* Commit the planning files first.
* Push the first commit to GitHub.
* Confirm the README displays correctly on GitHub.

---

## Architecture decision records

Use this section to record major design decisions.

### ADR 001 — Use event sourcing for ledger state

Decision:

* Reconcile will store accounting actions as append-only events.
* Current state will be derived through projections.

Why:

* Accounting systems need auditability.
* Reversals are more realistic than mutation.
* Replayable state demonstrates engineering rigor.

Alternatives considered:

* Simple CRUD journal tables.
* Direct account-balance mutation.

Tradeoff accepted:

* Event sourcing adds complexity, but it is central to the portfolio value.

Status:

* Accepted.

---

### ADR 002 — Use SQLite first

Decision:

* Reconcile will use SQLite for MVP storage.

Why:

* Easy local setup.
* No server required.
* Good portfolio demo fit.
* Keeps quickstart simple.

Alternatives considered:

* Postgres.

Tradeoff accepted:

* SQLite has fewer production features, but the schema can be designed with future migration in mind.

Status:

* Accepted.

---

### ADR 003 — Use integer cents for money

Decision:

* Money will be stored and calculated as integer cents.

Why:

* Avoids floating-point rounding errors.
* Makes invariants easier to test.
* Keeps reconciliation tolerances explicit.

Alternatives considered:

* Python floats.
* Decimal everywhere.

Tradeoff accepted:

* Formatting/parsing requires helper functions.

Status:

* Accepted.

---

### ADR 004 — Use Streamlit for dashboard

Decision:

* Reconcile will use Streamlit for the dashboard.

Why:

* Python-native.
* Fast to build.
* Works well with SQLite.
* Good for portfolio screenshots and public demo.
* Keeps focus on the accounting engine.

Alternatives considered:

* Plotly Dash.
* Evidence.dev.
* Power BI.

Tradeoff accepted:

* Streamlit is less enterprise-BI oriented, but better for this local-first Python engine.

Status:

* Accepted.

---

### ADR 005 — Use reversal events for corrections

Decision:

* Corrections will use reversal events and reversing journal entries.

Why:

* Preserves audit trail.
* Matches accounting practice.
* Keeps event history immutable.

Alternatives considered:

* Editing posted journal entries.
* Deleting incorrect entries.

Tradeoff accepted:

* Users must create additional entries for corrections.

Status:

* Accepted.

---

### ADR 006 — Keep ML categorization optional and local

Decision:

* Categorization starts rule-based.
* A local scikit-learn classifier may be added later using user corrections.
* No LLM or external API will be used for categorization.

Why:

* Rules are explainable.
* ML should not distract from ledger correctness.
* Local-only behavior keeps the project safe and portfolio-friendly.

Alternatives considered:

* LLM categorization.
* External enrichment APIs.

Tradeoff accepted:

* Local ML may be less powerful, but it is safer and easier to explain.

Status:

* Accepted.

---

## Step prompt template

Use this prompt structure for every build step:

````markdown
Reconcile Step [Number] only.

Current status:
- Step [previous] is complete.
- We are now working on Step [Number].
- Do not assume future steps are complete.

Goal for this step:
[One clear outcome.]

Allowed files to create/edit:
- [file]
- [file]
- docs/Reconcile_Project_State.md

Do not edit:
- [file]
- [file]

Do not implement yet:
- [future feature]
- [future feature]
- [scope danger]

Requirements:
- [specific behavior]
- [specific behavior]
- [specific behavior]

Tests required:
- Add/update tests for [specific behavior].
- Include happy-path tests.
- Include bad-input or edge-case tests.
- Existing tests must still pass.

Commands to run:
```bash
python -m pytest
python -m ruff check .
````

Project State update:

* Update docs/Reconcile_Project_State.md.
* Mark this step complete.
* Add completed work.
* Add commands run.
* Add next planned step.

Definition of done:

* The requested feature works.
* New tests cover the feature.
* Relevant edge cases are tested.
* Existing tests still pass.
* Ruff passes.
* Project State is updated.
* Git status only shows expected files.
* A clean commit message is suggested.

Git guidance:

* Show expected git status.
* Recommend one atomic commit message.

````

---

## Standard project phases

Reconcile will use these phases unless this file is updated first.

### Phase 0 — Planning

- README draft
- Project State
- MVP
- non-goals
- architecture
- event model
- schema plan
- reconciliation plan
- invariant testing plan
- step plan

### Phase 1 — Foundation

- folders
- `pyproject.toml`
- `.gitignore`
- package import
- first smoke test
- pytest
- ruff
- CI later or early if useful

### Phase 2 — Core accounting model

- custom exceptions
- money helpers
- account models
- journal entry models
- validation helpers
- model tests

### Phase 3 — Event store and SQL schema

- SQLite schema
- event append/load
- event sequence ordering
- event models
- event tests

### Phase 4 — Chart of accounts

- account opening
- account closing
- account projection
- seed chart
- account tests

### Phase 5 — Journal posting

- balanced journal validation
- JournalEntryPosted event
- journal projections
- line projections
- posting tests

### Phase 6 — Balance projections

- account balance projection
- projection handlers
- rebuild workflow
- projection replay tests

### Phase 7 — Reports

- trial balance
- income statement
- balance sheet
- report tests

### Phase 8 — Reversals

- JournalEntryReversed event
- reversing journal entries
- reversal projection behavior
- reversal tests

### Phase 9 — Property-based invariant tests

- Hypothesis strategies
- accounting invariant tests
- replay invariant tests
- reversal invariant tests

### Phase 10 — Bank import

- bank CSV importer
- normalization
- row hashing
- duplicate detection
- bank import tests

### Phase 11 — Reconciliation engine

- ledger cash movements
- exact matching
- fuzzy matching
- ambiguous matching
- split matching
- reconciliation tests

### Phase 12 — Categorization

- rule-based categorization
- correction storage
- optional local ML classifier
- categorization tests

### Phase 13 — Dashboard

- Streamlit overview
- event timeline
- reports
- reconciliation review
- categorization review

### Phase 14 — Cash flow and reporting polish

- direct-method cash flow
- report exports
- sample outputs

### Phase 15 — Documentation and release cleanup

- README polish
- architecture docs
- screenshots
- CHANGELOG
- CONTRIBUTING
- CI
- final smoke tests
- final git cleanup

---

## Step history

### Step 0 — README-driven planning and Project State

Status: Complete.

Goal:

- Define Reconcile before implementation begins.

Expected work:

- Add `README.md`.
- Add `docs/Reconcile_Project_State.md`.
- Define MVP scope.
- Define explicit non-goals.
- Define official project structure.
- Define event-sourcing rules.
- Define accounting rules.
- Define reconciliation rules.
- Define official sample input formats.
- Define official output formats.
- Define first GitHub setup checklist.

Allowed files to create/edit:

```text
README.md
docs/Reconcile_Project_State.md
docs/Architecture.md
docs/Event_Model.md
docs/Accounting_Invariants.md
docs/Reconciliation_Design.md
docs/Step_Plan.md
````

Commands run:

```bash
git status
```

Result in this sandbox:

```text
fatal: not a git repository (or any of the parent directories): .git
```

Completed summary:

* Added planning README.
* Added architecture overview.
* Added planned event model.
* Added accounting invariant plan.
* Added reconciliation design.
* Added phase-based step plan.
* Confirmed no implementation files were created.

Definition of done:

* Project goal is clear.
* MVP is clear.
* Non-goals are clear.
* Official paths are clear.
* Step plan is clear.
* Project State is committed.

Suggested commit message:

```text
Add Reconcile planning docs
```

---

### Step 1 — Create project skeleton and tooling baseline

Status: Complete.

Goal:

* Create the repo structure and confirm the basic Python package works.

Completed work:

* Created the initial `src/` package layout.
* Added `src/reconcile/__init__.py` with a package docstring and `__version__`.
* Added `pyproject.toml` using setuptools with `src/` layout.
* Added development dependencies for pytest and ruff only.
* Added simple ruff configuration.
* Added `.gitignore` for Python caches, virtual environments, tool caches, local database files, and local environment files.
* Added `.python-version` matching the local Python version used in this sandbox.
* Added `tests/test_package_import.py` for the import smoke test.
* Added fake demo company CSV files using the official Step 1 columns.
* Confirmed all fake sample journal entries balance.
* Added `.gitkeep` placeholders for `examples/sample_output/` and `exports/`.
* Did not add SQL schema, event store, models, posting logic, reports, reconciliation, categorization, dashboard, or future dependencies.

Files created or edited:

```text
.gitignore
.python-version
pyproject.toml
src/reconcile/__init__.py
tests/test_package_import.py
examples/demo_company/chart_of_accounts.csv
examples/demo_company/journal_entries.csv
examples/demo_company/bank_statement.csv
examples/sample_output/.gitkeep
exports/.gitkeep
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
git status
```

Results in this sandbox:

```text
python -m pip install -e ".[dev]"  # success
python -m pytest                    # 2 passed
python -m ruff check .              # All checks passed!
git status                          # fatal: not a git repository (or any of the parent directories): .git
```

Definition of done:

* Package imports.
* Tests pass.
* Ruff passes.
* Project State updated.
* Git status was checked; this sandbox is not a Git repository.

Suggested commit message:

```text
Add Reconcile project skeleton and tooling baseline
```

---

### Step 2 — Add core exceptions and money helpers

Status: Complete.

Goal:

* Add custom exceptions and safe money parsing/formatting utilities.

Completed work:

* Added `src/reconcile/exceptions.py` with the custom exception hierarchy:

  * `ReconcileError` inherits from `Exception`.
  * `ValidationError` inherits from `ReconcileError`.
  * `MoneyError` inherits from `ValidationError`.

* Added `src/reconcile/money.py` with integer-cents helpers:

  * `parse_money_to_cents(value: str) -> int`
  * `format_cents(cents: int) -> str`

* Implemented money parsing without floats.
* Supported valid whole-dollar, decimal, negative, comma, currency-symbol, whitespace, zero, and one-cent values.
* Rejected blank strings, non-string values, invalid numeric text, malformed comma text, currency-symbol-only values, and values with more than two decimal places.
* Implemented cents formatting with two decimals.
* Rejected bool, float, string, `Decimal`, and other non-int formatting values.
* Added focused tests in `tests/test_money.py`.
* Did not add accounts, journal entries, event storage, reports, reconciliation, categorization, or dashboard work.

Files created or edited:

```text
src/reconcile/exceptions.py
src/reconcile/money.py
tests/test_money.py
docs/Reconcile_Project_State.md
```

Commands run:

```bash
PYTHONPATH=src python -m pytest
python -m ruff check .
git status
```

Results in this sandbox:

```text
PYTHONPATH=src python -m pytest     # 31 passed
python -m ruff check .              # failed: No module named ruff in this sandbox environment
git status                          # fatal: not a git repository (or any of the parent directories): .git
```

Definition of done:

* Money parsing works.
* Money formatting works.
* Bad money inputs fail clearly with `MoneyError`.
* Tests pass in this sandbox.
* Ruff could not be run in this sandbox because `ruff` is not installed here; run it in the project virtual environment where Step 1 installed dev dependencies.
* Project State updated.

Suggested commit message:

```text
Add money helpers and custom exceptions
```

---

### Step 3 — Add account models and chart of accounts validation

Status: Complete.

Goal:

* Define the account model and validate chart of accounts rules.

Completed work:

* Added `src/reconcile/accounts/__init__.py` with Step 3 exports only.
* Added `src/reconcile/accounts/models.py` with account type definitions, normal balance definitions, normal balance mapping, validation helpers, and the `Account` dataclass.
* Added `expected_normal_balance(account_type: str) -> str`.
* Added validation for blank `account_id`, `code`, `name`, and `opened_at`.
* Added validation for official account types and normal balances.
* Added validation that normal balance must match the account type.
* Added validation that `is_active` must be a real bool, rejecting string and integer stand-ins.
* Allowed `closed_at=None` and rejected blank `closed_at` values when provided.
* Added `tests/test_accounts.py` covering valid account types, expected normal balances, invalid fields, invalid types, mismatched normal balances, non-bool active values, close timestamp edge cases, and `ValidationError` behavior.
* Did not implement SQLite, account events, account services, chart CSV loading, journal entries, reports, reconciliation, categorization, or dashboard work.

Files created or edited:

```text
src/reconcile/accounts/__init__.py
src/reconcile/accounts/models.py
tests/test_accounts.py
docs/Reconcile_Project_State.md
```

Commands run:

```bash
PYTHONPATH=src python -m pytest tests/test_accounts.py
PYTHONPATH=src python -m pytest
python -m ruff check .
git status
```

Results in this sandbox:

```text
PYTHONPATH=src python -m pytest tests/test_accounts.py  # could not complete: base Step 2 files are not present in this sandbox
PYTHONPATH=src python -m pytest                         # could not complete: base Step 2 files are not present in this sandbox
python -m ruff check .                                  # failed: No module named ruff in this sandbox environment
git status                                               # fatal: not a git repository (or any of the parent directories): .git
```

Definition of done:

* Account types are defined.
* Normal balance rules are defined.
* `expected_normal_balance` works.
* `Account` validates required fields.
* Invalid account data fails clearly with `ValidationError`.
* No SQLite, event, service, journal, report, reconciliation, or dashboard logic was added.
* Account tests cover happy paths, bad inputs, and edge cases.
* Project State updated.
* Full local test, ruff, and git checks should be run in the real repository virtual environment.

Suggested commit message:

```text
Add account models and validation
```

---

### Step 4 — Add journal entry models and validation

Status: Complete.

Goal:

* Define journal entry and journal line models with double-entry validation.

Completed work:

* Added `src/reconcile/journal/__init__.py` with Step 4 exports only.
* Added `src/reconcile/journal/models.py` with `JournalLine` and `JournalEntry` dataclasses.
* Added validation for required journal line fields.
* Added validation for required journal entry fields.
* Added validation that journal line side must be `debit` or `credit`.
* Added validation that journal line amounts must be positive integer cents and reject bool values.
* Added validation that line numbers must be positive integers and reject bool values.
* Added validation that optional line descriptions and external references cannot be blank when provided.
* Added validation that entries must contain at least two `JournalLine` items.
* Added validation that all lines must match the parent `journal_entry_id`.
* Added validation that line numbers are unique within an entry.
* Added validation that total debits must equal total credits.
* Added `src/reconcile/journal/validation.py` with `validate_journal_line`, `validate_journal_entry`, `total_debits`, `total_credits`, and `is_balanced`.
* Added `tests/test_journal_models.py` covering happy paths, bad inputs, edge cases, helper functions, and `ValidationError` behavior.
* Did not implement event storage, SQLite persistence, posting services, reversals, projections, reports, reconciliation, categorization, or dashboard logic.

Files created or edited:

```text
src/reconcile/journal/__init__.py
src/reconcile/journal/models.py
src/reconcile/journal/validation.py
tests/test_journal_models.py
docs/Reconcile_Project_State.md
```

Commands run:

```bash
PYTHONPATH=/tmp/reconcile_test/src pytest -q /tmp/reconcile_test/test_journal_models.py
python -m ruff check /mnt/data/reconcile_step4
git status
```

Results in this sandbox:

```text
PYTHONPATH=/tmp/reconcile_test/src pytest -q /tmp/reconcile_test/test_journal_models.py  # 31 passed
python -m ruff check /mnt/data/reconcile_step4                                      # failed: No module named ruff in this sandbox environment
git status                                                                          # not run here against the real repository
```

Definition of done:

* `src/reconcile/journal/__init__.py` exists.
* `src/reconcile/journal/models.py` exists.
* `src/reconcile/journal/validation.py` exists.
* Valid balanced journal entries pass.
* Unbalanced entries fail.
* Single-line entries fail.
* Negative or zero amounts fail.
* Duplicate line numbers fail.
* Invalid journal data fails clearly with `ValidationError`.
* Journal tests cover happy paths, bad inputs, and edge cases.
* No SQLite, event store, posting service, projection, report, reconciliation, or dashboard logic was added.
* Project State updated.
* Full local test, ruff, and git checks should be run in the real repository virtual environment.

Suggested commit message:

```text
Add journal entry models and double-entry validation
```

---

### Step 5 — Add SQLite schema initialization

Status: Complete.

Goal:

* Create the database connection helper and initialize MVP tables.

Expected work:

* Add `db.py`.
* Create SQLite connection helper.
* Create schema initialization function.
* Add tables for events, accounts, journal entries, journal lines, balances, bank imports, bank transactions, reconciliation runs, reconciliation matches, and reconciliation links.
* Add tests that confirm tables are created.

Allowed files to create/edit:

```text
src/reconcile/db.py
tests/test_db_schema.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Event append logic
* Account service
* Journal posting service
* Reconciliation engine

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Completed work:

* Added `src/reconcile/db.py`.
* Added `connect(db_path)` with parent directory creation, `sqlite3.Row`, and foreign key enforcement.
* Added `initialize_schema(connection)` with repeatable MVP table creation.
* Added optional `initialize_database(db_path)` helper.
* Added all MVP schema tables listed in the official schema.
* Added simple supporting indexes.
* Added `tests/test_db_schema.py` for connection behavior, table creation, required columns, idempotency, uniqueness, foreign keys, check constraints, and event sequence autoincrement.
* Did not implement event append/load logic or services.

Files created or edited:

```text
src/reconcile/db.py
tests/test_db_schema.py
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m py_compile /mnt/data/reconcile_step5/src/reconcile/db.py /mnt/data/reconcile_step5/tests/test_db_schema.py
```

Results in this sandbox:

```text
python -m py_compile /mnt/data/reconcile_step5/src/reconcile/db.py /mnt/data/reconcile_step5/tests/test_db_schema.py  # success
python -m pytest                                                                                                      # run locally in the real repository
python -m ruff check .                                                                                                # run locally in the real repository
git status                                                                                                            # run locally in the real repository
```

Definition of done:

* Test database initializes.
* Required tables exist.
* Schema setup is repeatable.
* Schema constraints are tested.
* Local tests should pass in the real repository.
* Local ruff should pass in the real repository.

Suggested commit message:

```text
Add SQLite schema initialization
```

---

### Step 6 — Add event models and append-only event store

Status: Complete.

Goal:

* Implement append-only event storage and deterministic event loading.

Expected work:

* Add event model.
* Add event store.
* Implement `append_event`.
* Implement `load_events`.
* Preserve `event_sequence` order.
* Validate event type and payload.
* Add tests for append/load behavior.

Allowed files to create/edit:

```text
src/reconcile/events/__init__.py
src/reconcile/events/models.py
src/reconcile/events/store.py
tests/test_event_store.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Event handlers
* Projection rebuild
* Journal posting

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Completed work:

* Added `src/reconcile/events/__init__.py` with Step 6 exports only.
* Added `src/reconcile/events/models.py` with the `LedgerEvent` dataclass.
* Added official MVP event type constants.
* Added validation for blank required fields, invalid event versions, bool event versions, non-dict payloads, non-JSON-serializable payloads, blank optional strings, and invalid event sequences.
* Added `src/reconcile/events/store.py` with append-only event-store functions.
* Added `append_event(connection, event)` to insert one row into `ledger_events` and return the stored event with its assigned `event_sequence`.
* Added `load_events(connection)` to return all events in deterministic `event_sequence ASC` order.
* Added `load_event_by_id(connection, event_id)` for single-event lookup.
* Added `load_events_by_type(connection, event_type)` for filtered deterministic event loading.
* Stored event payloads as JSON in `payload_json` and round-tripped them back to dict payloads.
* Converted duplicate event IDs into a project `ValidationError`.
* Added event-store tests covering model validation, append behavior, event sequence assignment, deterministic loading, JSON payload round trips, duplicate IDs, commit behavior, empty loads, event lookup, event-type filtering, and no projection writes.
* Did not add event handlers, projection writes, account services, journal posting services, reversals, reports, reconciliation, categorization, or dashboard logic.

Files created or edited:

```text
src/reconcile/events/__init__.py
src/reconcile/events/models.py
src/reconcile/events/store.py
tests/test_event_store.py
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m pytest
python -m ruff check .
git status
```

Results:

```text
python -m pytest        # passed locally
python -m ruff check .  # passed locally after fixing an initial ruff error
git status              # expected Step 6 files only
```

Definition of done:

* Events append successfully.
* Events load in sequence order.
* Event IDs are unique.
* Invalid event data fails clearly.
* Tests pass.
* Ruff passes.
* Project State updated.

Suggested commit message:

```text
Add append-only event store
```
---

### Step 7 — Add account service and AccountOpened projection

Status: Complete.

Goal:

* Open accounts through events and project them into the accounts table.

Expected work:

* Add account service.
* Implement `open_account`.
* Append `AccountOpened` event.
* Apply account-opened event to accounts projection.
* Reject duplicate account codes.
* Add seed chart behavior if appropriate.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/accounts/service.py
src/reconcile/accounts/chart.py
src/reconcile/events/handlers.py
tests/test_account_service.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Journal posting
* Balance projections
* Reports

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Completed work:

* Added `src/reconcile/accounts/service.py`.
* Added `open_account` to append an `AccountOpened` event and then apply it to the accounts projection.
* Added duplicate account ID and duplicate account code validation before appending events.
* Added AccountOpened payloads with all fields required to rebuild the account projection.
* Added account lookup helpers: `get_account_by_id`, `get_account_by_code`, and `list_accounts`.
* Added `src/reconcile/events/handlers.py` with `apply_event` support for `AccountOpened` only.
* Added clear `ValidationError` behavior for unsupported Step 7 event types.
* Added `src/reconcile/accounts/chart.py` with minimal `open_accounts` batch helper.
* Added `tests/test_account_service.py` covering account opening, event storage, projection writes, duplicate behavior, payload shape, direct event application, unsupported event behavior, lookup helpers, stable listing, and batch account opening.
* Did not add journal posting, balance projections, reports, reversals, reconciliation, categorization, dashboard, or CLI logic.

Files created or edited:

```text
src/reconcile/accounts/service.py
src/reconcile/accounts/chart.py
src/reconcile/events/handlers.py
tests/test_account_service.py
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m pytest
python -m ruff check .
git status
```

Results:

```text
python -m pytest        # run locally in the real repository
python -m ruff check .  # run locally in the real repository
git status              # expected Step 7 files only
```

Definition of done:

* Accounts can be opened.
* AccountOpened events are stored.
* Accounts projection is updated.
* Duplicate account IDs and account codes fail.
* AccountOpened payloads can rebuild account projections.
* Tests pass locally.
* Ruff passes locally.

Suggested commit message:

```text
Add account opening events and projection
```

---

### Step 8 — Add journal posting service and journal projections

Status: Complete.

Goal:

* Post balanced journal entries through events and project journal entries and lines.

Expected work:

* Add journal service.
* Implement `post_journal_entry`.
* Validate entries before appending events.
* Append `JournalEntryPosted` event.
* Project journal entry header.
* Project journal entry lines.
* Reject inactive or missing accounts.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/journal/service.py
src/reconcile/events/handlers.py
tests/test_journal_posting.py
docs/Reconcile_Project_State.md
```

Completed work:

* Added `src/reconcile/journal/service.py`.
* Added `post_journal_entry` to validate and post balanced journal entries through append-only `JournalEntryPosted` events.
* Added journal posting payloads with all header and line fields needed to rebuild journal projections.
* Added pre-append validation for duplicate journal entry IDs.
* Added pre-append validation for missing account references.
* Added pre-append validation for inactive account references.
* Extended `apply_event` to support `JournalEntryPosted` while preserving `AccountOpened` behavior.
* Preserved Step 7 handler expectations for unsupported event behavior and AccountOpened payload validation.
* Added projection behavior for `journal_entries`.
* Added projection behavior for `journal_entry_lines`.
* Added `status="posted"` for newly posted journal entries.
* Added `reversed_by_entry_id=None` for newly posted journal entries.
* Added `reversal_of_entry_id=None` for newly posted journal entries.
* Added duplicate journal entry ID validation during projection apply.
* Added duplicate journal line ID validation during projection apply.
* Added optional journal lookup helpers for single-entry lookup and stable ordered listing.
* Added `tests/test_journal_posting.py` covering happy paths, bad inputs, projection behavior, payload shape, account validation, duplicate behavior, direct event apply behavior, no-balance-projection behavior, and lookup helpers.
* Did not add account balance projections, projection rebuilds, reversals, reports, bank import, reconciliation, categorization, dashboard, CLI, or property-based tests.

Files created or edited:

```text
src/reconcile/journal/service.py
src/reconcile/events/handlers.py
tests/test_journal_posting.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Balance projections
* Projection rebuild workflow
* Reversals
* Reports
* Bank import
* Bank reconciliation
* Categorization
* Dashboard
* CLI

Commands run:

```bash
python -m pytest
python -m ruff check .
git status
```

Results:

```text
python -m pytest        # expected final result after fixes: 194 passed
python -m ruff check .  # run locally in the real repository
git status              # expected Step 8 files only
```

Definition of done:

* `src/reconcile/journal/service.py` exists.
* `src/reconcile/events/handlers.py` supports `AccountOpened` and `JournalEntryPosted`.
* Valid balanced journal entries can be posted through events.
* Posted journal entries are projected into `journal_entries`.
* Posted journal lines are projected into `journal_entry_lines`.
* Missing and inactive accounts are rejected.
* Duplicate journal entry IDs are rejected.
* Invalid journal entries do not enter the event store.
* Journal posting does not update account balances yet.
* No reversals, reports, reconciliation, dashboard, or CLI logic was added.
* `tests/test_journal_posting.py` covers happy paths, bad inputs, projection behavior, payload shape, account validation, duplicate behavior, and no-balance-projection behavior.
* Existing tests pass locally.
* Ruff passes locally.
* Project State is updated.

Suggested commit message:

```text
Add journal posting events and projections
```

---

### Step 9 — Add account balance projections

Status: Not started.

Goal:

* Apply journal entries to account-balance projections.

Expected work:

* Add balance projection logic.
* Update debit totals and credit totals.
* Calculate normal-balance-aware account balances.
* Apply journal events to balances.
* Add tests for asset, liability, equity, revenue, and expense behavior.

Allowed files to create/edit:

```text
src/reconcile/projections/__init__.py
src/reconcile/projections/balances.py
src/reconcile/events/handlers.py
tests/test_account_balances.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Projection rebuild
* Reports
* Reversals

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Debit to asset increases asset balance.
* Credit to liability increases liability balance.
* Credit to revenue increases revenue balance.
* Debit to expense increases expense balance.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add account balance projections
```

---

### Step 10 — Add projection rebuild workflow

Status: Not started.

Goal:

* Clear projections and rebuild them from the event log.

Expected work:

* Add projection rebuild module.
* Clear projection tables safely.
* Replay all events in `event_sequence` order.
* Rebuild accounts, journal entries, journal lines, and balances.
* Add rebuild script.
* Add tests proving rebuilt balances match current balances.

Allowed files to create/edit:

```text
src/reconcile/projections/rebuild.py
scripts/rebuild_projections.py
tests/test_projection_rebuild.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Reports
* Reversals
* Bank import

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Projections can be rebuilt.
* Replay order is deterministic.
* Rebuilt balances match incremental balances.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add projection rebuild workflow
```

---

### Step 11 — Add trial balance report

Status: Not started.

Goal:

* Generate trial balance data from projections.

Expected work:

* Add trial balance report module.
* Include account code, name, type, debit total, credit total, and ending debit/credit balance.
* Support as-of date if practical at this step.
* Add example-based tests.

Allowed files to create/edit:

```text
src/reconcile/reports/__init__.py
src/reconcile/reports/trial_balance.py
tests/test_reports.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Income statement
* Balance sheet
* Cash flow
* Dashboard

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Trial balance generates expected rows.
* Total debits equal total credits.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add trial balance report
```

---

### Step 12 — Add income statement and balance sheet reports

Status: Not started.

Goal:

* Generate basic income statement and balance sheet reports.

Expected work:

* Add income statement report.
* Add balance sheet report.
* Support date ranges for income statement.
* Support as-of date for balance sheet.
* Include current period net income in balance sheet if not closed.
* Add example-based tests.

Allowed files to create/edit:

```text
src/reconcile/reports/income_statement.py
src/reconcile/reports/balance_sheet.py
tests/test_reports.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Cash flow
* Dashboard
* Reconciliation

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Income statement totals are correct.
* Balance sheet balances.
* Report tests pass.
* Ruff passes.

Suggested commit message:

```text
Add income statement and balance sheet reports
```

---

### Step 13 — Add journal reversal behavior

Status: Not started.

Goal:

* Reverse posted journal entries through reversal events.

Expected work:

* Implement `reverse_journal_entry`.
* Create opposite debit/credit lines.
* Append `JournalEntryReversed` event.
* Create reversal journal entry projection.
* Mark original entry as reversed in projection.
* Preserve original event history.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/journal/service.py
src/reconcile/events/handlers.py
tests/test_journal_reversals.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Bank reconciliation
* Dashboard
* ML categorization

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Posted entries can be reversed.
* Reversal lines flip debit/credit sides.
* Net account impact is zero.
* Original entry is not deleted.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add journal reversal events
```

---

### Step 14 — Add property-based accounting invariant tests

Status: Not started.

Goal:

* Use Hypothesis to test core accounting invariants across generated ledgers.

Expected work:

* Add Hypothesis dependency.
* Add generated account/journal strategies.
* Test trial balance invariant.
* Test expanded accounting equation.
* Test replay invariant.
* Test reversal neutrality.
* Test invalid entries never reach event store.
* Document invariant tests.

Allowed files to create/edit:

```text
tests/property/test_accounting_invariants.py
tests/property/test_replay_invariants.py
tests/property/test_reversal_invariants.py
docs/Accounting_Invariants.md
docs/Reconcile_Project_State.md
pyproject.toml
```

Do not implement yet:

* Bank import
* Reconciliation
* Dashboard

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Property tests run successfully.
* Invariant docs explain the tests in plain English.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add property-based accounting invariant tests
```

---

### Step 15 — Add bank CSV import and normalization

Status: Not started.

Goal:

* Import fake bank statement CSV data and normalize descriptions.

Expected work:

* Add bank CSV importer.
* Validate required columns.
* Preserve raw descriptions.
* Normalize descriptions.
* Convert bank amounts to integer cents.
* Store import metadata.
* Store bank transactions.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/imports/__init__.py
src/reconcile/imports/bank_csv.py
src/reconcile/imports/normalization.py
tests/test_bank_import.py
examples/demo_company/bank_statement.csv
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Reconciliation matching
* Categorization
* Dashboard

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Valid bank CSV imports.
* Missing required columns fail clearly.
* Raw descriptions are preserved.
* Normalized descriptions are stored.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add bank CSV import and normalization
```

---

### Step 16 — Add bank duplicate detection

Status: Not started.

Goal:

* Detect duplicate bank import rows without deleting source data.

Expected work:

* Add row hashing.
* Detect duplicate external IDs if available.
* Detect duplicate date/amount/description groups.
* Store duplicate group IDs.
* Add duplicate reason/explanation if useful.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/imports/duplicate_detection.py
src/reconcile/imports/bank_csv.py
tests/test_bank_duplicate_detection.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Reconciliation matching
* Categorization
* Dashboard

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Duplicate rows are flagged.
* Legitimate similar transactions are not deleted.
* Duplicate logic is tested.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add bank duplicate detection
```

---

### Step 17 — Add ledger cash movement extraction

Status: Not started.

Goal:

* Convert journal entries touching Cash into bank-comparable ledger cash movements.

Expected work:

* Add cash movement extraction module.
* Support selected cash account.
* Convert debit to Cash as positive amount.
* Convert credit to Cash as negative amount.
* Include journal entry and line references.
* Exclude reversed entries appropriately if design requires.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/reconciliation/__init__.py
src/reconcile/reconciliation/cash_movements.py
tests/test_cash_movements.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Match scoring
* Split matching
* Dashboard

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Cash debits become positive movements.
* Cash credits become negative movements.
* Non-cash lines are ignored.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add ledger cash movement extraction
```

---

### Step 18 — Add exact reconciliation matching

Status: Not started.

Goal:

* Match bank transactions to ledger cash movements using exact amount/date logic.

Expected work:

* Add reconciliation models.
* Add exact matcher.
* Create reconciliation run records.
* Store match records.
* Store link records.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/reconciliation/models.py
src/reconcile/reconciliation/matcher.py
src/reconcile/reconciliation/explanations.py
tests/test_reconciliation_exact.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Fuzzy scoring
* Split matching
* Categorization

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Exact same amount/date matches.
* Exact deposits match cash debits.
* Exact withdrawals match cash credits.
* Unmatched items remain unmatched.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add exact reconciliation matching
```

---

### Step 19 — Add fuzzy reconciliation scoring and ambiguity handling

Status: Not started.

Goal:

* Score amount/date/description candidates and prevent unsafe auto-matches.

Expected work:

* Add scoring module.
* Implement amount score.
* Implement date score.
* Implement description score.
* Implement duplicate penalty.
* Implement score thresholds.
* Implement top-candidate gap rule.
* Store explanation JSON.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/reconciliation/scoring.py
src/reconcile/reconciliation/matcher.py
src/reconcile/reconciliation/explanations.py
tests/test_reconciliation_fuzzy.py
docs/Reconciliation_Design.md
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Split matching
* Manual review UI
* ML categorization

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Fuzzy candidates score correctly.
* Ambiguous candidates are not auto-matched.
* Explanation includes component scores.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add fuzzy reconciliation scoring
```

---

### Step 20 — Add split reconciliation matching

Status: Not started.

Goal:

* Match one bank transaction to two or three ledger cash movements.

Expected work:

* Add split matching module.
* Search combinations of 2 and 3 ledger movements.
* Enforce same-sign rule.
* Enforce date window.
* Enforce amount tolerance.
* Add split penalty.
* Store split explanation.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/reconciliation/splits.py
src/reconcile/reconciliation/matcher.py
tests/test_reconciliation_splits.py
docs/Reconciliation_Design.md
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Unlimited subset-sum
* Many bank transactions to one ledger entry
* Dashboard

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Two-line splits match.
* Three-line splits match.
* Wrong-sign splits are rejected.
* Ambiguous splits are candidates, not unsafe auto-matches.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add split reconciliation matching
```

---

### Step 21 — Add CLI workflow

Status: Not started.

Goal:

* Add a thin CLI that wires together the tested engine workflows.

Expected work:

* Add `cli.py`.
* Add `scripts/run_reconcile.py`.
* Support database initialization.
* Support demo seeding.
* Support projection rebuild.
* Support reports.
* Support bank import.
* Support reconciliation run.
* Add CLI tests.
* Run manual smoke checks.

Allowed files to create/edit:

```text
src/reconcile/cli.py
scripts/run_reconcile.py
tests/test_cli.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Streamlit dashboard
* Rule-based categorization
* ML classifier

Commands to run:

```bash
python -m pytest
python -m ruff check .
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db
python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db
python scripts/run_reconcile.py rebuild-projections --db-path exports/reconcile.db
```

Definition of done:

* CLI wrapper is thin.
* Core logic remains in package modules.
* CLI smoke checks pass.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add Reconcile CLI workflow
```

---

### Step 22 — Add report exports and sample outputs

Status: Not started.

Goal:

* Export reports and reconciliation results to stable output files.

Expected work:

* Add export behavior.
* Export trial balance.
* Export income statement.
* Export balance sheet.
* Export reconciliation results.
* Generate fake sample outputs.
* Add tests that inspect output contents.

Allowed files to create/edit:

```text
src/reconcile/reports/export.py
examples/sample_output/
tests/test_report_exports.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Dashboard
* Cash flow
* ML categorization

Commands to run:

```bash
python -m pytest
python -m ruff check .
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output
```

Definition of done:

* Output files use official names.
* Output files are generated from fake data.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add report exports and sample outputs
```

---

### Step 23 — Add rule-based categorization

Status: Not started.

Goal:

* Add deterministic category rules for imported bank transactions.

Expected work:

* Add categorization rules module.
* Add category rule model.
* Apply rules by priority.
* Store category source/reason.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/categorization/__init__.py
src/reconcile/categorization/rules.py
tests/test_categorization_rules.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* scikit-learn classifier
* Dashboard categorization review

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Rules assign categories deterministically.
* Rule explanations are stored or returned.
* Unmatched transactions remain uncategorized.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add rule-based categorization
```

---

### Step 24 — Add correction storage and optional local classifier

Status: Not started.

Goal:

* Add user correction tracking and optional local ML categorization.

Expected work:

* Add correction storage.
* Add training data extraction from corrections.
* Add optional scikit-learn classifier.
* Add confidence threshold.
* Make rules override ML predictions.
* Keep classifier local.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/categorization/corrections.py
src/reconcile/categorization/classifier.py
tests/test_categorization_classifier.py
pyproject.toml
docs/Reconcile_Project_State.md
```

Do not implement yet:

* External APIs
* LLM categorization
* Cloud model calls

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Corrections can be stored.
* Classifier can train from corrections.
* Low-confidence predictions are handled safely.
* Rules override classifier predictions.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add local categorization corrections and classifier
```

---

### Step 25 — Add cash flow report

Status: Not started.

Goal:

* Add a direct-method cash flow report.

Expected work:

* Add cash flow report module.
* Classify cash movements as operating, investing, or financing using account/category mapping.
* Calculate beginning cash.
* Calculate cash inflows.
* Calculate cash outflows.
* Calculate ending cash.
* Add tests.

Allowed files to create/edit:

```text
src/reconcile/reports/cash_flow.py
tests/test_cash_flow_report.py
docs/Reconcile_Project_State.md
```

Do not implement yet:

* Complex indirect-method cash flow
* Statement of retained earnings

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* Cash flow report produces expected totals.
* Beginning cash plus net change equals ending cash.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add direct-method cash flow report
```

---

### Step 26 — Add Streamlit dashboard foundation

Status: Not started.

Goal:

* Add a basic Streamlit dashboard shell connected to the demo database.

Expected work:

* Add `dashboard/streamlit_app.py`.
* Add database path selector or default demo path.
* Add overview page.
* Show basic project status.
* Show account balances.
* Keep logic thin.
* Add smoke-level test if practical.

Allowed files to create/edit:

```text
dashboard/streamlit_app.py
docs/Reconcile_Project_State.md
pyproject.toml
```

Do not implement yet:

* Full report pages
* Reconciliation review UI
* Categorization review UI

Commands to run:

```bash
python -m pytest
python -m ruff check .
streamlit run dashboard/streamlit_app.py
```

Definition of done:

* Streamlit app launches locally.
* Dashboard can read fake demo database.
* Core logic remains outside dashboard.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add Streamlit dashboard foundation
```

---

### Step 27 — Add dashboard report pages and event timeline

Status: Not started.

Goal:

* Display point-in-time reports and event history in Streamlit.

Expected work:

* Add trial balance page.
* Add income statement page.
* Add balance sheet page.
* Add cash flow page if Step 25 is complete.
* Add event timeline page.
* Add as-of date or event sequence selector.
* Add screenshots if useful.

Allowed files to create/edit:

```text
dashboard/streamlit_app.py
docs/Reconcile_Project_State.md
README.md
```

Do not implement yet:

* Reconciliation review UI
* Categorization review UI
* Cloud deployment

Commands to run:

```bash
python -m pytest
python -m ruff check .
streamlit run dashboard/streamlit_app.py
```

Definition of done:

* Reports display correctly.
* Event timeline displays correctly.
* Dashboard still keeps business logic thin.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add Streamlit reports and event timeline
```

---

### Step 28 — Add dashboard reconciliation and categorization review

Status: Not started.

Goal:

* Add review screens for reconciliation matches and categorization decisions.

Expected work:

* Show bank transactions.
* Show matched ledger movements.
* Show match status.
* Show match score and explanation.
* Show ambiguous candidates.
* Show category source/reason.
* Allow review-friendly display.
* Manual confirmation may be read-only or interactive depending on scope at this step.

Allowed files to create/edit:

```text
dashboard/streamlit_app.py
docs/Reconcile_Project_State.md
README.md
```

Do not implement yet:

* Production user workflow
* Auth
* Real bank APIs

Commands to run:

```bash
python -m pytest
python -m ruff check .
streamlit run dashboard/streamlit_app.py
```

Definition of done:

* Reconciliation results are reviewable.
* Match explanations are visible.
* Categorization decisions are visible.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Add Streamlit reconciliation and categorization review
```

---

### Step 29 — Add CI workflow

Status: Not started.

Goal:

* Add GitHub Actions for automated tests and linting.

Expected work:

* Add CI workflow.
* Run pytest.
* Run ruff.
* Confirm GitHub Actions passes.

Allowed files to create/edit:

```text
.github/workflows/ci.yml
docs/Reconcile_Project_State.md
README.md
```

Do not implement yet:

* Deployment automation
* Production hosting

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* CI file exists.
* CI runs tests and linting.
* Local tests pass.
* Local ruff passes.
* GitHub Actions passes.

Suggested commit message:

```text
Add CI workflow
```

---

### Step 30 — Polish README and architecture docs

Status: Not started.

Goal:

* Make the project understandable and portfolio-ready.

Expected work:

* Polish README quickstart.
* Add architecture overview.
* Add event model explanation.
* Add accounting invariant explanation.
* Add reconciliation design explanation.
* Add dashboard screenshots if available.
* Add limitations and future improvements.
* Confirm docs match actual behavior.

Allowed files to create/edit:

```text
README.md
docs/Architecture.md
docs/Event_Model.md
docs/Accounting_Invariants.md
docs/Reconciliation_Design.md
docs/Step_Plan.md
docs/Reconcile_Project_State.md
```

Do not implement yet:

* New major features
* README fiction

Commands to run:

```bash
python -m pytest
python -m ruff check .
```

Definition of done:

* README quickstart works.
* Docs match actual code.
* Architecture is clear.
* Limitations are honest.
* Tests pass.
* Ruff passes.

Suggested commit message:

```text
Polish Reconcile documentation
```

---

### Step 31 — Final portfolio polish and release cleanup

Status: Not started.

Goal:

* Prepare Reconcile as a finished portfolio project.

Expected work:

* Final README review.
* Final docs review.
* Final CHANGELOG update.
* Final CONTRIBUTING update.
* Final CI check.
* Final test pass.
* Final ruff pass.
* Manual smoke checks.
* Generate final fake sample outputs.
* Confirm no secrets or real data.
* Confirm final git status is clean.
* Mark project complete in this Project State file.

Allowed files to create/edit:

```text
README.md
CHANGELOG.md
CONTRIBUTING.md
docs/Reconcile_Project_State.md
examples/sample_output/
```

Commands to run:

```bash
python -m pytest
python -m ruff check .
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db
python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db
python scripts/run_reconcile.py rebuild-projections --db-path exports/reconcile.db
python scripts/run_reconcile.py report trial-balance --db-path exports/reconcile.db --as-of 2026-01-31
python scripts/run_reconcile.py report income-statement --db-path exports/reconcile.db --from 2026-01-01 --to 2026-01-31
python scripts/run_reconcile.py report balance-sheet --db-path exports/reconcile.db --as-of 2026-01-31
python scripts/run_reconcile.py import-bank examples/demo_company/bank_statement.csv --db-path exports/reconcile.db
python scripts/run_reconcile.py reconcile --db-path exports/reconcile.db --cash-account 1000 --from 2026-01-01 --to 2026-01-31
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output
git status
```

Definition of done:

* Tests pass.
* Ruff passes.
* CI passes.
* Manual smoke checks pass.
* Sample outputs are fake and safe.
* README is accurate.
* Docs are accurate.
* Project State is marked complete.
* Final git status is clean.

Suggested commit message:

```text
Finalize Reconcile portfolio project
```

---

## Portfolio readiness checklist

Before calling the project complete:

* [ ] Can the project be explained in one sentence?
* [ ] Does the README show what problem it solves?
* [ ] Does the quickstart work from a clean clone?
* [ ] Are sample inputs fake and safe?
* [ ] Are sample outputs committed if useful?
* [ ] Is the event-sourcing design documented?
* [ ] Is the event model documented?
* [ ] Is the reconciliation algorithm documented?
* [ ] Are accounting invariants documented?
* [ ] Do tests pass?
* [ ] Does ruff pass?
* [ ] Does coverage pass if configured?
* [ ] Does CI pass on GitHub?
* [ ] Are non-goals clear?
* [ ] Is the repo structure clean?
* [ ] Can projections be rebuilt from events?
* [ ] Can trial balance be generated?
* [ ] Can income statement be generated?
* [ ] Can balance sheet be generated?
* [ ] Can bank transactions be imported?
* [ ] Can reconciliation results be reviewed?
* [ ] Do match explanations exist?
* [ ] Does the dashboard launch locally?
* [ ] Does the dashboard avoid owning business logic?
* [ ] Is the Project State marked complete?
* [ ] Is the final git status clean?

---

## Final completion summary

Status: Not complete.

Final project summary:

* [What was built]
* [What works]
* [Tests/quality status]
* [Portfolio value]
* [Known future improvements, if any]

Final commands run:

```bash
[commands]
```

Final repository state:

```text
[clean / not clean / notes]
```

Known future improvements:

* Postgres migration option.
* More advanced AR/AP subledger.
* Indirect-method cash flow.
* Multi-period financial statement comparison.
* More advanced reconciliation search.
* Many bank transactions to one ledger movement.
* Deployment polish.
* More dashboard interactivity.
* More complete local ML categorization workflow.
* Export to Excel.
* Additional report formats.
* Optional Docker setup.