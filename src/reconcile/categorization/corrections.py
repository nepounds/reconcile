"""Correction storage for bank transaction categorization."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime

from reconcile.exceptions import ValidationError


def _utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _validate_nonblank_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} must be a nonblank string")
    return value.strip()


def _validate_optional_nonblank(value: object | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _validate_nonblank_string(value, field_name)


def _validate_iso_like(value: object | None, field_name: str) -> str | None:
    if value is None:
        return None
    text = _validate_nonblank_string(value, field_name)
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field_name} must be an ISO-like timestamp") from exc
    return text


def _bank_transaction_exists(
        connection: sqlite3.Connection,
        bank_transaction_id: str,
        ) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM bank_transactions
        WHERE bank_transaction_id = ?
        """,
        (bank_transaction_id,),
    ).fetchone()
    return row is not None


def _row_to_dict(row: sqlite3.Row) -> dict[str, object]:
    return {
        "correction_id": row["correction_id"],
        "bank_transaction_id": row["bank_transaction_id"],
        "corrected_category": row["corrected_category"],
        "corrected_by": row["corrected_by"],
        "reason": row["reason"],
        "corrected_at": row["corrected_at"],
        "created_at": row["created_at"],
    }


def initialize_categorization_schema(connection: sqlite3.Connection) -> None:
    """Create categorization correction tables if they do not already exist."""
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS category_corrections (
            correction_id TEXT PRIMARY KEY,
            bank_transaction_id TEXT NOT NULL,
            corrected_category TEXT NOT NULL,
            corrected_by TEXT,
            reason TEXT,
            corrected_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(bank_transaction_id)
                REFERENCES bank_transactions(bank_transaction_id)
        )
        """
    )
    connection.commit()


def record_category_correction(
    connection: sqlite3.Connection,
    *,
    bank_transaction_id: str,
    corrected_category: str,
    corrected_by: str | None = None,
    reason: str | None = None,
    corrected_at: str | None = None,
) -> dict[str, object]:
    """Append one category correction for an existing bank transaction."""
    bank_transaction_id = _validate_nonblank_string(
        bank_transaction_id, "bank_transaction_id"
    )
    corrected_category = _validate_nonblank_string(
        corrected_category, "corrected_category"
    )
    corrected_by = _validate_optional_nonblank(corrected_by, "corrected_by")
    reason = _validate_optional_nonblank(reason, "reason")
    corrected_at = _validate_iso_like(corrected_at, "corrected_at") or _utc_timestamp()
    created_at = _utc_timestamp()

    if not _bank_transaction_exists(connection, bank_transaction_id):
        raise ValidationError(
            "bank_transaction_id must reference an existing bank transaction"
        )

    correction_id = f"category-correction-{uuid.uuid4()}"
    connection.execute(
        """
        INSERT INTO category_corrections (
            correction_id,
            bank_transaction_id,
            corrected_category,
            corrected_by,
            reason,
            corrected_at,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            correction_id,
            bank_transaction_id,
            corrected_category,
            corrected_by,
            reason,
            corrected_at,
            created_at,
        ),
    )
    connection.commit()

    return {
        "correction_id": correction_id,
        "bank_transaction_id": bank_transaction_id,
        "corrected_category": corrected_category,
        "corrected_by": corrected_by,
        "reason": reason,
        "corrected_at": corrected_at,
        "created_at": created_at,
    }


def list_category_corrections(
    connection: sqlite3.Connection,
    *,
    bank_transaction_id: str | None = None,
) -> list[dict[str, object]]:
    """List category corrections in deterministic order."""
    params: tuple[str, ...] = ()
    where_sql = ""
    if bank_transaction_id is not None:
        bank_transaction_id = _validate_nonblank_string(
            bank_transaction_id, "bank_transaction_id"
        )
        where_sql = "WHERE bank_transaction_id = ?"
        params = (bank_transaction_id,)

    rows = connection.execute(
        f"""
        SELECT
            correction_id,
            bank_transaction_id,
            corrected_category,
            corrected_by,
            reason,
            corrected_at,
            created_at
        FROM category_corrections
        {where_sql}
        ORDER BY corrected_at, created_at, correction_id
        """,
        params,
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def latest_category_correction(
    connection: sqlite3.Connection,
    bank_transaction_id: str,
) -> dict[str, object] | None:
    """Return the newest correction for one bank transaction, if present."""
    bank_transaction_id = _validate_nonblank_string(
        bank_transaction_id, "bank_transaction_id"
    )
    row = connection.execute(
        """
        SELECT
            correction_id,
            bank_transaction_id,
            corrected_category,
            corrected_by,
            reason,
            corrected_at,
            created_at
        FROM category_corrections
        WHERE bank_transaction_id = ?
        ORDER BY corrected_at DESC, created_at DESC, correction_id DESC
        LIMIT 1
        """,
        (bank_transaction_id,),
    ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def training_examples_from_corrections(
    connection: sqlite3.Connection,
) -> list[dict[str, object]]:
    """Build classifier training examples from correction rows and bank rows."""
    rows = connection.execute(
        """
        SELECT
            c.correction_id,
            c.bank_transaction_id,
            c.corrected_category,
            c.corrected_at,
            c.created_at,
            b.description_raw,
            b.description_normalized,
            b.amount_cents
        FROM category_corrections AS c
        JOIN bank_transactions AS b
            ON b.bank_transaction_id = c.bank_transaction_id
        ORDER BY c.corrected_at, c.created_at, c.correction_id
        """
    ).fetchall()

    examples: list[dict[str, object]] = []
    for row in rows:
        description_normalized = row["description_normalized"]
        description_raw = row["description_raw"]
        text = description_normalized or description_raw
        examples.append(
            {
                "correction_id": row["correction_id"],
                "bank_transaction_id": row["bank_transaction_id"],
                "text": text,
                "description_raw": description_raw,
                "description_normalized": description_normalized,
                "amount_cents": row["amount_cents"],
                "category": row["corrected_category"],
                "corrected_at": row["corrected_at"],
            }
        )
    return examples


def _latest_corrections_by_bank_transaction(
    corrections: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    latest: dict[str, dict[str, object]] = {}
    sorted_corrections = sorted(
        (dict(correction) for correction in corrections),
        key=lambda item: (
            str(item.get("corrected_at") or ""),
            str(item.get("created_at") or ""),
            str(item.get("correction_id") or ""),
        ),
    )
    for correction in sorted_corrections:
        bank_transaction_id = correction.get("bank_transaction_id")
        if isinstance(bank_transaction_id, str) and bank_transaction_id.strip():
            latest[bank_transaction_id] = correction
    return latest


def apply_corrections_to_categorized_results(
    categorized_results: list[dict[str, object]],
    corrections: list[dict[str, object]],
) -> list[dict[str, object]]:
    """Apply latest user corrections to categorized result dictionaries."""
    latest = _latest_corrections_by_bank_transaction(corrections)
    output: list[dict[str, object]] = []

    for result in categorized_results:
        copied = dict(result)
        bank_transaction_id = copied.get("bank_transaction_id")
        correction = (
            latest.get(bank_transaction_id) 
            if isinstance(bank_transaction_id, str) 
            else None
        )
        if correction is not None:
            reason = correction.get("reason")
            reason_text = f"Corrected to {correction['corrected_category']}"
            if reason:
                reason_text = f"{reason_text}: {reason}"
            copied.update(
                {
                    "category": correction["corrected_category"],
                    "category_source": "correction",
                    "category_rule_id": None,
                    "category_reason": reason_text,
                    "correction_id": correction["correction_id"],
                    "corrected_at": correction["corrected_at"],
                }
            )
        output.append(copied)

    return output
