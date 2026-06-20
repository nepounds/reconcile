from __future__ import annotations

import json
from pathlib import Path

import pytest

from reconcile.categorization.classifier import (
    categorize_with_rules_corrections_and_classifier,
    predict_categories,
    predict_category,
    train_category_classifier,
)
from reconcile.categorization.rules import CategoryRule
from reconcile.exceptions import ValidationError

TRAINING_EXAMPLES = [
    {"text": "adobe creative cloud subscription", "category": "Software"},
    {"text": "microsoft office subscription", "category": "Software"},
    {"text": "coffee client lunch", "category": "Meals"},
    {"text": "restaurant business meal", "category": "Meals"},
]


def transaction(
    bank_transaction_id: str = "bank-1",
    description: str = "adobe software subscription",
    amount_cents: int = -1200,
) -> dict[str, object]:
    return {
        "bank_transaction_id": bank_transaction_id,
        "description_raw": description.upper(),
        "description_normalized": description,
        "amount_cents": amount_cents,
    }


def test_training_rejects_empty_examples() -> None:
    with pytest.raises(ValidationError, match="must not be empty"):
        train_category_classifier([])


@pytest.mark.parametrize(
    "examples",
    [
        [{"category": "Software"}],
        [{"text": "adobe"}],
        [{"text": " ", "category": "Software"}],
        [{"text": "adobe", "category": " "}],
    ],
)
def test_training_rejects_malformed_examples(examples: list[dict[str, object]]) -> None:
    with pytest.raises(ValidationError):
        train_category_classifier(examples)


def test_training_rejects_insufficient_category_variety() -> None:
    with pytest.raises(ValidationError, match="at least two categories"):
        train_category_classifier(
            [
                {"text": "adobe subscription", "category": "Software"},
                {"text": "microsoft subscription", "category": "Software"},
            ]
        )


def test_model_predicts_known_category_from_similar_text() -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)

    result = predict_category(
        model,
        transaction(description="adobe creative cloud"),
        min_confidence=0.20,
    )

    assert result["category"] == "Software"
    assert result["category_source"] == "classifier"
    assert result["category_rule_id"] is None
    assert result["matched_rule_priority"] is None
    assert result["classifier_confidence"] >= 0.20


def test_low_confidence_returns_uncategorized() -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)

    result = predict_category(
        model,
        transaction(description="random fuel station"),
        min_confidence=0.90,
    )

    assert result["category"] is None
    assert result["category_source"] is None
    assert result["classifier_confidence"] < 0.90
    assert "below threshold" in result["category_reason"]


def test_confidence_threshold_is_respected() -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)

    confident = predict_category(
        model,
        transaction(description="adobe creative cloud subscription"),
        min_confidence=0.20,
    )
    strict = predict_category(
        model,
        transaction(description="adobe creative cloud subscription"),
        min_confidence=1.00,
    )

    assert confident["category"] == "Software"
    assert strict["category"] is None


@pytest.mark.parametrize("value", [-0.01, 1.01, float("nan"), "0.5", True])
def test_invalid_confidence_values_raise_validation_error(value: object) -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)

    with pytest.raises(ValidationError, match="min_confidence"):
        predict_category(model, transaction(), min_confidence=value)  # type: ignore[arg-type]


def test_predict_categories_preserves_input_order() -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)
    transactions = [
        transaction("bank-1", "adobe creative cloud"),
        transaction("bank-2", "restaurant business meal"),
    ]

    results = predict_categories(model, transactions, min_confidence=0.20)

    assert [row["bank_transaction_id"] for row in results] == ["bank-1", "bank-2"]


def test_classifier_output_is_json_serializable() -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)
    result = predict_category(model, transaction(), min_confidence=0.20)

    json.dumps(result)


def test_correction_overrides_rule_and_classifier() -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)
    rules = [
        CategoryRule(
            rule_id="rule-software",
            category="Software",
            priority=100,
            description_contains="adobe",
        )
    ]
    corrections = [
        {
            "correction_id": "corr-1",
            "bank_transaction_id": "bank-1",
            "corrected_category": "Owner Draw",
            "reason": "Manual review",
            "corrected_at": "2026-01-01T00:00:00+00:00",
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    ]

    result = categorize_with_rules_corrections_and_classifier(
        transaction(),
        rules=rules,
        corrections=corrections,
        model=model,
        min_confidence=0.20,
    )

    assert result["category"] == "Owner Draw"
    assert result["category_source"] == "correction"
    assert result["correction_id"] == "corr-1"


def test_rule_overrides_classifier() -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)
    rules = [
        CategoryRule(
            rule_id="rule-special",
            category="Office Supplies",
            priority=100,
            description_contains="adobe",
        )
    ]

    result = categorize_with_rules_corrections_and_classifier(
        transaction(description="adobe creative cloud"),
        rules=rules,
        corrections=[],
        model=model,
        min_confidence=0.20,
    )

    assert result["category"] == "Office Supplies"
    assert result["category_source"] == "rule"
    assert result["classifier_confidence"] is None


def test_classifier_only_runs_when_no_correction_or_rule_matches() -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)

    result = categorize_with_rules_corrections_and_classifier(
        transaction(description="adobe creative cloud"),
        rules=[],
        corrections=[],
        model=model,
        min_confidence=0.20,
    )

    assert result["category"] == "Software"
    assert result["category_source"] == "classifier"


def test_no_model_and_no_rule_returns_uncategorized() -> None:
    result = categorize_with_rules_corrections_and_classifier(
        transaction(description="unknown merchant"),
        rules=[],
        corrections=[],
        model=None,
    )

    assert result["category"] is None
    assert result["category_source"] is None
    assert result["classifier_confidence"] is None


def test_classifier_does_not_mutate_transaction_dicts() -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)
    source = transaction(description="adobe creative cloud")
    before = dict(source)

    predict_category(model, source, min_confidence=0.20)
    categorize_with_rules_corrections_and_classifier(
        source,
        rules=[],
        corrections=[],
        model=model,
        min_confidence=0.20,
    )

    assert source == before


def test_classifier_does_not_write_files(tmp_path: Path) -> None:
    before = set(tmp_path.iterdir())

    model = train_category_classifier(TRAINING_EXAMPLES)
    predict_category(model, transaction(), min_confidence=0.20)

    assert set(tmp_path.iterdir()) == before


def test_classifier_does_not_touch_database() -> None:
    model = train_category_classifier(TRAINING_EXAMPLES)

    result = predict_category(model, transaction(), min_confidence=0.20)

    assert result["category_source"] == "classifier"
