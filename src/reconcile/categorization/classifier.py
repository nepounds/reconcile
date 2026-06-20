"""Small local categorization classifier trained from user corrections.

This module intentionally uses only the Python standard library. It is a simple
nearest-token-overlap classifier, not a production ML model. Corrections and
rules remain authoritative.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from reconcile.categorization.rules import CategoryRule, categorize_transaction
from reconcile.exceptions import ValidationError

_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class LocalCategoryClassifier:
    """A deterministic local classifier based on token overlap."""

    examples: tuple[dict[str, object], ...]
    category_tokens: dict[str, tuple[frozenset[str], ...]]


def _validate_confidence(min_confidence: float) -> float:
    if isinstance(min_confidence, bool) or not isinstance(min_confidence, int | float):
        raise ValidationError("min_confidence must be a number between 0.0 and 1.0")
    value = float(min_confidence)
    if math.isnan(value) or value < 0.0 or value > 1.0:
        raise ValidationError("min_confidence must be between 0.0 and 1.0")
    return value


def _tokens(value: object) -> frozenset[str]:
    if value is None:
        return frozenset()
    return frozenset(_TOKEN_RE.findall(str(value).lower()))


def _transaction_text(transaction: dict[str, object]) -> str:
    normalized = transaction.get("description_normalized")
    raw = transaction.get("description_raw")
    return str(normalized or raw or "")


def _validate_transaction(transaction: dict[str, object]) -> tuple[str, int, str]:
    bank_transaction_id = transaction.get("bank_transaction_id")
    if not isinstance(bank_transaction_id, str) or not bank_transaction_id.strip():
        raise ValidationError("bank_transaction_id must be a nonblank string")
    amount_cents = transaction.get("amount_cents")
    if isinstance(amount_cents, bool) or not isinstance(amount_cents, int):
        raise ValidationError("amount_cents must be an integer")
    text = _transaction_text(transaction)
    return bank_transaction_id.strip(), amount_cents, text


def _uncategorized_result(
    transaction: dict[str, object],
    reason: str,
    *,
    confidence: float | None = None,
) -> dict[str, object]:
    bank_transaction_id, amount_cents, matched_description = _validate_transaction(
        transaction
    )
    return {
        "bank_transaction_id": bank_transaction_id,
        "category": None,
        "category_source": None,
        "category_rule_id": None,
        "category_reason": reason,
        "matched_rule_priority": None,
        "matched_description": matched_description,
        "amount_cents": amount_cents,
        "classifier_confidence": confidence,
    }


def _classifier_result(
    transaction: dict[str, object],
    category: str,
    confidence: float,
) -> dict[str, object]:
    bank_transaction_id, amount_cents, matched_description = _validate_transaction(
        transaction
    )
    return {
        "bank_transaction_id": bank_transaction_id,
        "category": category,
        "category_source": "classifier",
        "category_rule_id": None,
        "category_reason": (
            "Local classifier predicted category "
            f"{category!r} with confidence {confidence:.2f}"
        ),
        "matched_rule_priority": None,
        "matched_description": matched_description,
        "amount_cents": amount_cents,
        "classifier_confidence": confidence,
    }


def train_category_classifier(training_examples: list[dict[str, object]]) -> object:
    """Train a deterministic local classifier from correction examples."""
    if not training_examples:
        raise ValidationError("training_examples must not be empty")

    normalized_examples: list[dict[str, object]] = []
    category_tokens: dict[str, list[frozenset[str]]] = {}
    categories: set[str] = set()

    for index, example in enumerate(training_examples):
        text = example.get("text")
        category = example.get("category")
        if not isinstance(text, str) or not text.strip():
            raise ValidationError(
                f"training example {index} must include nonblank text"
            )
        if not isinstance(category, str) or not category.strip():
            raise ValidationError(
                f"training example {index} must include a nonblank category"
            )
        category = category.strip()
        token_set = _tokens(text)
        if not token_set:
            raise ValidationError(
                f"training example {index} must include tokenizable text"
            )
        categories.add(category)
        category_tokens.setdefault(category, []).append(token_set)
        normalized_examples.append(
            {
                "text": text.strip(),
                "category": category,
                "tokens": tuple(sorted(token_set)),
            }
        )

    if len(categories) < 2:
        raise ValidationError("training requires at least two categories")

    frozen_category_tokens = {
        category: tuple(token_sets)
        for category, token_sets in sorted(category_tokens.items())
    }
    return LocalCategoryClassifier(
        examples=tuple(normalized_examples),
        category_tokens=frozen_category_tokens,
    )


def _score_category(
        transaction_tokens: frozenset[str],
        examples: tuple[frozenset[str], ...],
    ) -> float:
    if not transaction_tokens:
        return 0.0
    best = 0.0
    for example_tokens in examples:
        overlap = len(transaction_tokens & example_tokens)
        union = len(transaction_tokens | example_tokens)
        if union == 0:
            score = 0.0
        else:
            score = overlap / union
        best = max(best, score)
    return best


def predict_category(
    model: object,
    transaction: dict[str, object],
    *,
    min_confidence: float = 0.60,
) -> dict[str, object]:
    """Predict one transaction category with the local classifier."""
    min_confidence = _validate_confidence(min_confidence)
    if not isinstance(model, LocalCategoryClassifier):
        raise ValidationError("model must be trained by train_category_classifier")

    _validate_transaction(transaction)
    transaction_tokens = _tokens(_transaction_text(transaction))
    if not transaction_tokens:
        return _uncategorized_result(
            transaction,
            "Local classifier could not find usable description tokens",
            confidence=0.0,
        )

    scored: list[tuple[float, str]] = []
    for category, examples in model.category_tokens.items():
        scored.append((_score_category(transaction_tokens, examples), category))
    scored.sort(key=lambda item: (-item[0], item[1]))

    confidence, category = scored[0]
    confidence = round(float(confidence), 6)
    if confidence <= min_confidence:
        return _uncategorized_result(
            transaction,
            (
                "Local classifier confidence "
                f"{confidence:.2f} is below threshold {min_confidence:.2f}"
            ),
            confidence=confidence,
        )
    return _classifier_result(transaction, category, confidence)


def predict_categories(
    model: object,
    transactions: list[dict[str, object]],
    *,
    min_confidence: float = 0.60,
) -> list[dict[str, object]]:
    """Predict categories for transactions while preserving input order."""
    min_confidence = _validate_confidence(min_confidence)
    return [
        predict_category(model, dict(transaction), min_confidence=min_confidence)
        for transaction in transactions
    ]


def _latest_correction_for_transaction(
    corrections: list[dict[str, object]], bank_transaction_id: str
) -> dict[str, object] | None:
    matching = [
        dict(correction)
        for correction in corrections
        if correction.get("bank_transaction_id") == bank_transaction_id
    ]
    if not matching:
        return None
    matching.sort(
        key=lambda item: (
            str(item.get("corrected_at") or ""),
            str(item.get("created_at") or ""),
            str(item.get("correction_id") or ""),
        )
    )
    return matching[-1]


def _correction_result(
    transaction: dict[str, object], correction: dict[str, object]
) -> dict[str, object]:
    bank_transaction_id, amount_cents, matched_description = _validate_transaction(
        transaction
    )
    reason = correction.get("reason")
    category = correction.get("corrected_category")
    reason_text = f"Corrected to {category}"
    if reason:
        reason_text = f"{reason_text}: {reason}"
    return {
        "bank_transaction_id": bank_transaction_id,
        "category": category,
        "category_source": "correction",
        "category_rule_id": None,
        "category_reason": reason_text,
        "matched_rule_priority": None,
        "matched_description": matched_description,
        "amount_cents": amount_cents,
        "classifier_confidence": None,
        "correction_id": correction.get("correction_id"),
        "corrected_at": correction.get("corrected_at"),
    }


def categorize_with_rules_corrections_and_classifier(
    transaction: dict[str, object],
    *,
    rules: list[CategoryRule],
    corrections: list[dict[str, object]],
    model: object | None = None,
    min_confidence: float = 0.60,
) -> dict[str, object]:
    """Categorize using correction > rule > classifier > uncategorized precedence."""
    min_confidence = _validate_confidence(min_confidence)
    transaction_copy = dict(transaction)
    bank_transaction_id, _, _ = _validate_transaction(transaction_copy)

    correction = _latest_correction_for_transaction(corrections, bank_transaction_id)
    if correction is not None:
        return _correction_result(transaction_copy, correction)

    rule_result = categorize_transaction(transaction_copy, rules)
    if rule_result.get("category_source") == "rule":
        output = dict(rule_result)
        output["classifier_confidence"] = None
        return output

    if model is not None:
        return predict_category(
            model, transaction_copy, min_confidence=min_confidence
        )

    output = dict(rule_result)
    output["classifier_confidence"] = None
    return output
