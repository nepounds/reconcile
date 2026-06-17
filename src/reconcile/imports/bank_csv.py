"""Bank statement CSV import helpers."""

from __future__ import annotations

import csv
import hashlib
import sqlite3
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

from reconcile.exceptions import ValidationError
from reconcile.imports.duplicate_detection import mark_duplicate_bank_transactions
from reconcile.imports.normalization import normalize_bank_description
from reconcile.money import parse_money_to_cents

REQUIRED_COLUMNS = frozenset({"transaction_date", "description", "amount"})
OPTIONAL_COLUMNS = frozenset({"posted_date", "external_id", "check_number"})
HASH_FIELDS = (
    "transaction_date",
    "posted_date",
    "description",
    "amount",
    "external_id",
    "check_number",
)


def read_bank_statement_csv(csv_path: str | Path) -> list[dict[str, str]]:
    """Read and validate a bank statement CSV file."""
    path = Path(csv_path)

    if not path.exists():
        raise ValidationError(f"bank statement CSV does not exist: {path}")

    try:
        with path.open(newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames is None:
                raise ValidationError("bank statement CSV is empty")

            missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise ValidationError(f"bank statement CSV missing columns: {missing}")

            rows = list(reader)
    except OSError as exc:
        raise ValidationError(f"could not read bank statement CSV: {path}") from exc

    if not rows:
        raise ValidationError("bank statement CSV has headers but no data rows")

    for row_number, row in enumerate(rows, start=2):
        _validate_bank_row(row, row_number)

    return rows


def hash_bank_row(row: dict[str, str]) -> str:
    """Return a deterministic SHA-256 hash for stable bank row fields."""
    parts = []
    for field in HASH_FIELDS:
        value = row.get(field)
        parts.append("" if value is None else str(value).strip())

    joined = "\x1f".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def import_bank_statement_csv(
    connection: sqlite3.Connection,
    csv_path: str | Path,
    *,
    source_name: str = "bank_csv",
    import_id: str | None = None,
) -> str:
    """Import a validated bank statement CSV into SQLite."""
    path = Path(csv_path)
    rows = read_bank_statement_csv(path)
    clean_source_name = _require_nonblank_string(source_name, "source_name")
    clean_import_id = _resolve_import_id(import_id)
    imported_at = _utc_now_iso()
    file_hash = _hash_file(path)

    try:
        with connection:
            _validate_import_id_is_available(connection, clean_import_id)

            connection.execute(
                """
                INSERT INTO bank_statement_imports (
                    import_id,
                    source_name,
                    file_name,
                    file_hash,
                    imported_at,
                    row_count
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    clean_import_id,
                    clean_source_name,
                    path.name,
                    file_hash,
                    imported_at,
                    len(rows),
                ),
            )

            for row in rows:
                transaction_date = _parse_iso_date(
                    row["transaction_date"],
                    "transaction_date",
                )
                posted_date = _optional_iso_date(row.get("posted_date"))
                description_raw = row["description"]
                description_normalized = normalize_bank_description(description_raw)
                amount_cents = parse_money_to_cents(row["amount"])
                external_id = _optional_string(row.get("external_id"))
                check_number = _optional_string(row.get("check_number"))

                connection.execute(
                    """
                    INSERT INTO bank_transactions (
                        bank_transaction_id,
                        import_id,
                        transaction_date,
                        posted_date,
                        description_raw,
                        description_normalized,
                        amount_cents,
                        external_id,
                        check_number,
                        row_hash,
                        duplicate_group_id,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                    """,
                    (
                        _new_bank_transaction_id(),
                        clean_import_id,
                        transaction_date.isoformat(),
                        posted_date.isoformat() if posted_date else None,
                        description_raw,
                        description_normalized,
                        amount_cents,
                        external_id,
                        check_number,
                        hash_bank_row(row),
                        imported_at,
                    ),
                )
    except sqlite3.IntegrityError as exc:
        raise ValidationError("bank statement import could not be saved") from exc

    mark_duplicate_bank_transactions(connection, import_id=clean_import_id)
    return clean_import_id


def _validate_bank_row(row: dict[str, str], row_number: int) -> None:
    _parse_iso_date(row.get("transaction_date", ""), "transaction_date", row_number)

    if _is_blank(row.get("description")):
        raise ValidationError(f"row {row_number}: description cannot be blank")

    if _is_blank(row.get("amount")):
        raise ValidationError(f"row {row_number}: amount cannot be blank")

    try:
        parse_money_to_cents(row["amount"])
    except ValidationError as exc:
        raise ValidationError(f"row {row_number}: invalid amount") from exc

    posted_date = row.get("posted_date")
    if posted_date is not None and posted_date.strip():
        _parse_iso_date(posted_date, "posted_date", row_number)


def _parse_iso_date(
    value: str | None,
    field_name: str,
    row_number: int | None = None,
) -> date:
    if _is_blank(value):
        prefix = f"row {row_number}: " if row_number is not None else ""
        raise ValidationError(f"{prefix}{field_name} cannot be blank")

    try:
        return date.fromisoformat(str(value).strip())
    except ValueError as exc:
        prefix = f"row {row_number}: " if row_number is not None else ""
        raise ValidationError(f"{prefix}{field_name} must be YYYY-MM-DD") from exc


def _optional_iso_date(value: str | None) -> date | None:
    if _is_blank(value):
        return None

    return _parse_iso_date(value, "posted_date")


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None

    stripped = value.strip()
    return stripped or None


def _is_blank(value: str | None) -> bool:
    return value is None or not str(value).strip()


def _resolve_import_id(import_id: str | None) -> str:
    if import_id is None:
        return f"bank-import-{uuid.uuid4()}"

    return _require_nonblank_string(import_id, "import_id")


def _require_nonblank_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")

    stripped = value.strip()
    if not stripped:
        raise ValidationError(f"{field_name} cannot be blank")

    return stripped


def _validate_import_id_is_available(
    connection: sqlite3.Connection,
    import_id: str,
) -> None:
    row = connection.execute(
        """
        SELECT 1
        FROM bank_statement_imports
        WHERE import_id = ?
        """,
        (import_id,),
    ).fetchone()

    if row is not None:
        raise ValidationError(f"bank statement import already exists: {import_id}")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def _new_bank_transaction_id() -> str:
    return f"bank-txn-{uuid.uuid4()}"


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()