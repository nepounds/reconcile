"""Ledger event data structures and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from reconcile.exceptions import ValidationError

ACCOUNT_OPENED = "AccountOpened"
ACCOUNT_CLOSED = "AccountClosed"
JOURNAL_ENTRY_POSTED = "JournalEntryPosted"
JOURNAL_ENTRY_REVERSED = "JournalEntryReversed"
BANK_STATEMENT_IMPORTED = "BankStatementImported"
RECONCILIATION_RUN_COMPLETED = "ReconciliationRunCompleted"
RECONCILIATION_MATCH_CONFIRMED = "ReconciliationMatchConfirmed"
RECONCILIATION_MATCH_REJECTED = "ReconciliationMatchRejected"

LEDGER_EVENT_TYPES = (
    ACCOUNT_OPENED,
    ACCOUNT_CLOSED,
    JOURNAL_ENTRY_POSTED,
    JOURNAL_ENTRY_REVERSED,
    BANK_STATEMENT_IMPORTED,
    RECONCILIATION_RUN_COMPLETED,
    RECONCILIATION_MATCH_CONFIRMED,
    RECONCILIATION_MATCH_REJECTED,
)


@dataclass(frozen=True)
class LedgerEvent:
    """Append-only ledger event stored in deterministic sequence order."""

    event_id: str
    event_type: str
    event_version: int
    event_timestamp: str
    effective_date: str
    source: str
    payload: dict[str, Any]
    actor: str | None = None
    correlation_id: str | None = None
    causation_id: str | None = None
    created_at: str | None = None
    event_sequence: int | None = None

    def __post_init__(self) -> None:
        _validate_required_string(self.event_id, "event_id")
        _validate_required_string(self.event_type, "event_type")
        _validate_event_type(self.event_type)
        _validate_positive_int(self.event_version, "event_version")
        _validate_required_string(self.event_timestamp, "event_timestamp")
        _validate_required_string(self.effective_date, "effective_date")
        _validate_required_string(self.source, "source")
        _validate_payload(self.payload)

        _validate_optional_string(self.actor, "actor")
        _validate_optional_string(self.correlation_id, "correlation_id")
        _validate_optional_string(self.causation_id, "causation_id")
        _validate_optional_string(self.created_at, "created_at")

        if self.event_sequence is not None:
            _validate_positive_int(self.event_sequence, "event_sequence")


def _validate_required_string(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} cannot be blank")


def _validate_optional_string(value: str | None, field_name: str) -> None:
    if value is None:
        return

    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} cannot be blank if provided")


def _validate_positive_int(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an int")

    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero")


def _validate_payload(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValidationError("payload must be a dict")

    try:
        json.dumps(payload, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise ValidationError("payload must be JSON-serializable") from error


def _validate_event_type(event_type: str) -> None:
    if event_type not in LEDGER_EVENT_TYPES:
        raise ValidationError(f"event_type must be one of: {LEDGER_EVENT_TYPES}")