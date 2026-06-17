"""Duplicate detection for imported bank transactions."""

from __future__ import annotations

import hashlib
import sqlite3
from collections import defaultdict
from typing import Any

from reconcile.exceptions import ValidationError

DuplicateRow = dict[str, str | int | None]

DUPLICATE_FIELDS = (
    "bank_transaction_id",
    "import_id",
    "transaction_date",
    "posted_date",
    "description_raw",
    "description_normalized",
    "amount_cents",
    "external_id",
    "check_number",
    "row_hash",
)


def build_duplicate_group_id(reason: str, key: str) -> str:
    """Build a deterministic duplicate group ID."""
    clean_reason = _clean_reason(reason)
    digest = hashlib.sha256(f"{clean_reason}|{key}".encode("utf-8")).hexdigest()
    return f"dup-{clean_reason}-{digest[:12]}"


def detect_duplicate_bank_transactions(
    connection: sqlite3.Connection,
    *,
    import_id: str | None = None,
) -> list[DuplicateRow]:
    """Detect duplicate bank transactions without mutating the database."""
    clean_import_id = _validate_import_id(import_id)
    rows = _load_bank_transactions(connection, import_id=clean_import_id)
    assignments = _detect_assignments(rows)

    duplicate_rows: list[DuplicateRow] = []
    for row in rows:
        bank_transaction_id = row["bank_transaction_id"]
        assignment = assignments.get(bank_transaction_id)
        if assignment is None:
            continue

        duplicate_group_id, duplicate_reason = assignment
        duplicate_rows.append(
            {
                "bank_transaction_id": row["bank_transaction_id"],
                "import_id": row["import_id"],
                "duplicate_group_id": duplicate_group_id,
                "duplicate_reason": duplicate_reason,
                "transaction_date": row["transaction_date"],
                "posted_date": row["posted_date"],
                "description_raw": row["description_raw"],
                "description_normalized": row["description_normalized"],
                "amount_cents": row["amount_cents"],
                "external_id": row["external_id"],
                "check_number": row["check_number"],
                "row_hash": row["row_hash"],
            }
        )

    return sorted(
        duplicate_rows,
        key=lambda item: (
            str(item["duplicate_group_id"]),
            str(item["transaction_date"]),
            str(item["bank_transaction_id"]),
        ),
    )


def mark_duplicate_bank_transactions(
    connection: sqlite3.Connection,
    *,
    import_id: str | None = None,
) -> list[DuplicateRow]:
    """Mark duplicate bank transactions with deterministic group IDs."""
    clean_import_id = _validate_import_id(import_id)
    _clear_duplicate_group_ids(connection, import_id=clean_import_id)

    duplicate_rows = detect_duplicate_bank_transactions(
        connection,
        import_id=clean_import_id,
    )

    for duplicate_row in duplicate_rows:
        connection.execute(
            """
            UPDATE bank_transactions
            SET duplicate_group_id = ?
            WHERE bank_transaction_id = ?
            """,
            (
                duplicate_row["duplicate_group_id"],
                duplicate_row["bank_transaction_id"],
            ),
        )

    connection.commit()
    return duplicate_rows


def _validate_import_id(import_id: str | None) -> str | None:
    if import_id is None:
        return None

    if not isinstance(import_id, str):
        raise ValidationError("import_id must be a string")

    clean_import_id = import_id.strip()
    if not clean_import_id:
        raise ValidationError("import_id cannot be blank")

    return clean_import_id


def _load_bank_transactions(
    connection: sqlite3.Connection,
    *,
    import_id: str | None,
) -> list[sqlite3.Row]:
    if import_id is None:
        cursor = connection.execute(
            f"""
            SELECT {", ".join(DUPLICATE_FIELDS)}
            FROM bank_transactions
            ORDER BY import_id, transaction_date, bank_transaction_id
            """
        )
        return list(cursor.fetchall())

    cursor = connection.execute(
        f"""
        SELECT {", ".join(DUPLICATE_FIELDS)}
        FROM bank_transactions
        WHERE import_id = ?
        ORDER BY import_id, transaction_date, bank_transaction_id
        """,
        (import_id,),
    )
    return list(cursor.fetchall())


def _detect_assignments(
    rows: list[sqlite3.Row],
) -> dict[str, tuple[str, str]]:
    assignments: dict[str, tuple[str, str]] = {}

    _assign_duplicate_groups(
        rows=rows,
        assignments=assignments,
        reason="row_hash",
        key_builder=lambda row: str(row["row_hash"]),
        include_row=lambda row: bool(str(row["row_hash"]).strip()),
    )
    _assign_duplicate_groups(
        rows=rows,
        assignments=assignments,
        reason="external_id",
        key_builder=lambda row: str(row["external_id"]).strip(),
        include_row=lambda row: _has_nonblank_value(row["external_id"]),
    )
    _assign_duplicate_groups(
        rows=rows,
        assignments=assignments,
        reason="fingerprint",
        key_builder=_fingerprint_key,
        include_row=lambda row: True,
    )

    return assignments


def _assign_duplicate_groups(
    *,
    rows: list[sqlite3.Row],
    assignments: dict[str, tuple[str, str]],
    reason: str,
    key_builder: Any,
    include_row: Any,
) -> None:
    groups: dict[str, list[sqlite3.Row]] = defaultdict(list)

    for row in rows:
        bank_transaction_id = row["bank_transaction_id"]
        if bank_transaction_id in assignments:
            continue
        if not include_row(row):
            continue

        key = key_builder(row)
        groups[key].append(row)

    for key, group_rows in groups.items():
        if len(group_rows) < 2:
            continue

        duplicate_group_id = build_duplicate_group_id(reason, key)
        for row in group_rows:
            assignments[row["bank_transaction_id"]] = (
                duplicate_group_id,
                reason,
            )


def _fingerprint_key(row: sqlite3.Row) -> str:
    return "|".join(
        (
            str(row["transaction_date"]),
            str(row["amount_cents"]),
            str(row["description_normalized"]),
        )
    )


def _has_nonblank_value(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _clean_reason(reason: str) -> str:
    clean_reason = reason.strip().replace("_", "-")
    if not clean_reason:
        raise ValidationError("duplicate reason cannot be blank")
    return clean_reason


def _clear_duplicate_group_ids(
    connection: sqlite3.Connection,
    *,
    import_id: str | None,
) -> None:
    if import_id is None:
        connection.execute(
            """
            UPDATE bank_transactions
            SET duplicate_group_id = NULL
            """
        )
        return

    connection.execute(
        """
        UPDATE bank_transactions
        SET duplicate_group_id = NULL
        WHERE import_id = ?
        """,
        (import_id,),
    )