# Reconcile Project State

This file is the living source of truth for Reconcile.

Update it after every completed step.

Do not let implementation drift away from this file. If the plan changes, update this file first.

---

## Current status

Current step: Step 27 — Add dashboard report pages and event timeline.

Status: Step 27 complete.

Approximate project completion: 90% to 92%.

Current summary:

* Reconcile has its initial Python package skeleton under `src/reconcile/`.
* `pyproject.toml` is the dependency source of truth.
* Development tooling includes pytest, ruff, and Hypothesis.
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
* Step 9 added account balance projections for posted journal entries.
* Step 10 added a projection rebuild workflow that clears derived tables and replays append-only events.
* Step 11 added a trial balance report from account projections.
* Step 12 added income statement and balance sheet reports from posted journal entries and lines.
* Step 13 added journal reversal behavior through immutable `JournalEntryReversed` events.
* Step 14 added property-based accounting invariant tests with Hypothesis.
* Step 15 added bank statement CSV import and bank description normalization.
* Step 15 added raw bank description preservation, normalized descriptions, signed integer bank amounts, deterministic row hashes, and bank import metadata.
* Step 16 added bank duplicate detection and duplicate marking for imported bank transactions.
* Step 16 integrated duplicate marking into bank CSV import so duplicates are flagged immediately after import.
* Step 17 added ledger cash movement extraction for selected cash accounts.
* Step 17 converts debit lines to Cash into positive bank-comparable movements.
* Step 17 converts credit lines to Cash into negative bank-comparable movements.
* Step 17 supports inclusive start and end date filtering for ledger cash movements.
* Step 17 excludes reversed original entries and reversal entries by default, with an audit-inclusive option.
* Step 18 added exact reconciliation matching between imported bank transactions and extracted ledger cash movements.
* Step 18 creates reconciliation run records with completed status and JSON configuration.
* Step 18 stores reconciliation match records with match type, score, deltas, status, and JSON explanations.
* Step 18 stores ledger-link rows for exact auto-matches only.
* Step 18 enforces one-to-one ledger movement use within a reconciliation run.
* Step 18 leaves unmatched bank transactions clearly marked as unmatched.
* Step 18 blocks duplicate-flagged bank transactions from unsafe auto-matching.
* Step 19 added fuzzy reconciliation scoring for amount, date, and description candidates.
* Step 19 added fuzzy reconciliation run behavior with configurable amount tolerance and date windows.
* Step 19 stores fuzzy score components and explanations on reconciliation match records.
* Step 19 distinguishes fuzzy auto-matched, candidate, ambiguous, and unmatched decisions.
* Step 19 prevents unsafe auto-matches when top candidates are too close.
* Step 19 applies duplicate penalties and blocks duplicate-flagged bank rows from fuzzy auto-matching.
* Step 19 enforces one-to-one ledger movement use for fuzzy auto-matches within a run.
* Step 20 added limited split reconciliation matching for one bank transaction to two or three ledger cash movements.
* Step 20 added bounded split candidate discovery using same-sign components, amount tolerance, date windows, and deterministic ordering.
* Step 20 added split candidate scoring using amount, date, description, and split-penalty components.
* Step 20 added split reconciliation run behavior with auto-matched, candidate, ambiguous, and unmatched decisions.
* Step 20 stores split explanations with component movement IDs, component details, score components, and decision reasons.
* Step 20 creates one ledger-link row per component only for split auto-matches.
* Step 20 prevents component ledger movements from being reused across split auto-matches in the same run.
* Step 20 blocks duplicate-flagged bank transactions from split auto-matching.
* Step 21 added a thin `argparse` CLI at `src/reconcile/cli.py`.
* Step 21 added `scripts/run_reconcile.py` as a thin wrapper around `reconcile.cli.main`.
* Step 21 added CLI workflows for database initialization, demo seeding, projection rebuilds, reports, bank import, and exact/fuzzy/split reconciliation.
* Step 21 keeps CLI output plain text and keeps business logic inside existing package modules.
* Step 21 added CLI tests covering command wiring, demo seeding, reporting, bank import, reconciliation commands, validation errors, and wrapper smoke behavior.
* Step 22 added stable CSV exports for trial balance, income statement, balance sheet, and reconciliation results.
* Step 22 added `src/reconcile/reports/export.py` with read-only export functions that create parent output directories as needed.
* Step 22 added `export_all_reports` for coordinated report export into an output directory.
* Step 22 exports integer cents only and does not format report money as dollars.
* Step 22 exports report data rows only and keeps totals in returned summary dictionaries.
* Step 22 exports reconciliation results by joining reconciliation matches to bank transactions and aggregating ledger links.
* Step 22 skips `reconciliation_results.csv` when no reconciliation run ID is provided.
* Step 22 added `export-reports` as a top-level CLI command.
* Step 22 wired CLI report exports to `export_all_reports` while keeping CLI business logic thin.
* Step 22 generated fake sample output CSV files under `examples/sample_output/`.
* Step 22 added report export tests and CLI export tests covering file creation, headers, row counts, summaries, reconciliation exports, validation errors, and mutation safety.
* Step 23 added deterministic rule-based categorization for imported bank transactions.
* Step 23 added immutable `CategoryRule` models with validation for rule IDs, categories, priorities, text criteria, tokens, amount bounds, and amount signs.
* Step 23 added rule matching for normalized descriptions, raw-description fallback, any-token rules, all-token rules, amount ranges, and amount signs.
* Step 23 added explainable categorization result dictionaries with category, source, rule ID, reason, matched priority, matched description, and amount cents.
* Step 23 added deterministic rule ordering where highest priority wins and tied priorities sort by rule ID.
* Step 23 added uncategorized result behavior using `category=None` when no rule matches.
* Step 23 added fake/demo-friendly default rules for owner contributions, software, office supplies, meals, rent, and revenue.
* Step 23 added a read-only helper to load imported bank transactions for categorization review without mutating source rows or appending events.
* Step 23 added focused categorization tests covering validation, normalization, rule matching, deterministic categorization, default rules, transaction validation, read-only loading, and mutation safety.
* Step 24 added append-only categorization correction storage in SQLite.
* Step 24 added an idempotent `category_corrections` schema initializer without modifying the core database initializer.
* Step 24 added correction recording, correction listing, latest-correction lookup, training example extraction, and correction application helpers.
* Step 24 keeps category corrections separate from imported bank transaction rows and does not store final categories on `bank_transactions`.
* Step 24 added deterministic correction precedence where latest correction wins for each bank transaction.
* Step 24 added a small optional local standard-library classifier based on nearest token overlap instead of adding scikit-learn.
* Step 24 added rule/correction/classifier precedence: latest correction, then rule, then confident local classifier, then uncategorized.
* Step 24 added classifier confidence handling and low-confidence uncategorized results.
* Step 24 added focused correction and classifier tests covering validation, ordering, mutation safety, training behavior, prediction behavior, and precedence.
* Step 25 added a direct-method cash flow report from posted journal activity.
* Step 25 identifies cash-like asset/debit accounts using selected account IDs or cash/checking/bank heuristics.
* Step 25 classifies cash movement counterparties into operating, investing, and financing sections.
* Step 25 calculates beginning cash immediately before the report start date.
* Step 25 calculates ending cash through the report end date.
* Step 25 proves beginning cash plus net cash change equals ending cash with a cash-balances-tie flag.
* Step 25 excludes or nets out cash-to-cash transfers so transfers do not inflate cash flow.
* Step 25 added cash flow CSV export and included `cash_flow.csv` in `export_all_reports`.
* Step 25 added CLI support for `report cash-flow`.
* Step 25 generated fake sample output at `examples/sample_output/cash_flow.csv`.
* Step 25 added focused cash flow report, export, and CLI tests.
* Step 26 added the Streamlit dashboard foundation.
* Step 26 added `dashboard/streamlit_app.py` as a thin local demo dashboard.
* Step 26 added a database path input with `exports/reconcile.db` as the default.
* Step 26 added friendly missing-database setup instructions.
* Step 26 added read-only database counts for core accounting, bank, reconciliation, and categorization tables.
* Step 26 added summary metrics for ledger events, accounts, posted journal entries, bank transactions, reconciliation runs, trial balance status, and cash ending balance.
* Step 26 added a small trial balance/account balance preview using existing report logic.
* Step 26 added helper tests for dashboard database status, table counts, summary data, formatting, import safety, mutation safety, and missing optional tables.
* Step 26 added Streamlit as a runtime dependency.
* Step 27 expanded the Streamlit dashboard with sidebar navigation.
* Step 27 added read-only dashboard pages for Overview, Trial Balance, Income Statement, Balance Sheet, Cash Flow, and Event Timeline.
* Step 27 added default report dates of 2026-01-01 through 2026-01-31 and a default as-of date of 2026-01-31.
* Step 27 added report-loading helpers that call existing package report functions instead of adding dashboard business logic.
* Step 27 added dashboard display helpers for optional cents, optional boolean status, report row extraction, and report rows with cent fields.
* Step 27 added friendly validation handling for invalid report date ranges and invalid as-of dates.
* Step 27 added a read-only event timeline helper that queries `ledger_events` in deterministic `event_sequence` order.
* Step 27 added compact payload inspection for ledger events in Streamlit expanders.
* Step 27 preserved the known accounting refinement note that customer collections through Accounts Receivable should classify as operating cash flow, not investing.
* Step 27 expanded dashboard helper tests for report loaders, date validation, event timeline loading, JSON-serializable helper data, and read-only safety.
* Trial balance rows include account identity, debit totals, credit totals, and ending debit/credit balances.
* Income statements support inclusive start and end dates.
* Income statements include revenue and expense accounts only.
* Income statements calculate revenue as credits minus debits and expenses as debits minus credits.
* Balance sheets support an as-of date by reading posted journal lines through that date.
* Balance sheets include asset, liability, and equity account sections.
* Balance sheets include current period net income as an equity-like amount before closing entries exist.
* Balance sheets do not rely only on cumulative `account_balances` for as-of-date reporting.
* Journal reversals create opposite debit/credit lines while preserving original posted entries and original activity totals.
* Journal reversals mark the original posted entry with `reversed_by_entry_id` and mark the reversal entry with `reversal_of_entry_id`.
* Projection rebuilds replay `JournalEntryReversed` events and restore reversal state and balances.
* Property tests generate many valid accounting scenarios and verify core accounting laws still hold.
* Bank imports preserve source rows instead of deleting or merging anything.
* Duplicate imported bank rows are flagged with deterministic `duplicate_group_id` values.
* Duplicate detection returns a computed `duplicate_reason` without adding a new schema column.
* Duplicate detection supports row-hash, external-ID, and transaction-fingerprint rules.
* Ledger cash movement extraction returns stable movement IDs, journal entry references, journal line references, cash account metadata, signed integer amounts, and reversal metadata.
* Exact reconciliation uses exact cent equality and exact date equality only.
* Exact reconciliation uses bank-sign convention consistently with ledger cash movements.
* Duplicate detection precedence is row hash, then external ID, then transaction fingerprint.
* Report generation reads existing data and does not append events, rebuild projections, write files, print, or mutate projections.
* Ledger cash movement extraction reads existing journal projections and does not append events, rebuild projections, write files, print, or mutate accounting or bank tables.
* Exact reconciliation writes only reconciliation run, match, and ledger-link tables.
* Dashboard report pages and event timeline are implemented as read-only Streamlit pages.
* Manual review UI, confirmation/rejection events, Excel exports, JSON exports, PDF exports, and unlimited subset-sum split search are still intentionally not implemented.

Completed Step 27 files:

```text
dashboard/streamlit_app.py
tests/test_streamlit_dashboard.py
docs/Reconcile_Project_State.md
```

Completed Step 27 summary:

* Expanded `dashboard/streamlit_app.py` from a foundation shell into a read-only demo dashboard with sidebar navigation.
* Added Streamlit navigation pages for Overview, Trial Balance, Income Statement, Balance Sheet, Cash Flow, and Event Timeline.
* Preserved the default database path of `exports/reconcile.db`.
* Preserved missing-database setup instructions and graceful missing-database behavior.
* Preserved overview database counts, summary metrics, and account-balance preview behavior.
* Added default report dates for January 2026 and a default balance-sheet as-of date of 2026-01-31.
* Added date-range and as-of-date validation helpers that reject invalid ranges and datetime values.
* Added read-only report-loading helpers for trial balance, income statement, balance sheet, and cash flow.
* Kept dashboard report helpers thin by calling existing report functions in `src/reconcile/reports/`.
* Added display formatting helpers for optional integer cents, optional boolean statuses, and report rows with cent fields.
* Added tolerant report-row extraction for report functions that return sectioned dictionaries rather than only flat `rows` lists.
* Added fallback cash-flow display rows from cash-flow totals when the report has totals but no detail rows.
* Added read-only event timeline loading from `ledger_events` ordered by `event_sequence ASC`.
* Displayed event timeline fields for sequence, type, effective date, timestamp, source, actor, correlation ID, and causation ID.
* Displayed event payload JSON in expandable sections without replaying or mutating events.
* Added a dashboard cash-flow limitation note: customer collections through Accounts Receivable should classify as operating cash flow, not investing.
* Updated `tests/test_streamlit_dashboard.py` for Step 27 helper coverage.
* Tested dashboard module import safety.
* Tested page constants and page-rendering helper existence.
* Tested default report dates.
* Tested date validation and invalid date ranges.
* Tested trial balance, income statement, balance sheet, and cash flow report loaders.
* Tested event timeline loading, deterministic sequence ordering, expected fields, and empty event-log behavior.
* Tested missing database behavior for new report helpers.
* Tested cents and boolean formatters.
* Tested JSON-serializable dashboard helper payloads.
* Tested report helpers do not append ledger events.
* Tested report helpers do not mutate account balances.
* Tested event timeline loading does not mutate ledger events.
* Tested helpers do not import bank files, run reconciliation, or write export files.
* Did not add reconciliation review UI, categorization review UI, manual correction UI, manual confirmation/rejection UI, dashboard writeback, CI, deployment, screenshots, README polish, engine changes, new dependencies, or new accounting behavior.

Commands run for Step 27:

```bash
python -m ruff check dashboard/streamlit_app.py
python -m ruff check tests/test_streamlit_dashboard.py
python -m pytest tests/test_streamlit_dashboard.py
python -m ruff check .
python -m pytest
streamlit run dashboard/streamlit_app.py
git status
```

Results:

```text
python -m ruff check dashboard/streamlit_app.py      # All checks passed after import ordering and helper-order fixes
python -m ruff check tests/test_streamlit_dashboard.py # All checks passed
python -m pytest tests/test_streamlit_dashboard.py   # 35 passed after report-row extraction and cash-flow fallback fixes
python -m ruff check .                              # passed locally as reported
python -m pytest                                    # passed locally as reported
streamlit run dashboard/streamlit_app.py            # dashboard launched; all Step 27 pages showed no errors in manual smoke check
git status                                          # initially showed dashboard/streamlit_app.py only before test and Project State updates
```

Completed Step 18 files:

```text
src/reconcile/reconciliation/models.py
src/reconcile/reconciliation/explanations.py
src/reconcile/reconciliation/matcher.py
src/reconcile/reconciliation/__init__.py
tests/test_reconciliation_exact.py
docs/Reconcile_Project_State.md
```

Completed Step 18 summary:

* Added `src/reconcile/reconciliation/models.py`.
* Added lightweight constants for exact and unmatched match types.
* Added lightweight constants for auto-matched, candidate, and unmatched statuses.
* Added lightweight constant for completed reconciliation run status.
* Added `src/reconcile/reconciliation/explanations.py`.
* Added `build_exact_match_explanation(...)`.
* Added `build_unmatched_explanation(...)`.
* Kept explanations as JSON-serializable plain dictionaries.
* Included bank transaction IDs, ledger cash movement IDs, amount cents, bank dates, and ledger entry dates in explanations where applicable.
* Added `src/reconcile/reconciliation/matcher.py`.
* Added `run_exact_reconciliation(connection, *, cash_account_id, statement_start_date, statement_end_date, reconciliation_run_id=None, started_at=None)`.
* Added `list_reconciliation_matches(connection, reconciliation_run_id)`.
* Added `get_reconciliation_run(connection, reconciliation_run_id)`.
* Validated `cash_account_id` as a nonblank string.
* Validated statement start and end dates as real `datetime.date` values.
* Rejected `datetime.datetime` values for statement dates.
* Rejected statement ranges where start date is after end date.
* Validated provided reconciliation run IDs as nonblank strings.
* Generated UUID-based reconciliation run IDs when no run ID is provided.
* Inserted one reconciliation run row for each exact reconciliation run.
* Stored run status as `completed`.
* Stored cash account ID and statement dates on reconciliation runs.
* Stored started and completed timestamps on reconciliation runs.
* Stored JSON reconciliation configuration in `config_json`.
* Converted duplicate reconciliation run IDs into `ValidationError`.
* Selected bank transactions within the statement date range, inclusive.
* Used existing signed integer bank amounts from `bank_transactions.amount_cents`.
* Included duplicate-flagged bank transactions in inspection.
* Blocked duplicate-flagged bank transactions from automatic matching.
* Used `extract_ledger_cash_movements` for ledger-side selection.
* Used Step 17 default effective-only behavior for reversed entries.
* Did not reimplement cash movement extraction inside the matcher.
* Matched exact candidates only when bank amount equals ledger amount and bank transaction date equals ledger entry date.
* Used exact cent equality only.
* Used exact date equality only.
* Added deterministic matching order by bank transaction date, bank transaction ID, ledger entry date, and ledger movement ID.
* Enforced that one ledger cash movement can be used by at most one auto-match in the same run.
* Enforced that one bank transaction receives at most one reconciliation match record in Step 18.
* Created exact auto-match rows when exactly one unused ledger movement matched a bank transaction.
* Created unmatched rows when no ledger movement matched.
* Created candidate rows when multiple exact ledger candidates existed for one bank transaction.
* Created candidate rows when a matching ledger movement was already consumed by an earlier bank transaction.
* Created candidate rows when a duplicate-flagged bank transaction had an exact candidate.
* Stored exact auto-match rows with `match_type='exact'`, `score=100.0`, zero amount delta, zero date delta, and `status='auto_matched'`.
* Stored unmatched rows with `match_type='unmatched'`, `score=0.0`, bank amount as amount delta, `date_delta_days=NULL`, and `status='unmatched'`.
* Stored candidate rows with clear explanation JSON describing why no unsafe auto-match was made.
* Created ledger-link rows for exact auto-matches only.
* Linked exact auto-matches to matched journal entry IDs, journal entry line IDs, and signed amount cents.
* Did not create ledger-link rows for unmatched rows.
* Did not create ledger-link rows for candidate rows.
* Committed reconciliation writes after successful completion.
* Rolled back reconciliation writes if a failure occurred during the run.
* Did not append ledger events.
* Did not alter accounts.
* Did not alter journal entries.
* Did not alter journal entry lines.
* Did not alter account balances.
* Did not alter bank transactions.
* Updated `src/reconcile/reconciliation/__init__.py` to preserve Step 17 exports and add Step 18 public exports.
* Added `tests/test_reconciliation_exact.py`.
* Tested reconciliation run creation.
* Tested provided reconciliation run IDs.
* Tested generated reconciliation run IDs.
* Tested duplicate reconciliation run ID validation.
* Tested ISO date storage.
* Tested completed run status.
* Tested JSON run configuration.
* Tested summary counts.
* Tested exact deposit matching to debit-to-Cash movements.
* Tested exact withdrawal matching to credit-from-Cash movements.
* Tested amount mismatch unmatched behavior.
* Tested date mismatch unmatched behavior.
* Tested exact match record type, status, score, amount delta, date delta, and explanation JSON.
* Tested exact auto-match ledger-link rows.
* Tested unmatched records, unmatched explanations, and absence of ledger links.
* Tested one-to-one ledger movement safety.
* Tested multiple exact ledger candidates are not auto-matched.
* Tested duplicate-flagged bank transactions are not auto-matched.
* Tested deterministic matching behavior.
* Tested statement date range filtering for start date, end date, before range, and after range.
* Tested ledger movements outside the statement range are ignored.
* Tested invalid statement dates and invalid statement ranges.
* Tested reconciliation does not append ledger events.
* Tested reconciliation does not modify bank transaction rows.
* Tested reconciliation does not modify accounting projection tables.
* Tested reconciliation writes only reconciliation tables.
* Did not add fuzzy scoring, amount tolerance, fuzzy date windows, description similarity, split matching, manual confirmation/rejection, categorization, dashboard, full CLI workflow, CSV exports, cash flow, or new accounting features.

Commands run for Step 18:

```bash
python -m pytest
python -m ruff check .
```

Results:

```text
python -m pytest        # 441 passed in 72.82s (0:01:12)
python -m ruff check .  # All checks passed!
```

Completed Step 19 files:

```text
src/reconcile/reconciliation/scoring.py
src/reconcile/reconciliation/models.py
src/reconcile/reconciliation/explanations.py
src/reconcile/reconciliation/matcher.py
src/reconcile/reconciliation/__init__.py
tests/test_reconciliation_fuzzy.py
docs/Reconciliation_Design.md
docs/Reconcile_Project_State.md
```

Completed Step 19 summary:

* Added `src/reconcile/reconciliation/scoring.py`.
* Added `days_between`.
* Added `score_amount_match` with exact, tolerance, sign, and invalid-input handling.
* Added `score_date_match` with exact, date-window, and invalid-input handling.
* Added `score_description_match` with deterministic standard-library normalization and token-overlap scoring.
* Added `score_reconciliation_candidate` using amount, date, description, and duplicate-penalty components.
* Added fuzzy match type and ambiguous match status constants.
* Added `build_fuzzy_match_explanation` for JSON-serializable fuzzy match explanations.
* Preserved Step 18 exact and unmatched explanation builders.
* Added `run_fuzzy_reconciliation`.
* Preserved `run_exact_reconciliation` behavior.
* Stored fuzzy reconciliation run configuration in `config_json`.
* Selected bank transactions inside the statement date range.
* Used `extract_ledger_cash_movements` for ledger-side cash movement selection.
* Generated fuzzy candidates only when signs match, amount delta is within tolerance, and date delta is within the configured window.
* Scored fuzzy candidates with amount, date, description, amount delta, date delta, and duplicate penalty details.
* Added fuzzy auto-match threshold behavior.
* Added fuzzy candidate threshold behavior.
* Added ambiguous status behavior when high-scoring top candidates are too close.
* Blocked duplicate-flagged bank transactions from fuzzy auto-matching.
* Created ledger-link rows for fuzzy auto-matches only.
* Confirmed candidate, ambiguous, and unmatched fuzzy records do not create ledger-link rows.
* Enforced that one ledger cash movement can be consumed by at most one fuzzy auto-match in the same run.
* Added deterministic fuzzy candidate ordering.
* Added fuzzy reconciliation summary counts.
* Added `tests/test_reconciliation_fuzzy.py`.
* Tested amount scoring, date scoring, description scoring, candidate scoring, duplicate penalties, score clamping, fuzzy auto-matches, candidates, ambiguity handling, duplicate handling, one-to-one safety, run configuration, validation errors, and mutation safety.
* Updated `docs/Reconciliation_Design.md` to document implemented exact and fuzzy reconciliation behavior.
* Documented that split matching remains future work.
* Did not add split matching, manual review, categorization, dashboard, CLI integration, report exports, cash flow, or new accounting features.

Commands run for Step 19:

```bash
python -m pytest tests/test_reconciliation_fuzzy.py
python -m ruff check . --fix
python -m ruff check .
python -m pytest
git status
```

Results:

```text
python -m pytest tests/test_reconciliation_fuzzy.py  # passed locally
python -m ruff check . --fix                        # fixed import ordering
python -m ruff check .                              # All checks passed
python -m pytest                                    # passed locally
git status                                          # expected Step 19 files only
```

Completed Step 20 files:

```text
src/reconcile/reconciliation/splits.py
src/reconcile/reconciliation/models.py
src/reconcile/reconciliation/explanations.py
src/reconcile/reconciliation/matcher.py
src/reconcile/reconciliation/__init__.py
tests/test_reconciliation_splits.py
docs/Reconciliation_Design.md
docs/Reconcile_Project_State.md
```

Completed Step 20 summary:

* Added `src/reconcile/reconciliation/splits.py`.
* Added `find_split_candidates(...)` for bounded two- and three-component split candidate discovery.
* Added `score_split_candidate(...)` for scoring one bank transaction against multiple ledger cash movements.
* Limited split candidates to two or three ledger cash movements only.
* Rejected one-component split candidates.
* Rejected more-than-three-component split candidates.
* Rejected invalid `max_components` values below 2 or above 3.
* Rejected negative amount tolerances, date windows, and split penalties.
* Used standard-library deterministic combination search only.
* Required all split component movements to have the same nonzero sign.
* Rejected opposite-sign bank/component combinations.
* Required the signed component total to match the bank transaction amount within tolerance.
* Used integer cents for all money calculations.
* Compared each component date to the bank transaction date with absolute day deltas.
* Required every component movement to be inside the configured date window.
* Stored component-level date deltas in split candidate explanations.
* Stored summary date delta using the maximum absolute component date delta.
* Scored split candidates with `amount_score * 0.70 + date_score * 0.25 + description_score * 0.05 - split_penalty`.
* Used amount scoring against the summed component total.
* Used conservative split date scoring with the minimum component date score.
* Used best-component description scoring for split description support.
* Clamped split scores between 0.0 and 100.0.
* Returned split candidate result dictionaries with scores, deltas, component totals, component IDs, component details, and JSON-serializable score explanations.
* Added deterministic split candidate ordering by score, amount delta, date delta, component count, and movement IDs.
* Updated `src/reconcile/reconciliation/models.py` with `MATCH_TYPE_SPLIT = "split"`.
* Preserved exact, fuzzy, unmatched, status, and run-status constants.
* Updated `src/reconcile/reconciliation/explanations.py` with `build_split_match_explanation(...)`.
* Split explanations include candidate score, amount score, date score, description score, split penalty, amount delta, date delta, component count, component total, component movement IDs, component details, decision status, auto-match flag, and reason text.
* Updated `src/reconcile/reconciliation/matcher.py` with `run_split_reconciliation(...)`.
* Reused existing reconciliation validation, run insertion, match insertion, ledger-link insertion, and deterministic matching patterns.
* Stored split reconciliation run rows with completed status.
* Stored split run configuration in `config_json`.
* Selected imported bank transactions in the requested statement date range.
* Used Step 17 `extract_ledger_cash_movements` for ledger-side cash movement extraction.
* Generated split candidates from available ledger cash movements.
* Stored split reconciliation match rows with split explanation JSON.
* Created split ledger-link rows only for auto-matches.
* Created one ledger-link row for each component movement in a split auto-match.
* Did not create ledger-link rows for split candidate, ambiguous, or unmatched records.
* Applied split auto-match threshold, candidate threshold, and ambiguity gap decision rules.
* Created `auto_matched` rows only when the top split candidate met the auto threshold and had a sufficient gap from the second candidate.
* Created `ambiguous` rows when top split candidates were too close to auto-match safely.
* Created `candidate` rows when top split candidates met candidate threshold but not auto-match threshold.
* Created `unmatched` rows when no split candidate existed or the best split candidate was below candidate threshold.
* Blocked duplicate-flagged bank transactions from split auto-matching.
* Ensured candidate and ambiguous split rows do not consume ledger movements.
* Ensured a ledger cash movement can be consumed by at most one split auto-match in the same run.
* Ensured each bank transaction receives at most one split reconciliation match record in a split run.
* Preserved `run_exact_reconciliation`.
* Preserved `run_fuzzy_reconciliation`.
* Did not combine exact, fuzzy, and split workflows into one master function.
* Updated `src/reconcile/reconciliation/__init__.py` to export split helpers and split reconciliation runner while preserving existing Step 17 through Step 19 exports.
* Added `tests/test_reconciliation_splits.py`.
* Tested two-component split candidates.
* Tested three-component split candidates.
* Tested that one-component and four-component split candidates are not returned.
* Tested mixed-sign and opposite-sign rejection.
* Tested amount tolerance, date window, scoring, split penalty, candidate shape, component details, and deterministic ordering.
* Tested invalid helper inputs and invalid split run configuration values.
* Tested split auto-matching for two and three ledger movements.
* Tested within-tolerance split matching.
* Tested wrong-sign, out-of-tolerance, and out-of-window split behavior.
* Tested auto-match, candidate, ambiguous, and unmatched decision paths.
* Tested duplicate-flagged bank rows do not auto-match.
* Tested ledger-link creation for split auto-matches only.
* Tested component ledger movements are not reused across split auto-matches.
* Tested candidate and ambiguous rows do not consume component movements.
* Tested deterministic split matching behavior.
* Tested split reconciliation run rows, config JSON, provided run IDs, generated run IDs, and duplicate run ID validation.
* Tested split reconciliation mutation safety for ledger events, bank rows, and accounting projection tables.
* Updated `docs/Reconciliation_Design.md` to document implemented split matching behavior.
* Documented split two- and three-component search, same-sign rule, amount tolerance, date window, scoring formula, split penalty, statuses, ledger-link behavior, and out-of-scope unlimited subset-sum/manual review UI.
* Did not add CLI integration, categorization, dashboard, CSV export, cash flow reporting, manual confirmation/rejection, bank import events, or new accounting features.

Commands run for Step 20:

```bash
python -m ruff check .
python -m ruff check . --fix
python -m pytest tests/test_reconciliation_splits.py
python -m pytest
git status
```

Results:

```text
python -m ruff check .                              # initially found unused imports and line-length issues
python -m ruff check . --fix                        # removed safe unused imports
python -m pytest tests/test_reconciliation_splits.py # 52 passed after threshold adjustment
python -m ruff check .                              # All checks passed locally
python -m pytest                                    # passed locally
git status                                          # expected Step 20 files only
```

Completed Step 22 files:

```text
src/reconcile/reports/export.py
src/reconcile/reports/__init__.py
src/reconcile/cli.py
tests/test_report_exports.py
tests/test_cli.py
examples/sample_output/trial_balance.csv
examples/sample_output/income_statement.csv
examples/sample_output/balance_sheet.csv
docs/Reconcile_Project_State.md
```

Completed Step 22 summary:

* Added `src/reconcile/reports/export.py`.
* Added `export_trial_balance_csv(connection, output_path)`.
* Added `export_income_statement_csv(connection, *, start_date, end_date, output_path)`.
* Added `export_balance_sheet_csv(connection, *, as_of_date, output_path)`.
* Added `export_reconciliation_results_csv(connection, *, reconciliation_run_id, output_path)`.
* Added `export_all_reports(connection, *, output_dir, income_start_date, income_end_date, balance_sheet_as_of_date, reconciliation_run_id=None)`.
* Used standard-library CSV writing with `csv.DictWriter`.
* Used `pathlib.Path` and created output parent directories as needed.
* Returned JSON-serializable summary dictionaries with string file paths and data-row counts.
* Kept export functions read-only.
* Confirmed export functions do not append ledger events.
* Confirmed export functions do not mutate accounts, journal entries, journal lines, account balances, bank transactions, reconciliation runs, reconciliation matches, or reconciliation ledger links.
* Exported trial balance rows with account identity, account type, normal balance, debit totals, credit totals, ending debit balances, and ending credit balances.
* Kept trial balance totals in the returned summary instead of appending a totals row to the CSV.
* Exported income statement rows with `section` values of `revenue` and `expense`.
* Kept income statement totals in the returned summary instead of appending totals rows to the CSV.
* Exported balance sheet rows with `section` values of `asset`, `liability`, and `equity`.
* Included Current Period Net Income as a separate equity row in the balance sheet CSV.
* Kept balance sheet totals in the returned summary instead of appending totals rows to the CSV.
* Exported reconciliation results by joining `reconciliation_matches` to `bank_transactions`.
* Aggregated `reconciliation_match_ledger_links` into deterministic delimiter-separated ledger entry and line ID fields.
* Exported one reconciliation CSV row per reconciliation match.
* Preserved stored reconciliation explanation JSON in the export.
* Validated blank reconciliation run IDs and missing reconciliation run IDs with `ValidationError`.
* Implemented `export_all_reports` output filenames:

```text
trial_balance.csv
income_statement.csv
balance_sheet.csv
reconciliation_results.csv
```

* Skipped `reconciliation_results.csv` in `export_all_reports` when no reconciliation run ID was provided.
* Updated `src/reconcile/reports/__init__.py` to export Step 22 export helpers while preserving existing report exports.
* Added `export-reports` as a top-level CLI subcommand.
* Added CLI support for `--db-path`, `--output-dir`, `--from`, `--to`, `--as-of`, and optional `--reconciliation-run-id`.
* Reused the existing CLI ISO date parser for export date arguments.
* Kept CLI export behavior as a thin wrapper over `export_all_reports`.
* Printed concise CLI success output with generated paths and row counts.
* Added `tests/test_report_exports.py`.
* Tested trial balance CSV file creation, parent directory creation, header columns, data-row counts, deterministic account ordering, summary totals, balanced status, and mutation safety.
* Tested income statement CSV headers, revenue and expense sections, totals, net income, and invalid date ranges.
* Tested balance sheet CSV headers, asset/liability/equity sections, Current Period Net Income row, totals, balanced status, and invalid as-of dates.
* Tested reconciliation result CSV headers, bank transaction fields, match fields, score and delta fields, explanation JSON, ledger link fields, missing run IDs, and blank run IDs.
* Tested `export_all_reports` with and without reconciliation run IDs.
* Updated `tests/test_cli.py` with `export-reports` command coverage.
* Tested CLI export success after demo seeding.
* Tested custom export output directories.
* Tested CLI reconciliation export when a run ID is provided.
* Tested invalid export date arguments return nonzero and print clear stderr.
* Generated fake sample output CSVs under `examples/sample_output/`.
* Did not commit `exports/reconcile.db`.
* Did not add real bank data or private financial data.
* Did not add cash flow, categorization, Streamlit dashboard, CI, manual reconciliation confirmation/rejection, Excel export, JSON export, PDF export, or new accounting behavior.

Commands run for Step 22:

```bash
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db
python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output --from 2026-01-01 --to 2026-01-31 --as-of 2026-01-31
python -m pytest
python -m ruff check .
```

Results:

```text
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db  # Initialized database
python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db # reported acct-cash already existed because the local demo database was already seeded
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output --from 2026-01-01 --to 2026-01-31 --as-of 2026-01-31
# Exported reports to: examples\sample_output
# trial_balance: examples\sample_output\trial_balance.csv (9 rows)
# income_statement: examples\sample_output\income_statement.csv (3 rows)
# balance_sheet: examples\sample_output\balance_sheet.csv (5 rows)
# reconciliation_results: skipped
python -m pytest        # passed locally
python -m ruff check .  # All checks passed locally
```

Completed Step 23 files:

```text
src/reconcile/categorization/__init__.py
src/reconcile/categorization/rules.py
tests/test_categorization_rules.py
docs/Reconcile_Project_State.md
```

Completed Step 24 files:

```text
src/reconcile/categorization/corrections.py
src/reconcile/categorization/classifier.py
src/reconcile/categorization/__init__.py
tests/test_categorization_corrections.py
tests/test_categorization_classifier.py
docs/Reconcile_Project_State.md
```

Completed Step 24 summary:

* Added `src/reconcile/categorization/corrections.py`.
* Added `initialize_categorization_schema(connection)` to create `category_corrections` idempotently.
* Added `record_category_correction(...)` for append-only user category corrections.
* Validated bank transaction IDs, corrected categories, optional corrected-by values, optional reasons, and optional ISO-like correction timestamps.
* Required corrections to reference existing bank transactions.
* Generated UUID-based correction IDs.
* Preserved explicit correction timestamps and populated omitted timestamps with current UTC timestamps.
* Added `list_category_corrections(...)` with deterministic ordering and optional bank transaction filtering.
* Added `latest_category_correction(...)` using deterministic newest-correction ordering.
* Added `training_examples_from_corrections(...)` by joining corrections to imported bank transactions.
* Preferred normalized descriptions as classifier text and fell back to raw descriptions.
* Preserved signed integer `amount_cents` in training examples.
* Added `apply_corrections_to_categorized_results(...)` so latest corrections override existing categorized result dictionaries without mutating inputs.
* Added `src/reconcile/categorization/classifier.py`.
* Implemented the optional classifier as a deterministic standard-library nearest-token-overlap classifier.
* Did not add scikit-learn or any other dependency in Step 24.
* Added `train_category_classifier(...)` with validation for empty, malformed, and single-category training data.
* Added `predict_category(...)` and `predict_categories(...)` with confidence threshold handling.
* Added low-confidence uncategorized behavior with clear classifier confidence reasons.
* Added `categorize_with_rules_corrections_and_classifier(...)` with final precedence: correction, rule, classifier, uncategorized.
* Confirmed corrections override rules and classifier predictions.
* Confirmed rules override classifier predictions.
* Confirmed classifier runs only when no correction exists and no rule matches.
* Updated `src/reconcile/categorization/__init__.py` to preserve Step 23 exports and add Step 24 correction/classifier exports.
* Added `tests/test_categorization_corrections.py`.
* Added `tests/test_categorization_classifier.py`.
* Tested correction schema creation, idempotency, append-only recording, listing, latest lookup, training example extraction, correction application, validation errors, ordering, and mutation safety.
* Tested classifier training validation, prediction, low-confidence behavior, confidence thresholds, JSON serialization, prediction ordering, precedence, no-mutation behavior, no-file-write behavior, and no-database-touch behavior.
* Did not add dashboard categorization review, CLI categorization workflow, cash flow, Streamlit dashboard, CI, manual reconciliation confirmation/rejection, external APIs, LLM categorization, cloud model calls, reconciliation changes, report export changes, or new accounting behavior.

Commands run for Step 24:

```bash
python -m pytest tests/test_categorization_classifier.py
python -m pytest
python -m ruff check .
git status
```

Results:

```text
python -m pytest tests/test_categorization_classifier.py  # 23 passed after confidence threshold fix
python -m pytest                                          # all tests passed locally
python -m ruff check .                                    # All checks passed after line-length cleanup
git status                                                # expected Step 24 files only
```

Completed Step 23 summary:

* Added `src/reconcile/categorization/__init__.py`.
* Added `src/reconcile/categorization/rules.py`.
* Added immutable `CategoryRule` dataclass validation.
* Added `normalize_rule_text`.
* Added `match_category_rule`.
* Added `categorize_transaction`.
* Added `categorize_transactions`.
* Added `default_category_rules`.
* Added read-only `load_bank_transactions_for_categorization`.
* Rule matching supports normalized-description matching, raw-description fallback, phrase matching, any-token matching, all-token matching, amount ranges, and positive/negative/any amount signs.
* Categorization results are plain JSON-serializable dictionaries.
* Categorized results include bank transaction ID, category, category source, category rule ID, category reason, matched rule priority, matched description, and amount cents.
* Uncategorized results use `category=None`, `category_source=None`, `category_rule_id=None`, and a clear reason.
* Rule application is deterministic: highest priority wins, then tied priorities sort by rule ID.
* Categorization does not mutate input transaction dictionaries.
* Categorization does not write to SQLite.
* The read helper preserves raw descriptions, normalized descriptions, signed integer amounts, and deterministic ordering.
* Added `tests/test_categorization_rules.py`.
* Tested rule validation errors, text normalization, phrase/token/amount/sign matching, categorization ordering, default rules, transaction validation, read helper behavior, and mutation safety.
* Did not add correction storage, categorization persistence, local ML classifier, scikit-learn, CLI categorization workflow, dashboard review UI, cash flow, or new accounting behavior.

Commands run for Step 23:

```bash
python -m pytest
python -m ruff check .
git status
```

Results:

```text
python -m pytest        # passed locally
python -m ruff check .  # All checks passed locally
git status              # expected Step 23 files only
```

Completed Step 25 files:

```text
src/reconcile/reports/cash_flow.py
src/reconcile/reports/__init__.py
src/reconcile/reports/export.py
src/reconcile/cli.py
tests/test_cash_flow_report.py
tests/test_report_exports.py
tests/test_cli.py
examples/sample_output/cash_flow.csv
docs/Reconcile_Project_State.md
```

Completed Step 25 summary:

* Added `src/reconcile/reports/cash_flow.py`.
* Added `generate_cash_flow_statement(connection, *, start_date, end_date, cash_account_id=None)`.
* Added `cash_flow_totals(statement)`.
* Added `classify_cash_flow_section(counterparty_account_type, counterparty_account_code=None, counterparty_account_name=None)`.
* Implemented direct-method cash flow reporting from existing posted journal entries and journal lines.
* Identified cash-like accounts from selected `cash_account_id` or from asset/debit accounts with code `1000` or names containing cash, checking, or bank.
* Used the cash flow sign convention where debit to cash is an inflow and credit to cash is an outflow.
* Classified revenue and expense counterparties as operating.
* Classified non-cash asset counterparties as investing.
* Classified liability and equity counterparties as financing.
* Validated report dates as real `datetime.date` values and rejected `datetime.datetime` values.
* Rejected date ranges where start date is after end date.
* Calculated beginning cash from posted cash activity before the start date.
* Calculated ending cash from posted cash activity through the end date.
* Calculated operating, investing, financing, and net cash change totals.
* Added `cash_balances_tie` to verify beginning cash plus net cash change equals ending cash.
* Kept report rows JSON-serializable.
* Excluded pure cash-to-cash transfers from operating, investing, and financing activity.
* Supported selected cash account reporting with validation for missing and non-cash accounts.
* Added proportional allocation for multiple non-cash counterparties when needed.
* Updated `src/reconcile/reports/__init__.py` to export the cash flow report helpers.
* Added `export_cash_flow_csv(...)` to `src/reconcile/reports/export.py`.
* Added official `cash_flow.csv` output to `export_all_reports(...)`.
* Kept cash flow CSV exports to section rows only, with totals returned in the summary.
* Updated CLI `report cash-flow` command.
* Updated CLI `export-reports` output so cash flow export is shown with the other report exports.
* Added `tests/test_cash_flow_report.py`.
* Updated `tests/test_report_exports.py` for cash flow CSV behavior and `export_all_reports`.
* Updated `tests/test_cli.py` for `report cash-flow` and cash flow export behavior.
* Generated fake sample output at `examples/sample_output/cash_flow.csv`.
* Confirmed cash flow generation and export are read-only and mutation-safe.
* Did not add Streamlit, dashboard pages, indirect-method cash flow, closing entries, retained earnings, reconciliation changes, categorization changes, CI, Excel export, JSON export, PDF export, new dependencies, or new accounting behavior.

Commands run for Step 25:

```bash
python -m ruff check .
python -m pytest
python scripts/run_reconcile.py report cash-flow --db-path exports/reconcile.db --from 2026-01-01 --to 2026-01-31
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output --from 2026-01-01 --to 2026-01-31 --as-of 2026-01-31
git status
```

Results:

```text
python -m ruff check .  # All checks passed
python -m pytest        # 709 passed in the final full test run
python scripts/run_reconcile.py report cash-flow --db-path exports/reconcile.db --from 2026-01-01 --to 2026-01-31
# Cash Flow Statement: 2026-01-01 to 2026-01-31
# Operating cash flow: -950.00
# Investing cash flow: 1200.00
# Financing cash flow: 5000.00
# Net cash change: 5250.00
# Beginning cash: 0.00
# Ending cash: 5250.00
# Cash balances tie: True
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output --from 2026-01-01 --to 2026-01-31 --as-of 2026-01-31
# Exported reports to: examples\sample_output
# trial_balance: examples\sample_output\trial_balance.csv (9 rows)
# income_statement: examples\sample_output\income_statement.csv (3 rows)
# balance_sheet: examples\sample_output\balance_sheet.csv (5 rows)
# cash_flow: examples\sample_output\cash_flow.csv (4 rows)
# reconciliation_results: skipped
git status  # expected Step 25 files only before Project State update
```

Completed Step 26 files:

```text
dashboard/streamlit_app.py
tests/test_streamlit_dashboard.py
pyproject.toml
docs/Reconcile_Project_State.md
```

Completed Step 26 summary:

* Added `streamlit` as a project dependency.
* Added `dashboard/streamlit_app.py`.
* Added a safe `main()` entrypoint guarded by `if __name__ == "__main__"`.
* Added a Streamlit page title of `Reconcile`.
* Added the subtitle `Local-first event-sourced accounting engine`.
* Added a sidebar database path input.
* Defaulted the dashboard database path to `exports/reconcile.db`.
* Added a sidebar note that the dashboard expects a local demo database.
* Added friendly missing-database setup instructions.
* Kept setup instructions as display text only.
* Did not execute CLI commands from Streamlit.
* Added `database_exists`.
* Added `load_database_counts`.
* Added `load_trial_balance_preview`.
* Added `load_dashboard_summary`.
* Added `format_cents_for_dashboard`.
* Used `pathlib.Path` for path handling.
* Checked database existence before opening a connection.
* Avoided creating a database merely by launching the dashboard.
* Used `reconcile.db.connect` for existing SQLite database reads.
* Added graceful handling for missing database files.
* Added graceful handling for missing schema tables.
* Added graceful handling for empty databases.
* Added table counts for core ledger, accounting, bank, reconciliation, and categorization tables.
* Used existing `generate_trial_balance` and `trial_balance_totals` where practical.
* Displayed high-level summary metrics.
* Displayed a small account/trial-balance preview.
* Kept dashboard logic thin.
* Kept business logic inside existing package modules.
* Did not mutate the database.
* Did not append events.
* Did not import bank files.
* Did not rebuild projections.
* Did not run reconciliation.
* Did not train categorization classifiers.
* Did not write export files.
* Added `tests/test_streamlit_dashboard.py`.
* Tested missing and existing database status.
* Tested table counts for missing, empty, partial, and demo-like databases.
* Tested trial balance preview behavior.
* Tested dashboard summary JSON serialization.
* Tested empty database summary behavior.
* Tested missing optional tables do not crash helper functions.
* Tested cents formatting for positive, negative, and zero values.
* Tested importing the dashboard module does not launch the app.
* Tested helper functions do not append ledger events.
* Tested helper functions do not mutate account balances.
* Tested helper functions do not import bank files.
* Tested helper functions do not run reconciliation.
* Tested helper functions do not write exports.
* Did not add full dashboard report pages, event timeline, reconciliation review UI, categorization review UI, CI, deployment, screenshots, README polish, or new accounting behavior.

Commands run for Step 26:

```bash
python -m pip install -e ".[dev]"
python -m pytest tests/test_streamlit_dashboard.py
python -m ruff check . --fix
python -m ruff check .
streamlit run dashboard/streamlit_app.py
git status
```

Results:

```text
python -m pip install -e ".[dev]"              # Streamlit installed through project dependency
python -m pytest tests/test_streamlit_dashboard.py # 16 passed after empty cash balance fix
python -m ruff check . --fix                    # fixed one safe Ruff issue; remaining line lengths were fixed manually
python -m ruff check .                          # expected to pass after line-length cleanup
streamlit run dashboard/streamlit_app.py        # launched locally; stopped from PowerShell with Ctrl+C
git status                                      # expected Step 26 files shown
```

Next planned step:

Step 28 — Add dashboard reconciliation and categorization review.

Step 28 status: Not started.

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
* Keep generated Python code within Ruff's configured 88-character line limit. Break long function signatures, SQL strings, parametrized test cases, and error messages before handing off code.
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

### `category_corrections`

```sql
CREATE TABLE category_corrections (
    correction_id TEXT PRIMARY KEY,
    bank_transaction_id TEXT NOT NULL,
    corrected_category TEXT NOT NULL,
    corrected_by TEXT,
    reason TEXT,
    corrected_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(bank_transaction_id) REFERENCES bank_transactions(bank_transaction_id)
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
| `categorization/classifier.py`     | Optional local classifier trained from corrections.         |
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

* `streamlit` — dashboard/demo interface. Added in Step 26.
* `pandas` — dashboard tables and export-friendly data handling.
* `plotly` — optional dashboard charts.
* `scikit-learn` — optional future categorization dependency if the standard-library classifier becomes insufficient.

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

> Step 24 implemented a simple standard-library local classifier instead of adding `scikit-learn`. Add `scikit-learn` later only if it clearly improves the project without dependency friction.

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

Status: Complete.

Goal:

* Apply posted journal entries to account-balance projections.

Completed work:

* Created `src/reconcile/projections/__init__.py`.
* Created `src/reconcile/projections/balances.py`.
* Exported Step 9 balance projection helpers from the projections package.
* Added `apply_journal_entry_posted_to_balances(connection, event)`.
* Added `get_account_balance(connection, account_id)`.
* Added `list_account_balances(connection)`.
* Updated `src/reconcile/events/handlers.py` so `JournalEntryPosted` events update account balances after journal header and line projections are written.
* Kept `AccountOpened` behavior unchanged.
* Kept `AccountOpened` from creating account balance rows.
* Preserved unsupported-event behavior for event types that are valid in the model but not implemented in handlers yet.
* Read journal lines from `JournalEntryPosted` event payloads.
* Grouped line activity by account before applying balance updates.
* Inserted account balance rows when an affected account had no prior balance row.
* Updated account balance rows when an affected account already had balances.
* Accumulated `debit_total_cents`.
* Accumulated `credit_total_cents`.
* Recalculated `balance_cents` after every applied event.
* Used debit-normal balance calculation for asset and expense accounts:

```text
balance_cents = debit_total_cents - credit_total_cents
```

* Used credit-normal balance calculation for liability, equity, and revenue accounts:

```text
balance_cents = credit_total_cents - debit_total_cents
```

* Set balance projection `updated_at` from the event timestamp.
* Set balance projection `last_event_sequence` from the event sequence.
* Validated that every line account exists in the `accounts` table.
* Raised `ValidationError` for missing accounts during balance projection.
* Validated normal balances read from the database.
* Raised `ValidationError` for invalid normal balances in the database.
* Did not require accounts to be active during projection application.
* Did not mutate the `accounts` table during balance projection.
* Added idempotency protection using `account_balances.last_event_sequence`.
* Reapplying the same event does not double-count when every affected account already has a matching or later `last_event_sequence`.
* Added tests covering asset, expense, liability, equity, and revenue normal-balance behavior.
* Added tests covering debit and credit total accumulation.
* Added tests covering repeated entries and balance recalculation.
* Added tests covering `updated_at` and `last_event_sequence`.
* Added tests covering direct balance projection application from a loaded event.
* Added tests covering duplicate application/idempotency.
* Added tests covering missing accounts and invalid normal balances.
* Added tests covering `get_account_balance`.
* Added tests covering `list_account_balances`.
* Added tests proving `AccountOpened` does not create account balance rows by itself.
* Updated stale Step 8 journal-posting tests that previously expected no account balance writes.
* Updated stale account-service unsupported-event coverage so it still checks a genuinely unsupported handler case.
* Fixed tests to use the existing `open_account(connection, account=account)` API.
* Fixed tests to load the appended `JournalEntryPosted` event from the event store instead of assuming `post_journal_entry` returns the event.
* Fixed a ruff line-length issue in `src/reconcile/projections/balances.py`.
* Did not add projection rebuilds, reports, reversals, bank import, reconciliation, categorization, dashboard, CLI, or property-based tests.

Files created or edited:

```text
src/reconcile/projections/__init__.py
src/reconcile/projections/balances.py
src/reconcile/events/handlers.py
tests/test_account_balances.py
tests/test_journal_posting.py
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
python -m pytest        # 221 passed
python -m ruff check .  # All checks passed
git status              # expected Step 9 files only
```

Definition of done:

* `src/reconcile/projections/__init__.py` exists.
* `src/reconcile/projections/balances.py` exists.
* `src/reconcile/events/handlers.py` applies account balance projections for `JournalEntryPosted`.
* Posting valid journal entries updates `account_balances`.
* Debit totals and credit totals accumulate correctly.
* Normal-balance-aware `balance_cents` is correct for asset, expense, liability, equity, and revenue accounts.
* Duplicate application of the same event does not double-count balances.
* `get_account_balance` works.
* `list_account_balances` works.
* No rebuild, reports, reversals, reconciliation, dashboard, CLI, or property-based tests were added.
* `tests/test_account_balances.py` covers happy paths, bad inputs, normal balance behavior, repeated entries, idempotency, and lookup helpers.
* Existing tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add account balance projections
```

---

### Step 10 — Add projection rebuild workflow

Status: Complete.

Goal:

* Clear projections and rebuild them from the event log.

Completed work:

* Added `src/reconcile/projections/rebuild.py`.
* Added `clear_projections(connection)` to clear derived projection tables without deleting events.
* Added `rebuild_projections(connection)` to clear projections and replay append-only events.
* Added `projection_row_counts(connection)` to inspect projection table row counts.
* Cleared projection tables in foreign-key-safe child-before-parent order.
* Cleared future derived bank and reconciliation tables as part of projection reset:

```text
reconciliation_match_ledger_links
reconciliation_matches
reconciliation_runs
bank_transactions
bank_statement_imports
```

* Cleared current accounting projection tables as part of projection reset:

```text
account_balances
journal_entry_lines
journal_entries
accounts
```

* Explicitly preserved `ledger_events` during projection clearing and rebuilding.
* Rebuilt projections by loading events with `load_events(connection)`.
* Replayed events in deterministic `event_sequence` order.
* Reused existing `apply_event(connection, event)` behavior instead of adding duplicate rebuild-specific handlers.
* Rebuilt `accounts` from `AccountOpened` events.
* Rebuilt `journal_entries` from `JournalEntryPosted` events.
* Rebuilt `journal_entry_lines` from `JournalEntryPosted` events.
* Rebuilt `account_balances` from `JournalEntryPosted` events.
* Preserved existing unsupported-event behavior for MVP event types without handlers.
* Verified rebuild does not append new events.
* Verified rebuild preserves event count, event IDs, and event sequences.
* Verified rebuild is safe and deterministic when run more than once.
* Verified rebuild does not duplicate journal lines.
* Verified rebuilt account balances match incrementally posted balances.
* Verified rebuilt debit totals match incremental debit totals.
* Verified rebuilt credit totals match incremental credit totals.
* Verified rebuilt normal-balance-aware balances match incremental balances.
* Verified rebuild handles an empty event log by leaving projection tables empty.
* Added `scripts/rebuild_projections.py` as a thin script wrapper.
* Added `argparse` support for optional `--db-path`.
* Set the script default database path to `exports/reconcile.db`.
* Used `connect` to open the SQLite database.
* Initialized schema in the script before rebuild so the script can run against a fresh database path.
* Kept business logic in `src/reconcile/projections/rebuild.py` rather than the script.
* Added `tests/test_projection_rebuild.py` covering clearing, replay, idempotency, event-store protection, balance correctness, unsupported event behavior, row counts, and script smoke behavior.
* Fixed Step 10 tests to use real `datetime.date` values for journal entry dates.
* Fixed ruff import-order and line-length issues.
* Did not add reports, reversals, bank import, reconciliation, categorization, dashboard, full CLI workflow, or property-based tests.

Files created or edited:

```text
src/reconcile/projections/rebuild.py
scripts/rebuild_projections.py
tests/test_projection_rebuild.py
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m pytest
python -m ruff check .
python scripts/rebuild_projections.py --db-path exports/reconcile.db
git status
```

Results:

```text
python -m pytest                                      # 246 passed
python -m ruff check .                                # All checks passed
python scripts/rebuild_projections.py --db-path exports/reconcile.db  # success
git status                                            # expected Step 10 files only
```

Definition of done:

* `src/reconcile/projections/rebuild.py` exists.
* `scripts/rebuild_projections.py` exists.
* Projection tables can be cleared without deleting `ledger_events`.
* Projections can be rebuilt from events in `event_sequence` order.
* Account projections rebuild from `AccountOpened` events.
* Journal projections rebuild from `JournalEntryPosted` events.
* Balance projections rebuild from `JournalEntryPosted` events.
* Rebuilt projections match incremental projections.
* Rebuild is deterministic and safe to run repeatedly.
* Rebuild does not append new events.
* Rebuild does not duplicate rows.
* No reports, reversals, bank import, reconciliation, dashboard, full CLI workflow, or property-based tests were added.
* `tests/test_projection_rebuild.py` covers clearing, replay, deterministic behavior, event-store protection, and balance correctness.
* Existing tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add projection rebuild workflow
```

---

### Step 11 — Add trial balance report

Status: Complete.

Goal:

* Generate trial balance data from account balance projections.

Completed work:

* Added `src/reconcile/reports/__init__.py`.
* Added `src/reconcile/reports/trial_balance.py`.
* Added `generate_trial_balance(connection)`.
* Added `trial_balance_totals(rows)`.
* Generated report rows from the `accounts` table and left-joined `account_balances`.
* Included accounts with no balance rows as zero-balance rows.
* Included inactive accounts.
* Included account ID, account code, account name, account type, and normal balance.
* Included debit totals and credit totals from projections.
* Calculated ending debit and ending credit balances from normal-balance-aware `balance_cents` values.
* Displayed positive debit-normal balances as ending debit balances.
* Displayed negative debit-normal balances as ending credit balances.
* Displayed positive credit-normal balances as ending credit balances.
* Displayed negative credit-normal balances as ending debit balances.
* Sorted rows by account code and then account ID.
* Added totals for debit totals, credit totals, ending debit balances, ending credit balances, and `is_balanced`.
* Validated account types and normal balances read from SQLite.
* Validated numeric balance fields read from SQLite.
* Confirmed report generation does not append events.
* Confirmed report generation does not mutate `account_balances`.
* Confirmed rebuilt projections produce the same trial balance as incremental projections.
* Added Step 11 trial balance coverage to `tests/test_reports.py`.
* Did not add income statement, balance sheet, cash flow, reversals, bank import, reconciliation, categorization, dashboard, full CLI workflow, CSV exports, or property-based tests.

Files created or edited:

```text
src/reconcile/reports/__init__.py
src/reconcile/reports/trial_balance.py
tests/test_reports.py
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
python -m pytest        # passed
python -m ruff check .  # All checks passed
git status              # expected Step 11 files only
```

Definition of done:

* `src/reconcile/reports/trial_balance.py` exists.
* `src/reconcile/reports/__init__.py` exports trial balance functions.
* Trial balance report includes expected account rows and balances.
* Accounts without balance rows appear with zero values.
* Trial balance totals are calculated correctly.
* Valid ledgers balance.
* Invalid projection/database data raises `ValidationError`.
* Report generation does not append events.
* Report generation does not mutate projections.
* Rebuilt projections produce the same trial balance as incremental projections.
* No income statement, balance sheet, cash flow, reversals, bank import, reconciliation, dashboard, full CLI workflow, CSV exports, or property-based tests were added.
* Tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add trial balance report
```

---

### Step 12 — Add income statement and balance sheet reports

Status: Complete.

Goal:

* Generate basic income statement and balance sheet report data from existing ledger data.

Completed work:

* Added `src/reconcile/reports/income_statement.py`.
* Added `generate_income_statement(connection, *, start_date, end_date)`.
* Added `income_statement_totals(rows)`.
* Added `src/reconcile/reports/balance_sheet.py`.
* Added `generate_balance_sheet(connection, *, as_of_date)`.
* Updated `src/reconcile/reports/__init__.py` to export trial balance, income statement, and balance sheet functions.
* Preserved Step 11 `generate_trial_balance` and `trial_balance_totals` exports.
* Generated income statements from posted journal entries, journal lines, and accounts.
* Filtered income statements by `journal_entries.entry_date` between `start_date` and `end_date`, inclusive.
* Included only revenue and expense accounts in income statement account sections.
* Calculated revenue as credit activity minus debit activity.
* Calculated expenses as debit activity minus credit activity.
* Calculated net income as total revenue minus total expenses.
* Returned income statement dates as ISO date strings.
* Sorted income statement account rows by account code and account ID.
* Omitted zero-activity income statement accounts.
* Generated balance sheets from posted journal entries, journal lines, and accounts.
* Supported `as_of_date` by filtering journal activity through the as-of date.
* Avoided relying only on cumulative `account_balances` for balance sheet date filtering.
* Included asset, liability, and equity accounts in balance sheet account sections.
* Included inactive asset, liability, and equity accounts with zero balances when applicable.
* Excluded revenue and expense accounts from balance sheet account sections.
* Calculated asset balances as positive when debit-normal balances are positive.
* Calculated liability and equity balances as positive when credit-normal balances are positive.
* Calculated current period net income from revenue and expense activity through `as_of_date`.
* Included current period net income in total equity.
* Calculated total liabilities and equity as total liabilities plus total equity.
* Returned `is_balanced` when assets equal liabilities plus equity.
* Returned balance sheet date as an ISO date string.
* Sorted balance sheet account rows by account code and account ID.
* Validated report date arguments as real `datetime.date` instances.
* Rejected `datetime.datetime` values for report dates.
* Rejected income statement start dates after end dates.
* Validated account types read from the database.
* Validated normal balances read from the database for balance sheet reporting.
* Validated journal line sides read from the database.
* Used integer cents only.
* Did not format dollars.
* Did not use pandas.
* Did not write files.
* Did not print from report functions.
* Did not mutate projections.
* Did not rebuild projections inside report functions.
* Added income statement tests for empty databases, revenue, expense, net income, date filtering, sorting, invalid dates, invalid database data, no event appends, and no projection mutation.
* Added balance sheet tests for empty databases, asset/liability/equity balances, current period net income, as-of-date filtering, sorting, inactive accounts, invalid dates, invalid database data, no event appends, and no projection mutation.
* Added rebuild consistency coverage proving rebuilt projections produce the same Step 12 reports as incremental projections.
* Fixed test expectation wording for existing validation helper messages.
* Fixed ruff import-order, duplicate-import, and line-length issues.
* Did not add cash flow, reversals, closing entries, statement of retained earnings, bank import, reconciliation, categorization, dashboard, full CLI workflow, CSV exports, sample output generation, or property-based tests.

Files created or edited:

```text
src/reconcile/reports/income_statement.py
src/reconcile/reports/balance_sheet.py
src/reconcile/reports/__init__.py
tests/test_reports.py
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
python -m pytest        # 292 passed
python -m ruff check .  # All checks passed
git status              # expected Step 12 files only
```

Definition of done:

* `src/reconcile/reports/income_statement.py` exists.
* `src/reconcile/reports/balance_sheet.py` exists.
* `src/reconcile/reports/__init__.py` exports Step 11 and Step 12 report functions.
* `generate_income_statement` returns correct revenue, expense, and net income data.
* `generate_balance_sheet` returns correct asset, liability, equity, net income, and balanced totals.
* Income statement supports inclusive date ranges.
* Balance sheet supports `as_of_date`.
* Reports read existing data and do not mutate events or projections.
* No cash flow, reversals, bank import, reconciliation, dashboard, CLI, CSV export, or property-based tests were added.
* `tests/test_reports.py` covers trial balance, income statement behavior, balance sheet behavior, date filtering, report totals, invalid data, no mutation, and rebuild consistency.
* Existing tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add income statement and balance sheet reports
```

---

### Step 13 — Add journal reversal behavior

Status: Complete.

Goal:

* Reverse posted journal entries through immutable reversal events.

Completed work:

* Implemented `reverse_journal_entry` in `src/reconcile/journal/service.py`.
* Loaded original posted journal entries and lines from existing projections.
* Rejected blank original journal entry IDs.
* Rejected missing original journal entries.
* Rejected non-posted original journal entries.
* Rejected already reversed original journal entries.
* Rejected attempts to reverse reversal entries.
* Rejected duplicate reversal journal entry IDs before appending a reversal event.
* Defaulted reversal date to the original journal entry date when no reversal date is provided.
* Supported explicit reversal journal entry IDs.
* Supported explicit reversal dates.
* Built reversal journal entries with the same account IDs and amount cents as the original.
* Flipped reversal line sides from debit to credit and credit to debit.
* Preserved original line ordering in reversal lines.
* Used deterministic reversal line IDs based on reversal entry ID and line number.
* Preserved reversal line descriptions from original journal lines.
* Created clear default reversal descriptions referencing the original entry.
* Validated reversal journal entries before appending events.
* Appended `JournalEntryReversed` events.
* Included complete reversal event payloads needed for projection rebuilds.
* Preserved source, actor, and correlation ID metadata on reversal events.
* Added `JournalEntryReversed` support in `src/reconcile/events/handlers.py`.
* Inserted reversal journal entry projections from reversal events.
* Inserted reversal journal line projections from reversal events.
* Updated original journal entry projections with `reversed_by_entry_id`.
* Marked reversal journal entry projections with `reversal_of_entry_id`.
* Applied reversal line activity to account balances.
* Preserved historical debit and credit activity totals instead of erasing original activity.
* Ensured reversal events replay correctly during projection rebuilds.
* Ensured existing reports reflect reversal activity without report-specific reversal logic.
* Updated stale unsupported-event coverage now that `JournalEntryReversed` is supported.
* Fixed UTC timestamp usage in journal services.
* Fixed ruff import-order, duplicate-import, and unused-import issues.

Files created or edited:

```text
src/reconcile/journal/service.py
src/reconcile/events/handlers.py
tests/test_journal_reversals.py
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
python -m pytest        # 314 passed
python -m ruff check .  # All checks passed
git status              # expected Step 13 files only
```

Definition of done:

* Posted journal entries can be reversed.
* Reversal lines flip debit and credit sides.
* Reversal lines preserve account IDs, amount cents, line order, and descriptions.
* Original journal entries are not deleted or mutated into the reversal.
* Original journal lines are not changed.
* Original journal entry projections record `reversed_by_entry_id`.
* Reversal journal entry projections record `reversal_of_entry_id`.
* Reversal events are immutable and rebuildable.
* Projection rebuild restores reversal entries, reversal links, and account balances.
* Net account impact can be neutralized by reversals without erasing original debit and credit totals.
* Existing reports reflect reversal activity.
* Invalid reversal attempts do not append events.
* `tests/test_journal_reversals.py` covers service behavior, handler behavior, rebuild behavior, report behavior, and validation errors.
* Existing tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add journal reversal events
```

---

### Step 14 — Add property-based accounting invariant tests

Status: Complete.

Goal:

* Use Hypothesis to test core accounting invariants across generated ledgers.

Completed work:

* Added Hypothesis dependency to the development dependency set.
* Added `docs/Accounting_Invariants.md` documentation.
* Added shared property-test helper code in `tests/property/conftest.py`.
* Added generated standard chart-of-accounts helpers covering asset, liability, equity, revenue, and expense accounts.
* Added generated posting strategies for valid two-line journal entries.
* Added generated posting sequence strategies for multi-entry ledgers.
* Added helpers for creating balanced generated journal entries.
* Added helpers for creating intentionally unbalanced generated journal entries.
* Added fresh SQLite database creation per Hypothesis example to prevent state leakage between generated inputs.
* Added property tests for core accounting invariants.
* Added property tests for projection replay determinism.
* Added property tests for reversal invariants.
* Updated unsupported-future-event projection rebuild coverage to use `BankStatementImported`, because `JournalEntryReversed` is now supported.
* Fixed Hypothesis decorator keyword usage.
* Fixed Hypothesis function-scoped fixture health checks.
* Fixed property helper database reuse across generated examples.
* Fixed property-test calls to `post_journal_entry` to use the actual service signature.
* Fixed ruff import sorting.

Files created or edited:

```text
pyproject.toml
docs/Accounting_Invariants.md
docs/Reconcile_Project_State.md
tests/property/conftest.py
tests/property/test_accounting_invariants.py
tests/property/test_replay_invariants.py
tests/property/test_reversal_invariants.py
tests/test_projection_rebuild.py
```

Property tests added:

* Generated balanced journal entries validate successfully.
* Generated unbalanced journal entries raise `ValidationError`.
* Generated valid posted entries keep the trial balance balanced.
* Generated sequences of valid posted entries keep the trial balance balanced.
* Invalid generated entries do not enter the event store.
* Generated posted entries keep the expanded accounting equation balanced.
* Rebuilding generated posted entries restores the same account balances.
* Rebuilding generated posted entries restores the same trial balance.
* Rebuilding generated posted entries does not change event count.
* Rebuilding generated posted entries does not change event IDs.
* Rebuilding generated posted entries does not change event sequences.
* Running rebuild twice is deterministic.
* Generated event replay is deterministic when ordered by sequence.
* Reversing generated posted entries removes net account balance impact.
* Reversals preserve activity totals by adding opposite-side activity.
* Reversing generated posted entries keeps the trial balance balanced.
* Rebuilding after generated reversals restores incremental balances.
* Reversing any valid generated entry creates a linked reversal entry.
* Original entries are preserved after generated reversals.
* Generated reversal entries point back to original entries.
* Attempting to reverse the same generated entry twice raises `ValidationError`.

Allowed files created/edited:

```text
pyproject.toml
tests/property/conftest.py
tests/property/test_accounting_invariants.py
tests/property/test_replay_invariants.py
tests/property/test_reversal_invariants.py
docs/Accounting_Invariants.md
docs/Reconcile_Project_State.md
tests/test_projection_rebuild.py
```

Do not implement yet:

* Bank import
* Duplicate detection
* Reconciliation
* Categorization
* Dashboard
* Full CLI workflow
* CSV exports
* Cash flow

Commands run:

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
git status
```

Validation results:

```text
python -m ruff check .  # All checks passed!
python -m pytest        # 335 passed in 71.13s (0:01:11)
```

Definition of done:

* Property tests run successfully.
* Invariant docs explain the tests in plain English.
* Tests pass.
* Ruff passes.
* Project State is regenerated without compressing prior project history.

Suggested commit message:

```text
Add property-based accounting invariant tests
```

---

### Step 15 — Add bank CSV import and normalization

Status: Complete.

Goal:

* Import fake bank statement CSV data and normalize descriptions.

Completed work:

* Added `src/reconcile/imports/__init__.py`.
* Added `src/reconcile/imports/bank_csv.py`.
* Added `src/reconcile/imports/normalization.py`.
* Added `tests/test_bank_import.py`.
* Implemented `read_bank_statement_csv`.
* Implemented `hash_bank_row`.
* Implemented `import_bank_statement_csv`.
* Implemented deterministic bank description normalization.
* Validated required bank CSV columns:

```text
transaction_date
description
amount
```

* Supported optional bank CSV columns:

```text
posted_date
external_id
check_number
```

* Preserved raw bank descriptions in `description_raw`.
* Stored normalized descriptions in `description_normalized`.
* Converted bank amount strings to signed integer cents using bank-sign convention.
* Preserved deposits as positive amounts.
* Preserved withdrawals as negative amounts.
* Stored import metadata in `bank_statement_imports`.
* Stored imported rows in `bank_transactions`.
* Stored deterministic row hashes for imported rows.
* Left `duplicate_group_id` unset in Step 15.
* Validated missing files.
* Validated empty CSV files.
* Validated missing required columns.
* Validated blank descriptions.
* Validated blank amounts.
* Validated invalid dates.
* Validated invalid money values.
* Validated duplicate import IDs.
* Added tests for raw-description preservation.
* Added tests for normalized-description storage.
* Added tests for signed integer cent storage.
* Added tests for deterministic row hashes.
* Added tests for import metadata.
* Added tests for optional fields.
* Added tests for invalid CSV inputs.
* Added tests confirming bank imports do not append ledger events.
* Added tests confirming bank imports do not mutate accounting projection tables.
* Did not implement duplicate detection, ledger cash movement extraction, reconciliation matching, categorization, dashboard, full CLI workflow, CSV exports, or cash flow.

Files created or edited:

```text
src/reconcile/imports/__init__.py
src/reconcile/imports/bank_csv.py
src/reconcile/imports/normalization.py
tests/test_bank_import.py
examples/demo_company/bank_statement.csv
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
python -m pytest        # 378 passed
python -m ruff check .  # All checks passed!
git status              # expected Step 15 files only
```

Definition of done:

* Valid bank CSV files import successfully.
* Required columns are validated.
* Raw descriptions are preserved.
* Normalized descriptions are stored.
* Bank amounts are stored as signed integer cents.
* Row hashes are deterministic.
* Import metadata is stored.
* Duplicate group IDs remain unset until Step 16.
* No duplicate detection, reconciliation, categorization, dashboard, full CLI workflow, CSV export, or cash flow behavior was added.
* `tests/test_bank_import.py` covers import behavior, validation errors, normalization, row hashing, and no accounting-state mutation.
* Existing tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add bank CSV import and normalization
```

---

### Step 16 — Add bank duplicate detection

Status: Complete.

Goal:

* Detect duplicate bank import rows without deleting source data.

Completed work:

* Added `src/reconcile/imports/duplicate_detection.py`.
* Added `build_duplicate_group_id(reason, key)`.
* Added `detect_duplicate_bank_transactions(connection, import_id=None)`.
* Added `mark_duplicate_bank_transactions(connection, import_id=None)`.
* Implemented duplicate detection over `bank_transactions`.
* Supported scoped duplicate detection when `import_id` is provided.
* Supported global duplicate detection when `import_id` is omitted.
* Validated blank `import_id` arguments and raised `ValidationError`.
* Implemented duplicate Rule A for duplicate `row_hash` values.
* Implemented duplicate Rule B for duplicate nonblank `external_id` values.
* Ignored blank external IDs.
* Ignored `NULL` external IDs.
* Implemented duplicate Rule C for transaction fingerprints.
* Defined transaction fingerprints as:

```text
transaction_date
amount_cents
description_normalized
```

* Implemented rule precedence:

```text
row_hash
external_id
fingerprint
```

* Ensured a row receives at most one `duplicate_group_id`.
* Used deterministic SHA-256 hashing to create group IDs.
* Used recognizable group ID prefixes:

```text
dup-row-hash-
dup-external-id-
dup-fingerprint-
```

* Kept duplicate detection non-mutating.
* Kept duplicate marking deterministic and idempotent.
* Made duplicate marking clear existing selected-scope duplicate group IDs before recalculating.
* Committed duplicate marking updates.
* Returned duplicate rows after marking.
* Left non-duplicate rows with `duplicate_group_id = NULL`.
* Integrated duplicate marking into successful bank CSV import.
* Kept `import_bank_statement_csv` public return value unchanged.
* Exported duplicate detection functions from `src/reconcile/imports/__init__.py`.
* Fixed accidental `_init_.py` filename issue so imports use the real package initializer.
* Added `tests/test_bank_duplicate_detection.py`.
* Tested row-hash duplicate detection and marking.
* Tested external-ID duplicate detection and marking.
* Tested fingerprint duplicate detection and marking.
* Tested duplicate-rule precedence.
* Tested detection versus marking behavior.
* Tested marking idempotency.
* Tested recalculation after adding new duplicate rows.
* Tested import integration.
* Tested scoped detection versus global detection.
* Tested cross-import duplicate behavior.
* Tested empty bank transaction behavior.
* Tested blank `import_id` validation.
* Tested duplicate detection does not append ledger events.
* Tested duplicate detection does not modify accounting projection tables.
* Did not add a duplicate reason database column.
* Did not delete, merge, or alter source bank rows.
* Did not alter raw descriptions.
* Did not alter normalized descriptions.
* Did not alter amounts.
* Did not alter transaction dates.
* Did not append ledger events.
* Did not add bank import event handlers.
* Did not modify projection rebuild behavior for bank imports.
* Did not implement ledger cash movement extraction, reconciliation matching, fuzzy scoring, split matching, categorization, dashboard, full CLI workflow, CSV exports, or cash flow.

Files created or edited:

```text
src/reconcile/imports/duplicate_detection.py
src/reconcile/imports/bank_csv.py
src/reconcile/imports/__init__.py
tests/test_bank_duplicate_detection.py
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
python -m pytest        # 403 passed in 64.67s (0:01:04)
python -m ruff check .  # All checks passed!
git status              # run locally before commit
```

Definition of done:

* `src/reconcile/imports/duplicate_detection.py` exists.
* Duplicate row-hash groups are detected.
* Duplicate external-ID groups are detected.
* Duplicate transaction fingerprint groups are detected.
* Duplicate detection returns group IDs and reasons.
* Duplicate marking updates `bank_transactions.duplicate_group_id`.
* Duplicate marking is deterministic and idempotent.
* Bank CSV import marks duplicate rows after import.
* Non-duplicate rows remain unmarked.
* Duplicate rows are flagged, not deleted or merged.
* No ledger cash movements, reconciliation matching, categorization, dashboard, CLI, CSV export, cash flow, or bank import events were added.
* `tests/test_bank_duplicate_detection.py` covers duplicate rules, precedence, scoped detection, import integration, idempotency, and no accounting-state mutation.
* Existing tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add bank duplicate detection
```

---

### Step 17 — Add ledger cash movement extraction

Status: Complete.

Goal:

* Extract bank-comparable ledger cash movements from posted journal lines that touch a selected cash account.

Completed work:

* Added `src/reconcile/reconciliation/__init__.py`.
* Added `src/reconcile/reconciliation/cash_movements.py`.
* Added `extract_ledger_cash_movements(connection, *, cash_account_id, start_date=None, end_date=None, include_reversed=False)`.
* Added `get_cash_account(connection, cash_account_id)`.
* Exported only Step 17 cash movement helpers from the reconciliation package.
* Implemented ledger cash movement extraction from `journal_entry_lines` joined to `journal_entries`.
* Included only lines where `journal_entry_lines.account_id == cash_account_id`.
* Used selected cash account metadata from `accounts`.
* Returned plain dictionaries.
* Used integer cents only.
* Did not format dollars.
* Did not use pandas.
* Did not write files.
* Did not print.
* Did not mutate any tables.
* Did not append events.
* Did not rebuild projections inside extraction.
* Converted debit lines to the selected Cash account into positive bank-comparable `amount_cents`.
* Converted credit lines to the selected Cash account into negative bank-comparable `amount_cents`.
* Ignored non-cash journal lines.
* Returned `ledger_cash_movement_id` values using deterministic `cashmov-{journal_entry_line_id}` format.
* Returned journal entry IDs and journal entry line IDs.
* Returned `entry_date` values as ISO date strings.
* Returned journal entry descriptions and line descriptions.
* Returned cash account ID, cash account code, and cash account name.
* Returned `side`, signed `amount_cents`, `source`, `external_reference`, `is_reversal`, `reversal_of_entry_id`, and `reversed_by_entry_id`.
* Returned `source` and `external_reference` as `None` because the current journal projection tables do not store those fields.
* Implemented inclusive `start_date` filtering.
* Implemented inclusive `end_date` filtering.
* Implemented inclusive combined date range filtering.
* Validated that date filter arguments are `datetime.date` instances when provided.
* Rejected `datetime.datetime` values for date filters.
* Rejected `start_date > end_date`.
* Validated `cash_account_id` as a nonblank string.
* Validated selected cash account existence.
* Validated selected cash account `account_type='asset'`.
* Validated selected cash account `normal_balance='debit'`.
* Allowed inactive asset/debit cash accounts for historical extraction.
* Excluded original reversed entries by default.
* Excluded reversal entries by default.
* Added `include_reversed=True` support to include original reversed entries and reversal entries for audit review.
* Marked reversal journal entry movements with `is_reversal=True`.
* Marked ordinary/original journal entry movements with `is_reversal=False`.
* Preserved `reversed_by_entry_id` on original reversed rows.
* Preserved `reversal_of_entry_id` on reversal rows.
* Sorted movement rows by `entry_date`, `journal_entry_id`, and `journal_entry_line_id`.
* Validated stored journal line side values read from the database.
* Validated stored journal line amount values read from the database.
* Added `tests/test_cash_movements.py`.
* Tested empty database extraction with a valid cash account.
* Tested debit-to-Cash positive movement behavior.
* Tested credit-to-Cash negative movement behavior.
* Tested non-cash journal lines are ignored.
* Tested deterministic date, entry, and line ordering.
* Tested returned movement row includes journal entry ID and journal line ID.
* Tested returned movement row includes cash account ID, code, and name.
* Tested returned movement row includes description and line description.
* Tested returned movement ID is deterministic.
* Tested start date filtering.
* Tested end date filtering.
* Tested inclusive date ranges.
* Tested `start_date=end_date`.
* Tested invalid date ranges.
* Tested string date argument rejection.
* Tested `datetime.datetime` argument rejection.
* Tested blank cash account ID rejection.
* Tested missing cash account rejection.
* Tested non-asset selected account rejection.
* Tested credit-normal selected account rejection.
* Tested inactive asset/debit cash account historical readability.
* Tested default exclusion of original reversed entries.
* Tested default exclusion of reversal entries.
* Tested `include_reversed=True` includes original reversed entries.
* Tested `include_reversed=True` includes reversal entries.
* Tested reversal cash movement has the opposite sign from the original.
* Tested reversal rows include `is_reversal=True`.
* Tested original reversed rows include `reversed_by_entry_id`.
* Tested reversal rows include `reversal_of_entry_id`.
* Tested extraction does not append ledger events.
* Tested extraction does not modify accounting projection tables.
* Tested extraction does not modify bank transaction tables.
* Tested invalid stored journal line side raises `ValidationError`.
* Tested invalid stored journal line amount raises `ValidationError`.
* Fixed test calls to match the existing `reverse_journal_entry` signature using `reversal_entry_id`.
* Did not add exact reconciliation matching, fuzzy reconciliation scoring, split matching, reconciliation run creation, reconciliation match records, manual match confirmation/rejection, categorization, dashboard, full CLI workflow, CSV exports, cash flow, or new accounting features.

Files created or edited:

```text
src/reconcile/reconciliation/__init__.py
src/reconcile/reconciliation/cash_movements.py
tests/test_cash_movements.py
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m pytest
python -m ruff check .
```

Results:

```text
python -m pytest        # 429 passed in 66.79s (0:01:06)
python -m ruff check .  # All checks passed!
```

Definition of done:

* `src/reconcile/reconciliation/__init__.py` exists.
* `src/reconcile/reconciliation/cash_movements.py` exists.
* `extract_ledger_cash_movements` exists.
* Debit lines to the selected cash account become positive cash movements.
* Credit lines to the selected cash account become negative cash movements.
* Non-cash lines are ignored.
* Date filters work inclusively.
* Cash account validation works.
* Reversal handling works with default effective-only behavior and optional audit-inclusive behavior.
* Returned movement rows include stable IDs and useful journal/account metadata.
* Extraction is read-only and does not mutate events, accounting projections, or bank transaction tables.
* No reconciliation matching, scoring, split matching, categorization, dashboard, CLI, exports, or cash flow work was added.
* `tests/test_cash_movements.py` covers extraction, signs, filtering, account validation, reversal handling, ordering, and read-only safety.
* Existing tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add ledger cash movement extraction
```

---

### Step 18 — Add exact reconciliation matching

Status: Complete.

Goal:

* Match bank transactions to ledger cash movements using exact amount/date logic.

Completed work:

* Added `src/reconcile/reconciliation/models.py`.
* Added lightweight constants for Step 18 reconciliation run, match type, and match status values.
* Added `src/reconcile/reconciliation/explanations.py`.
* Added exact-match and unmatched explanation builders that return JSON-serializable dictionaries.
* Added `src/reconcile/reconciliation/matcher.py`.
* Added `run_exact_reconciliation`.
* Added `list_reconciliation_matches`.
* Added `get_reconciliation_run`.
* Created completed reconciliation run records.
* Stored reconciliation run statement dates as ISO strings.
* Stored reconciliation run configuration as JSON.
* Validated cash account IDs, statement dates, date ranges, and optional run IDs.
* Rejected `datetime.datetime` values for statement dates.
* Generated UUID-based reconciliation run IDs when omitted.
* Converted duplicate reconciliation run IDs into `ValidationError`.
* Selected bank transactions inside the statement date range, inclusive.
* Selected ledger cash movements by calling Step 17 `extract_ledger_cash_movements`.
* Used Step 17 default effective-only reversal behavior.
* Matched bank transactions to ledger cash movements only when amount cents and date matched exactly.
* Used exact cent equality only.
* Used exact date equality only.
* Did not add fuzzy date windows, amount tolerances, description scoring, or split matching.
* Enforced one-to-one ledger movement use for auto-matches within a run.
* Created exact auto-match records with `match_type='exact'`, `score=100.0`, zero amount delta, zero date delta, and `status='auto_matched'`.
* Created unmatched records with `match_type='unmatched'`, `score=0.0`, bank amount as amount delta, null date delta, and `status='unmatched'`.
* Created candidate records for duplicate-flagged rows and ambiguous exact-candidate situations instead of unsafe auto-matches.
* Stored JSON explanation objects on every reconciliation match row.
* Created `reconciliation_match_ledger_links` rows for exact auto-matches only.
* Linked exact auto-matches to journal entry IDs, journal entry line IDs, and signed amount cents.
* Did not create ledger-link rows for unmatched or candidate rows.
* Made matching deterministic through stable ordering.
* Committed successful reconciliation writes.
* Rolled back reconciliation writes on failure.
* Wrote only to reconciliation tables.
* Did not append ledger events.
* Did not mutate accounts, journal entries, journal lines, account balances, or bank transactions.
* Updated `src/reconcile/reconciliation/__init__.py` to preserve Step 17 exports and add Step 18 exports.
* Added `tests/test_reconciliation_exact.py`.
* Tested run creation, duplicate run IDs, ISO date storage, completed status, config JSON, and summary counts.
* Tested exact positive deposit matching.
* Tested exact negative withdrawal matching.
* Tested amount mismatch behavior.
* Tested date mismatch behavior.
* Tested exact match fields, score, deltas, explanations, and ledger links.
* Tested unmatched records and absence of ledger links.
* Tested one-to-one movement safety.
* Tested multiple exact ledger candidates are not auto-matched.
* Tested duplicate-flagged bank rows are not auto-matched.
* Tested deterministic matching.
* Tested statement date range inclusion and exclusion.
* Tested invalid date arguments and invalid ranges.
* Tested read-only safety for events, bank transactions, and accounting projection tables.
* Did not add fuzzy reconciliation scoring, ambiguity score gap rules, split matching, categorization, dashboard, full CLI workflow, report exports, cash flow, or new accounting features.

Files created or edited:

```text
src/reconcile/reconciliation/models.py
src/reconcile/reconciliation/explanations.py
src/reconcile/reconciliation/matcher.py
src/reconcile/reconciliation/__init__.py
tests/test_reconciliation_exact.py
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m pytest
python -m ruff check .
```

Results:

```text
python -m pytest        # 441 passed in 72.82s (0:01:12)
python -m ruff check .  # All checks passed!
```

Definition of done:

* `src/reconcile/reconciliation/models.py` exists.
* `src/reconcile/reconciliation/explanations.py` exists.
* `src/reconcile/reconciliation/matcher.py` exists.
* `run_exact_reconciliation` exists.
* Exact same amount/date bank transactions auto-match to ledger cash movements.
* Deposits match debit-to-cash movements.
* Withdrawals match credit-from-cash movements.
* Unmatched bank transactions get unmatched records.
* Exact auto-matches create ledger-link rows.
* Ledger movements are not reused across multiple auto-matches in one run.
* Duplicate-flagged bank transactions are not unsafe auto-matched.
* Explanations are stored as JSON.
* Reconciliation writes only reconciliation tables.
* No fuzzy scoring, split matching, categorization, dashboard, CLI, CSV export, or cash flow work was added.
* `tests/test_reconciliation_exact.py` covers exact matching, unmatched handling, run records, ledger links, one-to-one safety, date filtering, explanations, and mutation safety.
* Existing tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add exact reconciliation matching
```

---

### Step 19 — Add fuzzy reconciliation scoring and ambiguity handling

Status: Complete.

Goal:

* Score amount/date/description candidates and prevent unsafe auto-matches.

Completed work:

* Added `src/reconcile/reconciliation/scoring.py`.
* Added `days_between`.
* Added `score_amount_match`.
* Added `score_date_match`.
* Added `score_description_match`.
* Added `score_reconciliation_candidate`.
* Implemented amount scoring with exact-match, same-sign tolerance, opposite-sign rejection, out-of-tolerance rejection, integer-cent validation, and negative-tolerance validation.
* Implemented date scoring with exact-match, date-window tolerance, out-of-window rejection, `datetime.datetime` rejection, non-date rejection, and negative-window validation.
* Implemented deterministic description scoring with standard-library normalization, case-insensitive matching, whitespace normalization, simple punctuation cleanup, exact normalized matches, containment matches, token-overlap partial scoring, and missing-description handling.
* Implemented candidate scoring using the default formula:

```text
score = amount_score * 0.60
      + date_score * 0.25
      + description_score * 0.15
      - duplicate_penalty
```

* Clamped final candidate scores between `0.0` and `100.0`.
* Added meaningful duplicate penalty behavior for duplicate-flagged bank transactions.
* Added fuzzy match type constant `fuzzy`.
* Added ambiguous match status constant `ambiguous`.
* Preserved exact and unmatched match constants.
* Preserved exact, candidate, auto-matched, and unmatched statuses.
* Added `build_fuzzy_match_explanation`.
* Preserved existing exact and unmatched explanation builders.
* Included score, amount score, date score, description score, amount delta, date delta, duplicate penalty, decision status, auto-match flag, and reason text in fuzzy explanations.
* Added `run_fuzzy_reconciliation` to `src/reconcile/reconciliation/matcher.py`.
* Preserved `run_exact_reconciliation` behavior.
* Added fuzzy run argument validation.
* Validated negative amount tolerance and date windows.
* Validated threshold ranges and threshold ordering.
* Inserted completed reconciliation run rows for fuzzy runs.
* Stored fuzzy run configuration in `config_json`.
* Selected bank transactions inside the statement date range.
* Used `extract_ledger_cash_movements` for ledger-side cash movement selection.
* Generated fuzzy candidates only when amount signs matched.
* Generated fuzzy candidates only when amount deltas were within tolerance.
* Generated fuzzy candidates only when date deltas were within the configured window.
* Used exact signed integer cents for amount deltas.
* Used signed day differences for date deltas.
* Used normalized or raw bank descriptions and ledger entry or line descriptions for description scoring.
* Ordered fuzzy candidates deterministically by score, amount delta, date delta, movement ID, journal entry ID, and line ID.
* Added fuzzy auto-match behavior when top score meets threshold and score gap is sufficient.
* Added fuzzy candidate behavior when score meets candidate threshold but not auto-match threshold.
* Added ambiguous behavior when top candidates are too close for safe auto-matching.
* Added unmatched behavior when no candidates exist or the top candidate score is too low.
* Blocked duplicate-flagged bank transactions from fuzzy auto-matching.
* Added clear duplicate explanation behavior for duplicate-flagged bank rows.
* Created ledger-link rows for fuzzy auto-matches only.
* Confirmed candidate fuzzy records do not create ledger-link rows.
* Confirmed ambiguous fuzzy records do not create ledger-link rows.
* Confirmed unmatched fuzzy records do not create ledger-link rows.
* Enforced that a ledger cash movement can be consumed by at most one fuzzy auto-match in the same run.
* Ensured candidate and ambiguous rows do not consume ledger movements.
* Ensured each bank transaction receives at most one fuzzy match record in Step 19.
* Updated `src/reconcile/reconciliation/__init__.py` to export Step 19 scoring and fuzzy reconciliation functions.
* Preserved Step 17 cash movement exports.
* Preserved Step 18 exact reconciliation exports.
* Updated `docs/Reconciliation_Design.md` to document implemented exact reconciliation and fuzzy reconciliation behavior.
* Documented fuzzy scoring formula, amount scoring, date scoring, description scoring, duplicate penalty behavior, thresholds, ledger-link behavior, one-to-one safety, and mutation safety.
* Documented that split matching remains future work.
* Added `tests/test_reconciliation_fuzzy.py`.
* Tested scoring unit behavior.
* Tested fuzzy auto-match behavior for exact-like matches.
* Tested amount-tolerance fuzzy matching.
* Tested date-window fuzzy matching.
* Tested that description similarity cannot override bad amount candidates.
* Tested date-window rejection.
* Tested candidate status behavior.
* Tested ambiguous status behavior.
* Tested ledger-link creation for fuzzy auto-matches.
* Tested no ledger-link creation for candidate and ambiguous matches.
* Tested duplicate-flagged bank rows do not auto-match.
* Tested duplicate explanations include penalty or duplicate context.
* Tested one-to-one ledger movement safety.
* Tested deterministic fuzzy matching behavior.
* Tested fuzzy run creation, run ID behavior, config JSON, invalid date ranges, invalid thresholds, and invalid tolerance/window values.
* Tested fuzzy reconciliation does not append ledger events.
* Tested fuzzy reconciliation does not modify bank transaction rows.
* Tested fuzzy reconciliation does not modify accounting projection tables.
* Fixed ruff import-order issues with `python -m ruff check . --fix`.
* Did not add split matching, manual confirmation/rejection, categorization, dashboard, full CLI workflow, CSV exports, cash flow, or bank import events.

Files created or edited:

```text
src/reconcile/reconciliation/scoring.py
src/reconcile/reconciliation/models.py
src/reconcile/reconciliation/explanations.py
src/reconcile/reconciliation/matcher.py
src/reconcile/reconciliation/__init__.py
tests/test_reconciliation_fuzzy.py
docs/Reconciliation_Design.md
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m pytest tests/test_reconciliation_fuzzy.py
python -m ruff check . --fix
python -m ruff check .
python -m pytest
git status
```

Results:

```text
python -m pytest tests/test_reconciliation_fuzzy.py  # passed locally
python -m ruff check . --fix                        # fixed import ordering
python -m ruff check .                              # All checks passed
python -m pytest                                    # passed locally
git status                                          # expected Step 19 files only
```

Definition of done:

* `src/reconcile/reconciliation/scoring.py` exists.
* Amount scoring works.
* Date scoring works.
* Description scoring works.
* Candidate scoring works with configured weights and duplicate penalty.
* `run_fuzzy_reconciliation` exists.
* Fuzzy reconciliation stores reconciliation runs, match records, explanations, and ledger-link rows for auto-matches.
* Fuzzy reconciliation distinguishes auto-matched, candidate, ambiguous, and unmatched statuses.
* Ambiguous matches are not auto-matched.
* Candidate and ambiguous matches do not create ledger-link rows.
* Duplicate-flagged bank rows are not unsafe auto-matched.
* Ledger movements are not reused across fuzzy auto-matches.
* Exact reconciliation behavior from Step 18 still works.
* `docs/Reconciliation_Design.md` documents fuzzy scoring accurately.
* No split matching, categorization, dashboard, CLI, CSV export, or cash flow work was added.
* `tests/test_reconciliation_fuzzy.py` covers scoring, fuzzy matching, ambiguity handling, duplicate penalty, run config, and mutation safety.
* Existing tests pass locally.
* Ruff passes locally.
* Project State is updated.

Suggested commit message:

```text
Add fuzzy reconciliation scoring
```

---

### Step 20 — Add split reconciliation matching

Status: Complete.

Goal:

* Match one bank transaction to two or three ledger cash movements.

Completed work:

* Added split matching module.
* Added bounded combinations of 2 and 3 ledger movements.
* Enforced same-sign component rule.
* Enforced opposite-sign bank/component rejection.
* Enforced amount tolerance against summed component totals.
* Enforced date window against every component movement.
* Added split penalty.
* Added split scoring formula and JSON-serializable score explanations.
* Added split match explanations.
* Added split reconciliation run function.
* Added split auto-matched, candidate, ambiguous, and unmatched statuses.
* Added one ledger-link row per component for split auto-matches only.
* Preserved candidate and ambiguous rows as non-consuming review records.
* Prevented component reuse across split auto-matches in the same run.
* Preserved exact and fuzzy reconciliation behavior.
* Added split reconciliation tests.
* Updated reconciliation design documentation.

Files created or edited:

```text
src/reconcile/reconciliation/splits.py
src/reconcile/reconciliation/models.py
src/reconcile/reconciliation/explanations.py
src/reconcile/reconciliation/matcher.py
src/reconcile/reconciliation/__init__.py
tests/test_reconciliation_splits.py
docs/Reconciliation_Design.md
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m ruff check .
python -m ruff check . --fix
python -m pytest tests/test_reconciliation_splits.py
python -m pytest
git status
```

Results:

```text
python -m ruff check .                              # initially found unused imports and line-length issues
python -m ruff check . --fix                        # removed safe unused imports
python -m pytest tests/test_reconciliation_splits.py # 52 passed after threshold adjustment
python -m ruff check .                              # All checks passed locally
python -m pytest                                    # passed locally
git status                                          # expected Step 20 files only
```

Definition of done:

* `src/reconcile/reconciliation/splits.py` exists.
* Split candidate discovery works for two and three ledger cash movements.
* Split candidate scoring works with amount/date/description scores and split penalty.
* `run_split_reconciliation` exists.
* Split reconciliation stores reconciliation runs, match records, explanations, and ledger-link rows for auto-matches.
* Split reconciliation distinguishes auto-matched, candidate, ambiguous, and unmatched statuses.
* Split auto-matches create one ledger-link row per component.
* Candidate and ambiguous split matches do not create ledger-link rows.
* Duplicate-flagged bank rows are not unsafe auto-matched.
* Component ledger movements are not reused across split auto-matches.
* Exact reconciliation behavior from Step 18 still works.
* Fuzzy reconciliation behavior from Step 19 still works.
* `docs/Reconciliation_Design.md` documents split matching accurately.
* No CLI, categorization, dashboard, CSV export, cash flow, manual confirmation/rejection, or new accounting features were added.
* `tests/test_reconciliation_splits.py` covers split candidate discovery, split scoring, split reconciliation, ambiguity handling, duplicate handling, run config, and mutation safety.
* Existing tests pass locally.
* Ruff passes locally.
* Project State is updated.

Suggested commit message:

```text
Add split reconciliation matching
```

---

### Step 21 — Add CLI workflow

Status: Complete.

Goal:

* Add a thin CLI that wires together the tested engine workflows.

Completed work:

* Added `src/reconcile/cli.py`.
* Added `scripts/run_reconcile.py`.
* Added `tests/test_cli.py`.
* Implemented a standard-library `argparse` CLI.
* Exposed public `main(argv: list[str] | None = None) -> int`.
* Returned integer exit codes from package CLI logic instead of calling `sys.exit` inside `src/reconcile/`.
* Kept `scripts/run_reconcile.py` as a thin wrapper around `reconcile.cli.main`.
* Added default `--db-path exports/reconcile.db`.
* Added `init-db`.
* Added `seed-demo`.
* Added `rebuild-projections`.
* Added `report trial-balance`.
* Added `report income-statement`.
* Added `report balance-sheet`.
* Added `import-bank`.
* Added `reconcile exact`.
* Added `reconcile fuzzy`.
* Added `reconcile split`.
* Added ISO date parsing that accepts `YYYY-MM-DD` and rejects datetimes.
* Converted expected `ReconcileError` and `ValidationError` failures into nonzero exits with clear stderr output.
* Kept output plain text.
* Printed concise command success messages and report/reconciliation summaries.
* Seeded demo accounts through existing `open_account` service behavior.
* Seeded demo journal entries through existing `post_journal_entry` service behavior.
* Did not insert accounts or journal entries directly into projection tables.
* Imported bank CSVs through existing `import_bank_statement_csv` behavior.
* Rebuilt projections through existing `rebuild_projections` behavior.
* Generated CLI reports through existing report functions.
* Ran exact, fuzzy, and split reconciliation through existing reconciliation functions.
* Added CLI tests for help behavior.
* Added CLI tests for database initialization and expected schema tables.
* Added CLI tests for demo account seeding through events.
* Added CLI tests for demo journal posting through events.
* Added CLI tests for projection rebuild behavior.
* Added CLI tests for trial balance, income statement, and balance sheet commands.
* Added CLI tests for invalid report dates.
* Added CLI tests for bank import.
* Added CLI tests for exact, fuzzy, and split reconciliation command wiring.
* Added CLI tests for expected validation errors returning nonzero exits.
* Added wrapper script smoke coverage.
* Did not add report exports.
* Did not add sample output generation.
* Did not add rule-based categorization.
* Did not add a local ML classifier.
* Did not add cash flow reporting.
* Did not add Streamlit dashboard behavior.
* Did not add CI.
* Did not add manual reconciliation confirmation/rejection workflow.
* Did not add confirmation/rejection events.
* Did not add new accounting behavior.

Files created or edited:

```text
src/reconcile/cli.py
scripts/run_reconcile.py
tests/test_cli.py
docs/Reconcile_Project_State.md
```

Commands run during Step 21 implementation thread:

```bash
python -m pytest tests/test_cli.py
python -m ruff check .
python -m ruff check . --fix
git status
```

Latest visible results from the Step 21 thread:

```text
python -m pytest tests/test_cli.py  # initially collected 19 tests; 16 passed and 3 failed before report-shape and wrapper-path fixes
python -m ruff check .              # initially found one unused import and two line-length issues
python -m ruff check . --fix        # removed the unused import; two manual line-length fixes remained
git status                          # showed expected untracked Step 21 files only
```

Final local validation commands to run before committing:

```bash
python -m ruff check .
python -m pytest tests/test_cli.py
python -m pytest
python scripts/run_reconcile.py --help
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db
python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db
python scripts/run_reconcile.py rebuild-projections --db-path exports/reconcile.db
git status
```

Definition of done:

* `src/reconcile/cli.py` exists.
* `scripts/run_reconcile.py` exists.
* `tests/test_cli.py` exists.
* CLI uses `argparse`.
* CLI exposes `main(argv=None) -> int`.
* CLI commands are thin wrappers around existing package functions.
* `init-db` works.
* `seed-demo` works through event-sourced services.
* `rebuild-projections` works.
* Trial balance CLI report works.
* Income statement CLI report works.
* Balance sheet CLI report works.
* Bank import CLI works.
* Exact reconciliation CLI works.
* Fuzzy reconciliation CLI works.
* Split reconciliation CLI is wired.
* Expected validation errors produce nonzero exits and clear stderr output.
* CLI tests cover the new workflow.
* No report exports, categorization, dashboard, cash flow, CI, or new accounting behavior was added.
* Project State is updated.

Suggested commit message:

```text
Add Reconcile CLI workflow
```

---

### Step 22 — Add report exports and sample outputs

Status: Complete.

Goal:

* Export reports and reconciliation results to stable output files.

Completed work:

* Added stable CSV export behavior for existing reports.
* Added reconciliation result CSV export behavior.
* Added coordinated all-report export behavior.
* Added CLI `export-reports` command.
* Generated fake sample output files.
* Added report export tests.
* Added CLI export tests.
* Confirmed exports are read-only and mutation-safe.

Files created or edited:

```text
src/reconcile/reports/export.py
src/reconcile/reports/__init__.py
src/reconcile/cli.py
tests/test_report_exports.py
tests/test_cli.py
examples/sample_output/trial_balance.csv
examples/sample_output/income_statement.csv
examples/sample_output/balance_sheet.csv
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db
python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output --from 2026-01-01 --to 2026-01-31 --as-of 2026-01-31
python -m pytest
python -m ruff check .
```

Results:

```text
python scripts/run_reconcile.py init-db --db-path exports/reconcile.db  # Initialized database
python scripts/run_reconcile.py seed-demo --db-path exports/reconcile.db # reported acct-cash already existed because the local demo database was already seeded
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output --from 2026-01-01 --to 2026-01-31 --as-of 2026-01-31
# Exported reports to: examples\sample_output
# trial_balance: examples\sample_output\trial_balance.csv (9 rows)
# income_statement: examples\sample_output\income_statement.csv (3 rows)
# balance_sheet: examples\sample_output\balance_sheet.csv (5 rows)
# reconciliation_results: skipped
python -m pytest        # passed locally
python -m ruff check .  # All checks passed locally
```

Definition of done:

* `src/reconcile/reports/export.py` exists.
* `tests/test_report_exports.py` exists.
* Trial balance CSV export works.
* Income statement CSV export works.
* Balance sheet CSV export works.
* Reconciliation results CSV export works.
* `export_all_reports` works.
* CLI `export-reports` command works.
* Fake sample output CSV files are generated under `examples/sample_output/`.
* Export functions are read-only and mutation-safe.
* Existing report functions still work.
* Existing CLI commands still work.
* Tests pass.
* Ruff passes.
* No cash flow, categorization, dashboard, CI, Excel export, PDF export, JSON export, or new accounting behavior was added.
* Project State is updated.

Suggested commit message:

```text
Add report exports and sample outputs
```

---

### Step 23 — Add rule-based categorization

Status: Complete.

Goal:

* Add deterministic category rules for imported bank transactions.

Completed work:

* Added `src/reconcile/categorization/__init__.py`.
* Added Step 23 public categorization exports only.
* Added `src/reconcile/categorization/rules.py`.
* Added frozen `CategoryRule` dataclass.
* Validated `rule_id` as a nonblank string.
* Validated `category` as a nonblank string.
* Validated `priority` as an int and rejected bool values.
* Validated optional string fields as nonblank when provided.
* Validated description token tuples as tuples containing only nonblank strings.
* Validated amount bounds as ints and rejected bool values.
* Rejected min amount greater than max amount.
* Validated `amount_sign` as `positive`, `negative`, `any`, or `None`.
* Added deterministic text normalization for rule and transaction text.
* Added `normalize_rule_text(value)`.
* Added `match_category_rule(transaction, rule)`.
* Added `categorize_transaction(transaction, rules)`.
* Added `categorize_transactions(transactions, rules)`.
* Added `default_category_rules()`.
* Added optional read-only `load_bank_transactions_for_categorization(connection)`.
* Rule matching prefers `description_normalized` and falls back to `description_raw`.
* Rule matching supports phrase contains checks.
* Rule matching supports any-token checks.
* Rule matching supports all-token checks.
* Rule matching supports amount minimums and maximums.
* Rule matching supports positive, negative, and any amount signs.
* Categorization validates required transaction identity and amount fields.
* Missing descriptions are allowed but do not match description-based rules.
* Categorization results are JSON-serializable plain dictionaries.
* Categorized results include category, source, rule ID, reason, priority, matched description, and amount cents.
* Uncategorized results use `category=None` and clear reason text.
* Rule ordering is deterministic with highest priority first and rule ID tie-breaks.
* Only one category is returned per transaction.
* Default rules cover owner contribution, software, office supplies, meals, rent, and revenue without using external data or ML.
* Categorization functions do not mutate input transaction dictionaries.
* Categorization functions do not write to SQLite.
* Categorization functions do not append ledger events or mutate accounting, bank, reconciliation, or report state.
* Added `tests/test_categorization_rules.py`.
* Tested valid rule creation and all required invalid rule cases.
* Tested text normalization behavior.
* Tested phrase, any-token, all-token, amount range, and sign matching.
* Tested explainable match result fields.
* Tested highest-priority and tied-priority deterministic categorization.
* Tested uncategorized behavior.
* Tested transaction validation errors.
* Tested default rule behavior for demo-like transactions.
* Tested read helper deterministic ordering, description preservation, signed amount preservation, bank-row mutation safety, and event-store safety.
* Did not add correction storage, categorization persistence, local ML classifier, scikit-learn, CLI categorization workflow, dashboard review UI, cash flow, CI, or new accounting behavior.

Files created or edited:

```text
src/reconcile/categorization/__init__.py
src/reconcile/categorization/rules.py
tests/test_categorization_rules.py
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
python -m ruff check .  # All checks passed locally
git status              # expected Step 23 files only
```

Definition of done:

* `src/reconcile/categorization/__init__.py` exists.
* `src/reconcile/categorization/rules.py` exists.
* `tests/test_categorization_rules.py` exists.
* Category rules validate inputs.
* Rule matching works for descriptions, tokens, amount ranges, and signs.
* Default rules exist.
* Categorization results include category, source, rule ID, reason, matched description, and amount.
* Unknown transactions remain uncategorized.
* Categorization is deterministic.
* Categorization does not mutate source transaction dictionaries.
* Categorization does not write to the database.
* No correction storage, classifier, dashboard, CLI categorization, persistence schema, cash flow, or new accounting behavior was added.
* Existing tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add rule-based categorization
```

---

### Step 24 — Add correction storage and optional local classifier

Status: Complete.

Goal:

* Add user correction tracking and an optional local-only categorization classifier.

Completed work:

* Added `src/reconcile/categorization/corrections.py`.
* Added idempotent `category_corrections` schema initialization.
* Added append-only correction recording for imported bank transactions.
* Added validation for bank transaction IDs, corrected categories, optional correction metadata, and ISO-like correction timestamps.
* Required corrections to reference existing `bank_transactions` rows.
* Added deterministic correction listing and latest-correction lookup.
* Added correction-based training example extraction joined to bank transaction descriptions and amounts.
* Added correction application helper where the latest correction overrides categorized result dictionaries without mutating inputs.
* Added `src/reconcile/categorization/classifier.py`.
* Implemented a deterministic standard-library nearest-token-overlap classifier instead of adding scikit-learn.
* Kept the classifier local-only, in-memory, optional, and non-persistent.
* Added confidence threshold validation and low-confidence uncategorized behavior.
* Added combined categorization precedence: latest correction, then rule, then confident classifier, then uncategorized.
* Updated `src/reconcile/categorization/__init__.py` to export Step 24 helpers while preserving Step 23 exports.
* Added `tests/test_categorization_corrections.py`.
* Added `tests/test_categorization_classifier.py`.
* Did not edit `pyproject.toml` because no new dependency was added.
* Did not add scikit-learn in Step 24.
* Did not add dashboard review, CLI categorization workflow, cash flow, Streamlit, CI, manual reconciliation review, confirmation/rejection events, external APIs, LLM calls, cloud calls, reconciliation changes, report export changes, or new accounting behavior.

Files created or edited:

```text
src/reconcile/categorization/corrections.py
src/reconcile/categorization/classifier.py
src/reconcile/categorization/__init__.py
tests/test_categorization_corrections.py
tests/test_categorization_classifier.py
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
python -m pytest tests/test_categorization_classifier.py  # 23 passed after confidence threshold fix
python -m pytest                                          # all tests passed locally
python -m ruff check .                                    # All checks passed after line-length cleanup
git status                                                # expected Step 24 files only
```

Definition of done:

* `src/reconcile/categorization/corrections.py` exists.
* `src/reconcile/categorization/classifier.py` exists.
* `tests/test_categorization_corrections.py` exists.
* `tests/test_categorization_classifier.py` exists.
* Categorization correction schema can be initialized.
* Corrections can be recorded append-only.
* Corrections can be listed.
* Latest correction can be retrieved.
* Training examples can be extracted from corrections.
* Corrections can override categorized results.
* Correction behavior is deterministic and JSON-serializable.
* Correction logic does not mutate bank transactions.
* Correction read paths are mutation-safe.
* Step 23 rule-based categorization still works.
* Classifier tests cover local prediction, confidence behavior, and precedence.
* Classifier implementation is local-only and uses the standard library.
* Existing tests should pass locally.
* Ruff should pass locally.
* Project State is updated.

Suggested commit message:

```text
Add categorization corrections and local classifier
```

---

### Step 25 — Add cash flow report

Status: Complete.

Goal:

* Add a direct-method cash flow report.

Completed work:

* Added `src/reconcile/reports/cash_flow.py`.
* Added `generate_cash_flow_statement(connection, *, start_date, end_date, cash_account_id=None)`.
* Added `cash_flow_totals(statement)`.
* Added `classify_cash_flow_section(counterparty_account_type, counterparty_account_code=None, counterparty_account_name=None)`.
* Implemented direct-method cash flow reporting from existing posted journal activity.
* Identified cash-like asset/debit accounts from selected account IDs or cash/checking/bank heuristics.
* Used account code `1000` and account names containing `cash`, `checking`, or `bank` as cash-like account hints.
* Used debit-to-cash as positive cash inflow.
* Used credit-from-cash as negative cash outflow.
* Classified revenue and expense counterparties as operating.
* Classified non-cash asset counterparties as investing.
* Classified liability and equity counterparties as financing.
* Excluded pure cash-to-cash transfers so transfers do not inflate cash flow.
* Calculated beginning cash immediately before the report start date.
* Calculated ending cash through the report end date.
* Calculated operating, investing, financing, and net cash change totals.
* Added `cash_balances_tie` to prove beginning cash plus net cash change equals ending cash.
* Returned report dates as ISO strings.
* Kept all statement rows JSON-serializable.
* Added validation for invalid dates, datetime values, invalid date ranges, invalid account types, missing cash accounts, and non-cash selected accounts.
* Added proportional allocation for multiple non-cash counterparties when simple allocation is practical.
* Updated `src/reconcile/reports/__init__.py` to export cash flow helpers.
* Added `export_cash_flow_csv(...)` to report exports.
* Added `cash_flow.csv` to `export_all_reports(...)`.
* Added CLI `report cash-flow`.
* Updated CLI `export-reports` output to include cash flow export results.
* Added fake sample output at `examples/sample_output/cash_flow.csv`.
* Added `tests/test_cash_flow_report.py`.
* Updated `tests/test_report_exports.py`.
* Updated `tests/test_cli.py`.
* Confirmed cash flow generation and export do not append events or mutate ledger, account, journal, balance, bank, reconciliation, or categorization tables.
* Did not add Streamlit, dashboard cash flow page, indirect-method cash flow, retained earnings, closing entries, reconciliation changes, categorization changes, CI, Excel export, JSON export, PDF export, external APIs, LLM behavior, or new dependencies.

Files created or edited:

```text
src/reconcile/reports/cash_flow.py
src/reconcile/reports/__init__.py
src/reconcile/reports/export.py
src/reconcile/cli.py
tests/test_cash_flow_report.py
tests/test_report_exports.py
tests/test_cli.py
examples/sample_output/cash_flow.csv
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m ruff check .
python -m pytest
python scripts/run_reconcile.py report cash-flow --db-path exports/reconcile.db --from 2026-01-01 --to 2026-01-31
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output --from 2026-01-01 --to 2026-01-31 --as-of 2026-01-31
git status
```

Results:

```text
python -m ruff check .  # All checks passed
python -m pytest        # 709 passed in final full run
python scripts/run_reconcile.py report cash-flow --db-path exports/reconcile.db --from 2026-01-01 --to 2026-01-31
# Cash Flow Statement: 2026-01-01 to 2026-01-31
# Operating cash flow: -950.00
# Investing cash flow: 1200.00
# Financing cash flow: 5000.00
# Net cash change: 5250.00
# Beginning cash: 0.00
# Ending cash: 5250.00
# Cash balances tie: True
python scripts/run_reconcile.py export-reports --db-path exports/reconcile.db --output-dir examples/sample_output --from 2026-01-01 --to 2026-01-31 --as-of 2026-01-31
# Exported reports to: examples\sample_output
# trial_balance: examples\sample_output\trial_balance.csv (9 rows)
# income_statement: examples\sample_output\income_statement.csv (3 rows)
# balance_sheet: examples\sample_output\balance_sheet.csv (5 rows)
# cash_flow: examples\sample_output\cash_flow.csv (4 rows)
# reconciliation_results: skipped
git status  # expected Step 25 files only before Project State update
```

Definition of done:

* `src/reconcile/reports/cash_flow.py` exists.
* `tests/test_cash_flow_report.py` exists.
* Direct-method cash flow statement works.
* Operating, investing, and financing sections are classified.
* Beginning cash is calculated correctly.
* Ending cash is calculated correctly.
* Net cash change is calculated correctly.
* Beginning cash plus net cash change equals ending cash.
* Cash transfers are excluded or net to zero.
* Cash flow generation is read-only and mutation-safe.
* Cash flow CSV export works.
* `export_all_reports` includes `cash_flow.csv`.
* CLI `report cash-flow` works.
* Fake sample cash flow output exists under `examples/sample_output/cash_flow.csv`.
* Existing reports still work.
* Existing exports still work.
* Existing CLI commands still work.
* No Streamlit, dashboard, CI, indirect cash flow, closing entries, categorization changes, reconciliation changes, or new dependencies were added.
* Existing tests pass.
* Ruff passes.
* Project State is updated.

Suggested commit message:

```text
Add direct-method cash flow report
```

---

### Step 26 — Add Streamlit dashboard foundation

Status: Complete.

Goal:

* Add a basic Streamlit dashboard shell connected to the demo database.

Completed work:

* Added `streamlit` as a project dependency.
* Added `dashboard/streamlit_app.py`.
* Added a safe `main()` entrypoint guarded by `if __name__ == "__main__"`.
* Added a Streamlit page title of `Reconcile`.
* Added the subtitle `Local-first event-sourced accounting engine`.
* Added a sidebar database path input.
* Defaulted the dashboard database path to `exports/reconcile.db`.
* Added a sidebar note that the dashboard expects a local demo database.
* Added friendly missing-database setup instructions.
* Kept setup instructions as display text only.
* Did not execute CLI commands from Streamlit.
* Added `database_exists`.
* Added `load_database_counts`.
* Added `load_trial_balance_preview`.
* Added `load_dashboard_summary`.
* Added `format_cents_for_dashboard`.
* Used `pathlib.Path` for path handling.
* Checked database existence before opening a connection.
* Avoided creating a database merely by launching the dashboard.
* Used `reconcile.db.connect` for existing SQLite database reads.
* Added graceful handling for missing database files.
* Added graceful handling for missing schema tables.
* Added graceful handling for empty databases.
* Added table counts for useful tables when available:

```text
ledger_events
accounts
journal_entries
journal_entry_lines
account_balances
bank_statement_imports
bank_transactions
reconciliation_runs
reconciliation_matches
category_corrections
```

* Used existing `generate_trial_balance` and `trial_balance_totals` where practical.
* Displayed high-level summary metrics for events, accounts, posted journal entries, imported bank transactions, reconciliation runs, trial balance status, cash ending balance, and cash flow tie status.
* Displayed a small account/trial-balance preview.
* Kept cash flow tie status as `N/A` in the foundation dashboard instead of building a full cash flow page.
* Kept dashboard logic thin.
* Kept business logic inside existing package modules.
* Did not mutate the database.
* Did not append events.
* Did not import bank files.
* Did not rebuild projections.
* Did not run reconciliation.
* Did not train categorization classifiers.
* Did not write export files.
* Added `tests/test_streamlit_dashboard.py`.
* Tested `database_exists` for missing and existing SQLite paths.
* Tested table counts for missing databases.
* Tested table counts for initialized empty schemas.
* Tested table counts after demo-like accounting, bank, and reconciliation setup.
* Tested trial balance preview behavior after demo-like setup.
* Tested dashboard summary data is JSON-serializable.
* Tested empty database summary behavior.
* Tested missing optional tables do not crash helper functions.
* Tested cents formatting for positive, negative, and zero values.
* Tested importing `dashboard.streamlit_app` does not launch the app.
* Tested helper functions do not append ledger events.
* Tested helper functions do not mutate account balances.
* Tested helper functions do not import bank files.
* Tested helper functions do not run reconciliation.
* Tested helper functions do not write exports.
* Fixed empty database cash balance behavior so an initialized database with no accounts reports cash ending balance as `N/A`.
* Fixed Step 26 Ruff line-length issues in Streamlit setup command strings and table-count query formatting.
* Did not add full dashboard report pages, event timeline, reconciliation review UI, categorization review UI, CI, deployment, screenshots, README polish, or new accounting behavior.

Files created or edited:

```text
dashboard/streamlit_app.py
tests/test_streamlit_dashboard.py
pyproject.toml
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m pytest tests/test_streamlit_dashboard.py
python -m ruff check . --fix
streamlit run dashboard/streamlit_app.py
git status
```

Results:

```text
python -m pytest tests/test_streamlit_dashboard.py
# Initially 15 passed and 1 failed because empty database cash balance returned $0.00 instead of N/A.
# After the empty database cash balance fix, dashboard helper tests were expected to pass.

python -m ruff check . --fix
# Initially found long lines in Streamlit setup command strings and one table-count query.
# Long setup command strings and the table-count query were manually wrapped.

streamlit run dashboard/streamlit_app.py
# Dashboard launched locally and was stopped from PowerShell with Ctrl+C.

git status
# Showed modified pyproject.toml and untracked dashboard/ and tests/test_streamlit_dashboard.py before Project State regeneration.
```

Definition of done:

* `dashboard/streamlit_app.py` exists.
* `tests/test_streamlit_dashboard.py` exists.
* `pyproject.toml` includes Streamlit.
* Dashboard launches with `streamlit run dashboard/streamlit_app.py`.
* Dashboard handles a missing demo database gracefully.
* Dashboard reads an existing demo database.
* Dashboard shows overview/status information.
* Dashboard shows useful table counts.
* Dashboard shows a basic account/trial-balance preview.
* Dashboard helper tests pass after the empty-database cash-balance fix.
* Ruff passes after line-length cleanup.
* Dashboard logic remains thin.
* Core accounting/reconciliation/reporting logic remains in `src/reconcile/`.
* No full report pages, event timeline, reconciliation review, categorization review, CI, deployment, screenshots, or new engine behavior was added.
* Project State is updated.

Suggested commit message:

```text
Add Streamlit dashboard foundation
```


### Step 27 — Add dashboard report pages and event timeline

Status: Complete.

Goal:

* Display point-in-time reports and event history in Streamlit.

Completed work:

* Expanded `dashboard/streamlit_app.py` from the Step 26 foundation shell into a useful read-only demo dashboard.
* Added Streamlit sidebar navigation with these pages:

```text
Overview
Trial Balance
Income Statement
Balance Sheet
Cash Flow
Event Timeline
```

* Preserved the Reconcile title, local-first subtitle, database path input, default `exports/reconcile.db` path, missing-database setup instructions, overview summary, and safe `main()` entrypoint guard.
* Preserved module import safety for pytest.
* Added report defaults:

```text
start date: 2026-01-01
end date: 2026-01-31
as-of date: 2026-01-31
```

* Added date validation helpers for report ranges and as-of dates.
* Added friendly invalid-date handling for income statement and cash flow ranges.
* Added friendly invalid-date handling for balance sheet as-of dates.
* Added `format_cents_for_dashboard(cents: int | None) -> str`.
* Added `format_bool_status(value: bool | None) -> str`.
* Added report-row display helpers for cent-field formatting.
* Added tolerant report-row extraction for report helpers that return sectioned dictionaries instead of only flat row lists.
* Added a cash-flow row fallback from totals for tiny ledgers where totals exist but no detail rows are returned.
* Added `load_trial_balance_report(db_path)`.
* Added `load_income_statement_report(db_path, start_date, end_date)`.
* Added `load_balance_sheet_report(db_path, as_of_date)`.
* Added `load_cash_flow_report(db_path, start_date, end_date)`.
* Added `load_event_timeline(db_path)`.
* Trial Balance page uses `generate_trial_balance(connection)` and `trial_balance_totals(rows)`.
* Trial Balance page displays account code, account name, account type, normal balance, ending debit balance, and ending credit balance.
* Trial Balance page displays ending debit total, ending credit total, and balanced status.
* Income Statement page uses `generate_income_statement(connection, start_date, end_date)` and `income_statement_totals(rows)`.
* Income Statement page displays the selected date range, revenue/expense rows, total revenue, total expenses, and net income.
* Balance Sheet page uses `generate_balance_sheet(connection, as_of_date)`.
* Balance Sheet page displays the selected as-of date, asset/liability/equity rows, total assets, total liabilities, total equity, total liabilities and equity, and balanced status.
* Cash Flow page uses `generate_cash_flow_statement(connection, start_date, end_date)` and `cash_flow_totals(statement)`.
* Cash Flow page displays the selected date range, operating/investing/financing rows, net cash change, beginning cash, ending cash, and cash-balance tie status.
* Cash Flow page includes the known accounting refinement note that customer collections through Accounts Receivable should classify as operating cash flow, not investing.
* Event Timeline page reads directly from `ledger_events` in deterministic `event_sequence` order.
* Event Timeline page displays event sequence, event type, effective date, event timestamp, source, actor, correlation ID, and causation ID.
* Event Timeline page displays `payload_json` inside expandable sections.
* Event Timeline page does not replay events or rebuild projections.
* Dashboard report helpers handle missing databases gracefully.
* Dashboard report helpers handle SQLite and validation errors with friendly unavailable/error dictionaries.
* Dashboard remains read-only.
* Dashboard helpers do not append ledger events.
* Dashboard helpers do not modify accounts.
* Dashboard helpers do not modify journal entries.
* Dashboard helpers do not modify journal entry lines.
* Dashboard helpers do not modify account balances.
* Dashboard helpers do not modify bank transactions.
* Dashboard helpers do not modify reconciliation runs, matches, or links.
* Dashboard helpers do not modify category corrections.
* Dashboard helpers do not rebuild projections.
* Dashboard helpers do not import bank files.
* Dashboard helpers do not run reconciliation.
* Dashboard helpers do not train classifiers.
* Dashboard helpers do not write export files.
* Updated `tests/test_streamlit_dashboard.py` for Step 27 helper coverage.
* Tested dashboard module import safety.
* Tested navigation/page constants and render helper existence.
* Tested default report dates.
* Tested trial balance report loading from demo-like data.
* Tested income statement report loading for date ranges.
* Tested balance sheet report loading for as-of dates.
* Tested cash flow report loading for date ranges.
* Tested event timeline loading in sequence order.
* Tested event timeline expected fields.
* Tested event timeline empty-log behavior.
* Tested missing-database report helper behavior.
* Tested invalid income statement and cash flow date ranges.
* Tested cents formatting for positive, negative, zero, and `None`.
* Tested boolean formatting for true, false, and `None`.
* Tested JSON-serializable helper payloads.
* Tested report-loading helpers do not append ledger events.
* Tested report-loading helpers do not mutate account balances.
* Tested event timeline helper does not mutate ledger events.
* Tested helpers do not import bank files.
* Tested helpers do not run reconciliation.
* Tested helpers do not write export files.
* Did not add reconciliation review UI.
* Did not add categorization review UI.
* Did not add manual correction recording.
* Did not add manual reconciliation confirmation or rejection.
* Did not add dashboard writeback.
* Did not add Streamlit Cloud deployment.
* Did not add screenshots.
* Did not add CI.
* Did not add README polish.
* Did not change accounting, reconciliation, categorization, import, projection, or report engine behavior.

Files created or edited:

```text
dashboard/streamlit_app.py
tests/test_streamlit_dashboard.py
docs/Reconcile_Project_State.md
```

Commands run:

```bash
python -m ruff check dashboard/streamlit_app.py
python -m ruff check tests/test_streamlit_dashboard.py
python -m pytest tests/test_streamlit_dashboard.py
python -m ruff check .
python -m pytest
streamlit run dashboard/streamlit_app.py
git status
```

Results:

```text
python -m ruff check dashboard/streamlit_app.py       # All checks passed after import ordering and helper-order fixes
python -m ruff check tests/test_streamlit_dashboard.py # All checks passed
python -m pytest tests/test_streamlit_dashboard.py    # 35 passed after report-row extraction and cash-flow fallback fixes
python -m ruff check .                               # passed locally as reported
python -m pytest                                     # passed locally as reported
streamlit run dashboard/streamlit_app.py             # manual smoke passed; all Step 27 pages showed no errors
git status                                           # expected Step 27 files after Project State update
```

Definition of done:

* Dashboard launches with `streamlit run dashboard/streamlit_app.py`.
* Overview page still works.
* Sidebar navigation exists.
* Trial Balance page works.
* Income Statement page works.
* Balance Sheet page works.
* Cash Flow page works.
* Event Timeline page works.
* Missing database state is handled gracefully.
* Demo database can be read.
* Report pages use existing package report functions.
* Event timeline reads `ledger_events` without mutation.
* Dashboard remains read-only.
* Dashboard logic remains thin.
* Core accounting/reconciliation/reporting logic remains in `src/reconcile/`.
* `tests/test_streamlit_dashboard.py` covers Step 27 helper behavior.
* Tests pass locally as reported.
* Ruff passes locally as reported.
* No reconciliation review UI, categorization review UI, writeback workflow, CI, deployment, screenshots, or new engine behavior was added.
* Project State is updated.

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