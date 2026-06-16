# Reconcile Event Model

This document defines the planned MVP event model. Step 0 does not implement these events yet.

## Event store role

The event store will be the source of truth. Projections and reports will be derived from events. Events should be loaded and replayed in deterministic `event_sequence` order.

## Common event fields

Every event is planned to include:

| Field | Purpose |
| --- | --- |
| `event_sequence` | Database-assigned ordering value. |
| `event_id` | Stable unique event identifier. |
| `event_type` | Event name, such as `JournalEntryPosted`. |
| `event_version` | Version number for payload compatibility. |
| `event_timestamp` | When the event was recorded. |
| `effective_date` | Accounting or business date of the event. |
| `source` | Source such as demo, manual, import, or reversal. |
| `actor` | Optional user/system actor. |
| `correlation_id` | Optional workflow grouping ID. |
| `causation_id` | Optional prior event that caused this event. |
| `payload_json` | JSON payload for replaying the event. |
| `created_at` | Storage timestamp. |

## Planned MVP event types

### AccountOpened

Records that an account was opened.

Expected payload fields:

- `account_id`
- `code`
- `name`
- `account_type`
- `normal_balance`
- `parent_account_code`, optional
- `description`, optional
- `is_active`

Replay expectation:

- Create or restore the account projection as active.
- Reject duplicate account codes before event append in service logic.

### AccountClosed

Records that an account was closed or marked inactive.

Expected payload fields:

- `account_id`
- `code`
- `closed_at`
- `reason`, optional

Replay expectation:

- Mark the account projection inactive.
- Preserve the account history.

### JournalEntryPosted

Records that a balanced journal entry was posted.

Expected payload fields:

- `journal_entry_id`
- `entry_date`
- `description`
- `source`
- `external_reference`, optional
- `lines`, each containing:
  - `line_id`
  - `line_number`
  - `account_id` or account code resolved before projection
  - `side`
  - `amount_cents`
  - `description`, optional

Replay expectation:

- Create journal entry and line projections.
- Apply debits and credits to account-balance projections.
- Preserve the original entry.

### JournalEntryReversed

Records that a posted journal entry was reversed.

Expected payload fields:

- `original_journal_entry_id`
- `reversal_journal_entry_id`
- `reversal_date`
- `reason`
- `reversal_lines`

Replay expectation:

- Create reversal journal entry projection.
- Mark original entry as reversed if the projection supports that status.
- Apply reversing lines to balance projections.
- Keep the original entry visible.

### BankStatementImported

Records that a bank statement file was imported.

Expected payload fields:

- `import_id`
- `source_name`
- `file_name`
- `file_hash`, optional
- `row_count`
- `transactions`, each containing:
  - `bank_transaction_id`
  - `transaction_date`
  - `posted_date`, optional
  - `description_raw`
  - `description_normalized`, optional
  - `amount_cents`
  - `external_id`, optional
  - `check_number`, optional
  - `row_hash`
  - `duplicate_group_id`, optional

Replay expectation:

- Store import metadata.
- Store imported bank transactions.
- Preserve raw descriptions.
- Flag duplicates instead of deleting them.

### ReconciliationRunCompleted

Records that a reconciliation run was completed.

Expected payload fields:

- `reconciliation_run_id`
- `cash_account_id`
- `statement_start_date`
- `statement_end_date`
- `started_at`
- `completed_at`
- `config`
- `summary`

Replay expectation:

- Store reconciliation run metadata.
- Preserve configuration used for matching.

### ReconciliationMatchConfirmed

Records that a reconciliation match was confirmed.

Expected payload fields:

- `reconciliation_match_id`
- `reconciliation_run_id`
- `bank_transaction_id`
- `ledger_movement_ids`
- `match_type`
- `score`
- `amount_delta_cents`
- `date_delta_days`, optional
- `explanation`
- `confirmed_by`, optional

Replay expectation:

- Store or update match status as confirmed.
- Link the bank transaction to the selected ledger cash movement or movements.
- Do not reuse confirmed ledger movements in the same run.

### ReconciliationMatchRejected

Records that a reconciliation candidate was rejected.

Expected payload fields:

- `reconciliation_match_id`
- `reconciliation_run_id`
- `bank_transaction_id`
- `ledger_movement_ids`
- `reason`
- `rejected_by`, optional

Replay expectation:

- Mark the candidate as rejected.
- Preserve the reason.

## Event ordering

Events will be replayed by `event_sequence`, not by timestamp alone. Timestamps can collide or arrive out of order. The sequence number is the deterministic replay order.

## Payload expectations

Event payloads should be JSON-compatible and contain enough information to rebuild projections. Payloads should avoid derived values unless those values are needed for audit or explanation.

Money values in payloads should use integer cents.

## Replay expectations

Replay should be deterministic. Given the same event list in the same order, projections should rebuild to the same state.

Invalid business actions should be rejected before an event is appended. For example, an unbalanced journal entry should not create a `JournalEntryPosted` event.

## Versioning expectations

MVP events will use `event_version = 1`. If a payload shape changes later, the version should increase and replay code should handle old versions intentionally.
