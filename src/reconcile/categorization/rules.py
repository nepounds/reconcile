"""Deterministic rule-based categorization for bank transactions."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Any

from reconcile.exceptions import ValidationError

_AMOUNT_SIGNS = {"positive", "negative", "any"}
_WORD_RE = re.compile(r"[^a-z0-9]+")


def normalize_rule_text(value: str | None) -> str:
    """Normalize rule and transaction text for deterministic matching."""
    if value is None:
        return ""
    text = str(value).casefold()
    text = _WORD_RE.sub(" ", text)
    return " ".join(text.split())


def _validate_nonblank_string(value: object, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")
    stripped = value.strip()
    if not stripped:
        raise ValidationError(f"{field_name} cannot be blank.")
    return stripped


def _validate_optional_string(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _validate_nonblank_string(value, field_name)


def _validate_token_tuple(value: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise ValidationError(f"{field_name} must be a tuple of strings.")
    normalized: list[str] = []
    for token in value:
        _validate_nonblank_string(token, field_name)
        normalized_token = normalize_rule_text(token)
        if not normalized_token:
            raise ValidationError(f"{field_name} cannot contain blank tokens.")
        normalized.append(normalized_token)
    return tuple(normalized)


def _validate_optional_int(value: int | None, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field_name} must be an integer number of cents.")
    return value


@dataclass(frozen=True)
class CategoryRule:
    """A deterministic category rule for imported bank transactions."""

    rule_id: str
    category: str
    priority: int
    description_contains: str | None = None
    description_tokens_any: tuple[str, ...] = ()
    description_tokens_all: tuple[str, ...] = ()
    amount_min_cents: int | None = None
    amount_max_cents: int | None = None
    amount_sign: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        rule_id = _validate_nonblank_string(self.rule_id, "rule_id")
        category = _validate_nonblank_string(self.category, "category")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise ValidationError("priority must be an integer.")

        description_contains = _validate_optional_string(
            self.description_contains,
            "description_contains",
        )
        reason = _validate_optional_string(self.reason, "reason")
        amount_min_cents = _validate_optional_int(
            self.amount_min_cents,
            "amount_min_cents",
        )
        amount_max_cents = _validate_optional_int(
            self.amount_max_cents,
            "amount_max_cents",
        )
        if (
            amount_min_cents is not None
            and amount_max_cents is not None
            and amount_min_cents > amount_max_cents
        ):
            raise ValidationError(
                "amount_min_cents cannot be greater than amount_max_cents."
            )
        if self.amount_sign not in (*_AMOUNT_SIGNS, None):
            raise ValidationError(
                "amount_sign must be 'positive', 'negative', 'any', or None."
            )

        object.__setattr__(self, "rule_id", rule_id)
        object.__setattr__(self, "category", category)
        object.__setattr__(
            self,
            "description_contains",
            normalize_rule_text(description_contains),
        )
        object.__setattr__(
            self,
            "description_tokens_any",
            _validate_token_tuple(
                self.description_tokens_any,
                "description_tokens_any",
            ),
        )
        object.__setattr__(
            self,
            "description_tokens_all",
            _validate_token_tuple(
                self.description_tokens_all,
                "description_tokens_all",
            ),
        )
        object.__setattr__(self, "amount_min_cents", amount_min_cents)
        object.__setattr__(self, "amount_max_cents", amount_max_cents)
        object.__setattr__(self, "reason", reason)


def _transaction_identity(transaction: dict[str, object]) -> str:
    bank_transaction_id = transaction.get("bank_transaction_id")
    if not isinstance(bank_transaction_id, str) or not bank_transaction_id.strip():
        raise ValidationError("bank_transaction_id must be a nonblank string.")
    return bank_transaction_id.strip()


def _transaction_amount(transaction: dict[str, object]) -> int:
    if "amount_cents" not in transaction:
        raise ValidationError("amount_cents is required.")
    amount_cents = transaction["amount_cents"]
    if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
        raise ValidationError("amount_cents must be an integer number of cents.")
    return amount_cents


def _transaction_description(transaction: dict[str, object]) -> str:
    normalized = transaction.get("description_normalized")
    raw = transaction.get("description_raw")
    if isinstance(normalized, str) and normalized.strip():
        return normalize_rule_text(normalized)
    if isinstance(raw, str) and raw.strip():
        return normalize_rule_text(raw)
    return ""


def _description_tokens(description: str) -> set[str]:
    if not description:
        return set()
    return set(description.split())


def _amount_sign_matches(amount_cents: int, amount_sign: str | None) -> bool:
    if amount_sign in (None, "any"):
        return True
    if amount_sign == "positive":
        return amount_cents > 0
    if amount_sign == "negative":
        return amount_cents < 0
    return False


def _rule_matches_description(description: str, rule: CategoryRule) -> bool:
    tokens = _description_tokens(description)
    if (
        rule.description_contains is not None
        and rule.description_contains not in description
    ):
        return False
    if rule.description_tokens_any and not any(
        token in tokens or token in description for token in rule.description_tokens_any
    ):
        return False
    if rule.description_tokens_all and not all(
        token in tokens or token in description for token in rule.description_tokens_all
    ):
        return False
    if (
        rule.description_contains is not None
        or rule.description_tokens_any
        or rule.description_tokens_all
    ) and not description:
        return False
    return True


def _rule_matches_amount(amount_cents: int, rule: CategoryRule) -> bool:
    if rule.amount_min_cents is not None and amount_cents < rule.amount_min_cents:
        return False
    if rule.amount_max_cents is not None and amount_cents > rule.amount_max_cents:
        return False
    return _amount_sign_matches(amount_cents, rule.amount_sign)


def _category_reason(rule: CategoryRule) -> str:
    if rule.reason is not None:
        return f"Matched rule {rule.rule_id}: {rule.reason}"
    return f"Matched rule {rule.rule_id} for category {rule.category}."


def match_category_rule(
    transaction: dict[str, object],
    rule: CategoryRule,
) -> dict[str, object] | None:
    """Return a category result when one rule matches one transaction."""
    bank_transaction_id = _transaction_identity(transaction)
    amount_cents = _transaction_amount(transaction)
    matched_description = _transaction_description(transaction)

    if not _rule_matches_description(matched_description, rule):
        return None
    if not _rule_matches_amount(amount_cents, rule):
        return None

    return {
        "bank_transaction_id": bank_transaction_id,
        "category": rule.category,
        "category_source": "rule",
        "category_rule_id": rule.rule_id,
        "category_reason": _category_reason(rule),
        "matched_rule_priority": rule.priority,
        "matched_description": matched_description,
        "amount_cents": amount_cents,
    }


def categorize_transaction(
    transaction: dict[str, object],
    rules: list[CategoryRule],
) -> dict[str, object]:
    """Categorize one bank transaction with the highest-priority matching rule."""
    bank_transaction_id = _transaction_identity(transaction)
    amount_cents = _transaction_amount(transaction)
    matched_description = _transaction_description(transaction)

    ordered_rules = sorted(rules, key=lambda rule: (-rule.priority, rule.rule_id))
    for rule in ordered_rules:
        result = match_category_rule(transaction, rule)
        if result is not None:
            return result

    return {
        "bank_transaction_id": bank_transaction_id,
        "category": None,
        "category_source": None,
        "category_rule_id": None,
        "category_reason": "No category rule matched.",
        "matched_rule_priority": None,
        "matched_description": matched_description,
        "amount_cents": amount_cents,
    }


def categorize_transactions(
    transactions: list[dict[str, object]],
    rules: list[CategoryRule],
) -> list[dict[str, object]]:
    """Categorize bank transactions while preserving input order."""
    return [categorize_transaction(transaction, rules) for transaction in transactions]


def default_category_rules() -> list[CategoryRule]:
    """Return deterministic demo-friendly default category rules."""
    return [
        CategoryRule(
            rule_id="owner-contribution-deposit",
            category="Owner Contribution",
            priority=100,
            description_tokens_all=("owner", "contribution"),
            amount_sign="positive",
            reason=(
                "description contains owner contribution "
                "and the amount is an inflow"
            ),
        ),
        CategoryRule(
            rule_id="software-subscription",
            category="Software",
            priority=90,
            description_tokens_any=("software", "subscription", "saas"),
            amount_sign="negative",
            reason="description indicates a software subscription outflow",
        ),
        CategoryRule(
            rule_id="office-supplies",
            category="Office Supplies",
            priority=80,
            description_tokens_all=("office", "supplies"),
            amount_sign="negative",
            reason="description indicates office supplies",
        ),
        CategoryRule(
            rule_id="meals",
            category="Meals",
            priority=70,
            description_tokens_any=("meal", "meals", "restaurant", "cafe", "coffee"),
            amount_sign="negative",
            reason="description indicates a meal or restaurant purchase",
        ),
        CategoryRule(
            rule_id="rent",
            category="Rent",
            priority=70,
            description_tokens_any=("rent", "lease"),
            amount_sign="negative",
            reason="description indicates rent or lease expense",
        ),
        CategoryRule(
            rule_id="revenue-deposit",
            category="Revenue",
            priority=60,
            description_tokens_any=("revenue", "payment", "deposit", "customer"),
            amount_sign="positive",
            reason="description indicates customer revenue or deposit inflow",
        ),
    ]


def load_bank_transactions_for_categorization(
    connection: sqlite3.Connection,
) -> list[dict[str, object]]:
    """Load imported bank transactions for read-only categorization review."""
    rows = connection.execute(
        """
        SELECT
            bank_transaction_id,
            transaction_date,
            posted_date,
            description_raw,
            description_normalized,
            amount_cents,
            external_id,
            check_number,
            duplicate_group_id
        FROM bank_transactions
        ORDER BY transaction_date, bank_transaction_id
        """
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, object]:
    keys = (
        "bank_transaction_id",
        "transaction_date",
        "posted_date",
        "description_raw",
        "description_normalized",
        "amount_cents",
        "external_id",
        "check_number",
        "duplicate_group_id",
    )
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in keys}
    return dict(zip(keys, row, strict=True))
