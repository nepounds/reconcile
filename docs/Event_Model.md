# Reconcile Event Model

This document describes the event model currently implemented in Reconcile and
separates it from MVP workflow tables that are not event-sourced yet.

## Event store role

The `ledger_events` table is the source of truth for implemented ledger actions.
Projection tables can be rebuilt by loading events in deterministic
`event_sequence` order and applying each event to the read models.

Events are append-only. Posted accounting history is not edited or deleted.
Corrections use reversal events.

## `ledger_events`

Each stored event has these fields:

| Field | Purpose |
| --- | --- |
| `event_sequence` | SQLite-assigned replay order. |
| `event_id` | Stable unique event identifier. |
| `event_type` | Event name, such as `JournalEntryPosted`. |
| `event_version` | Payload version. MVP events use version 1. |
| `event_timestamp` | When the event was recorded. |
| `effective_date` | Accounting or business date. |
| `source` | Source such as demo, manual, import, or reversal. |
| `actor` | Optional actor. |
| `correlation_id` | Optional workflow grouping ID. |
| `causation_id` | Optional prior event that caused this one. |
| `payload_json` | JSON payload used for replay. |
| `created_at` | Storage timestamp. |

## Event ordering

Events replay by `event_sequence`, not timestamp. Timestamps can collide or be
created out of order. The sequence number is the deterministic replay order.

## Payload JSON

Event payloads are JSON-compatible dictionaries. Money values use integer cents.
Payloads contain enough data to rebuild the implemented accounting projections.

Invalid business actions are rejected before an event is appended. For example,
an unbalanced journal entry does not create a `JournalEntryPosted` event.

## Implemented event types

### AccountOpened

Records that an account was opened.

Payload includes account identity, code, name, account type, normal balance,
active status, open timestamp, and optional close timestamp.

Replay behavior:

- inserts or restores the account projection
- preserves account identity and normal-balance rules
- rejects duplicate projection rows during application

### JournalEntryPosted

Records that a balanced double-entry journal entry was posted.

Payload includes the journal entry header and all journal lines, including line
IDs, account IDs, debit/credit side, amount cents, descriptions, and line order.

Replay behavior:

- inserts the journal entry projection
- inserts journal line projections
- applies debit and credit activity to account-balance projections

### JournalEntryReversed

Records that a posted journal entry was reversed.

Payload includes the original journal entry ID, the reversal journal entry ID,
the reversal date, reason, and reversing lines.

Replay behavior:

- inserts the reversal journal entry projection
- inserts reversal journal lines
- marks the original entry with `reversed_by_entry_id`
- marks the reversal entry with `reversal_of_entry_id`
- applies the reversing debit/credit activity to account balances

Reversals preserve audit history. The original entry remains visible, and the
reversal is a separate journal entry with opposite sides.

## MVP table-backed workflows

Some implemented MVP features are stored in regular SQLite workflow tables
instead of ledger events.

### Bank imports

Bank imports currently write to:

- `bank_statement_imports`
- `bank_transactions`

They are not event-sourced in the current implementation. Raw bank descriptions,
normalized descriptions, signed integer amounts, row hashes, and duplicate flags
are preserved in those tables.

### Reconciliation

Reconciliation currently writes to:

- `reconciliation_runs`
- `reconciliation_matches`
- `reconciliation_match_ledger_links`

Reconciliation runs and match decisions are table-backed in the MVP. They do not
append ledger events and do not mutate ledger history.

### Categorization corrections

Categorization corrections currently write to:

- `category_corrections`

Corrections are append-only rows, but they are not `ledger_events` in the MVP.
They affect categorization review, not financial ledger state.

## Planned or future event types

These event types are not implemented as ledger events yet:

- `AccountClosed`
- `BankStatementImported`
- `ReconciliationRunCompleted`
- `ReconciliationMatchConfirmed`
- `ReconciliationMatchRejected`
- `CategorizationRuleCreated`
- `CategorizationRuleUpdated`
- `TransactionCategoryCorrected`
- `ClassifierTrained`
- `ReportSnapshotCreated`

They are listed as future design possibilities, not current behavior.

## Versioning

Current event payloads use `event_version = 1`. If a payload shape changes later,
the version should increase and replay code should handle old versions
intentionally.
