from __future__ import annotations

import sqlite3

import pytest

from reconcile.categorization.rules import (
    CategoryRule,
    categorize_transaction,
    categorize_transactions,
    default_category_rules,
    load_bank_transactions_for_categorization,
    match_category_rule,
    normalize_rule_text,
)
from reconcile.db import initialize_schema
from reconcile.exceptions import ValidationError


def bank_transaction(
    *,
    bank_transaction_id: str = "bank-001",
    description_raw: object = "POS SOFTWARE SUBSCRIPTION",
    description_normalized: object = "pos software subscription",
    amount_cents: object = -5000,
) -> dict[str, object]:
    return {
        "bank_transaction_id": bank_transaction_id,
        "description_raw": description_raw,
        "description_normalized": description_normalized,
        "amount_cents": amount_cents,
    }


def test_category_rule_valid_creation_normalizes_text_fields() -> None:
    rule = CategoryRule(
        rule_id=" software ",
        category=" Software ",
        priority=10,
        description_contains="Software, Subscription!",
        description_tokens_any=("SaaS",),
        description_tokens_all=("Cloud App",),
        amount_min_cents=-10000,
        amount_max_cents=-1,
        amount_sign="negative",
        reason=" recurring software ",
    )

    assert rule.rule_id == "software"
    assert rule.category == "Software"
    assert rule.description_contains == "software subscription"
    assert rule.description_tokens_any == ("saas",)
    assert rule.description_tokens_all == ("cloud app",)
    assert rule.reason == "recurring software"


@pytest.mark.parametrize("rule_id", ["", "   "])
def test_category_rule_blank_rule_id_rejected(rule_id: str) -> None:
    with pytest.raises(ValidationError, match="rule_id"):
        CategoryRule(rule_id=rule_id, category="Meals", priority=1)


@pytest.mark.parametrize("category", ["", "   "])
def test_category_rule_blank_category_rejected(category: str) -> None:
    with pytest.raises(ValidationError, match="category"):
        CategoryRule(rule_id="meals", category=category, priority=1)


def test_category_rule_bool_priority_rejected() -> None:
    with pytest.raises(ValidationError, match="priority"):
        CategoryRule(rule_id="meals", category="Meals", priority=True)


def test_category_rule_non_int_priority_rejected() -> None:
    with pytest.raises(ValidationError, match="priority"):
        CategoryRule(
            rule_id="meals",
            category="Meals",
            priority="1",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("field_name", ["description_contains", "reason"])
def test_category_rule_blank_optional_strings_rejected(field_name: str) -> None:
    kwargs = {field_name: "   "}
    with pytest.raises(ValidationError, match=field_name):
        CategoryRule(rule_id="meals", category="Meals", priority=1, **kwargs)


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("description_tokens_any", ("",)),
        ("description_tokens_any", ("   ",)),
        ("description_tokens_any", (123,)),
        ("description_tokens_any", ["software"]),
        ("description_tokens_all", ("",)),
        ("description_tokens_all", ("   ",)),
        ("description_tokens_all", (None,)),
        ("description_tokens_all", ["owner"]),
    ],
)
def test_category_rule_invalid_token_tuples_rejected(
    field_name: str,
    value: object,
) -> None:
    kwargs = {field_name: value}
    with pytest.raises(ValidationError, match=field_name):
        CategoryRule(rule_id="rule", category="Category", priority=1, **kwargs)


@pytest.mark.parametrize("field_name", ["amount_min_cents", "amount_max_cents"])
def test_category_rule_bool_amount_bounds_rejected(field_name: str) -> None:
    kwargs = {field_name: False}
    with pytest.raises(ValidationError, match=field_name):
        CategoryRule(rule_id="rule", category="Category", priority=1, **kwargs)


def test_category_rule_min_greater_than_max_rejected() -> None:
    with pytest.raises(ValidationError, match="amount_min_cents"):
        CategoryRule(
            rule_id="rule",
            category="Category",
            priority=1,
            amount_min_cents=10,
            amount_max_cents=1,
        )


def test_category_rule_invalid_amount_sign_rejected() -> None:
    with pytest.raises(ValidationError, match="amount_sign"):
        CategoryRule(
            rule_id="rule",
            category="Category",
            priority=1,
            amount_sign="outflow",
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("SOFTWARE Subscription", "software subscription"),
        ("POS: Software-Subscription!!!", "pos software subscription"),
        ("  many\tspaces\nthere  ", "many spaces there"),
        (None, ""),
    ],
)
def test_normalize_rule_text(value: str | None, expected: str) -> None:
    assert normalize_rule_text(value) == expected


def test_phrase_contains_match() -> None:
    rule = CategoryRule(
        rule_id="software",
        category="Software",
        priority=1,
        description_contains="software subscription",
    )

    result = match_category_rule(bank_transaction(), rule)

    assert result is not None
    assert result["category"] == "Software"


def test_any_token_match() -> None:
    rule = CategoryRule(
        rule_id="meals",
        category="Meals",
        priority=1,
        description_tokens_any=("restaurant", "software"),
    )

    assert match_category_rule(bank_transaction(), rule) is not None


def test_all_token_match() -> None:
    rule = CategoryRule(
        rule_id="owner",
        category="Owner Contribution",
        priority=1,
        description_tokens_all=("owner", "contribution"),
    )
    transaction = bank_transaction(
        description_raw="DEPOSIT OWNER CONTRIBUTION",
        description_normalized="deposit owner contribution",
        amount_cents=500000,
    )

    assert match_category_rule(transaction, rule) is not None


def test_amount_minimum_match() -> None:
    rule = CategoryRule(
        rule_id="large-deposit",
        category="Revenue",
        priority=1,
        amount_min_cents=10000,
    )
    transaction = bank_transaction(amount_cents=25000)

    assert match_category_rule(transaction, rule) is not None


def test_amount_maximum_match() -> None:
    rule = CategoryRule(
        rule_id="small-expense",
        category="Office Supplies",
        priority=1,
        amount_max_cents=-1,
    )

    assert match_category_rule(bank_transaction(amount_cents=-2500), rule) is not None


def test_positive_amount_sign_match() -> None:
    rule = CategoryRule(
        rule_id="deposit",
        category="Revenue",
        priority=1,
        amount_sign="positive",
    )

    assert match_category_rule(bank_transaction(amount_cents=100), rule) is not None


def test_negative_amount_sign_match() -> None:
    rule = CategoryRule(
        rule_id="withdrawal",
        category="Meals",
        priority=1,
        amount_sign="negative",
    )

    assert match_category_rule(bank_transaction(amount_cents=-100), rule) is not None


def test_mismatched_sign_does_not_match() -> None:
    rule = CategoryRule(
        rule_id="deposit",
        category="Revenue",
        priority=1,
        amount_sign="positive",
    )

    assert match_category_rule(bank_transaction(amount_cents=-100), rule) is None


def test_mismatched_amount_range_does_not_match() -> None:
    rule = CategoryRule(
        rule_id="large-deposit",
        category="Revenue",
        priority=1,
        amount_min_cents=10000,
    )

    assert match_category_rule(bank_transaction(amount_cents=9999), rule) is None


def test_missing_description_does_not_match_description_rule() -> None:
    rule = CategoryRule(
        rule_id="software",
        category="Software",
        priority=1,
        description_contains="software",
    )
    transaction = bank_transaction(description_raw=None, description_normalized=None)

    assert match_category_rule(transaction, rule) is None


def test_match_result_includes_explainable_fields() -> None:
    rule = CategoryRule(
        rule_id="software",
        category="Software",
        priority=10,
        description_contains="software",
        reason="software text found",
    )

    result = match_category_rule(bank_transaction(), rule)

    assert result == {
        "bank_transaction_id": "bank-001",
        "category": "Software",
        "category_source": "rule",
        "category_rule_id": "software",
        "category_reason": "Matched rule software: software text found",
        "matched_rule_priority": 10,
        "matched_description": "pos software subscription",
        "amount_cents": -5000,
    }


def test_categorize_transaction_highest_priority_rule_wins() -> None:
    rules = [
        CategoryRule(
            rule_id="broad",
            category="Office Supplies",
            priority=1,
            description_tokens_any=("software",),
        ),
        CategoryRule(
            rule_id="specific",
            category="Software",
            priority=10,
            description_tokens_any=("software",),
        ),
    ]

    result = categorize_transaction(bank_transaction(), rules)

    assert result["category"] == "Software"
    assert result["category_rule_id"] == "specific"


def test_categorize_transaction_tied_priority_sorts_by_rule_id() -> None:
    rules = [
        CategoryRule(
            rule_id="z-rule",
            category="Wrong",
            priority=10,
            description_tokens_any=("software",),
        ),
        CategoryRule(
            rule_id="a-rule",
            category="Right",
            priority=10,
            description_tokens_any=("software",),
        ),
    ]

    result = categorize_transaction(bank_transaction(), rules)

    assert result["category"] == "Right"
    assert result["category_rule_id"] == "a-rule"


def test_categorize_transaction_only_one_category_returned() -> None:
    rules = [
        CategoryRule(
            rule_id="software",
            category="Software",
            priority=10,
            description_tokens_any=("software",),
        ),
        CategoryRule(
            rule_id="subscription",
            category="Office Supplies",
            priority=9,
            description_tokens_any=("subscription",),
        ),
    ]

    result = categorize_transaction(bank_transaction(), rules)

    assert result["category"] == "Software"
    assert isinstance(result["category"], str)


def test_no_matching_rule_returns_uncategorized_result() -> None:
    result = categorize_transaction(bank_transaction(), [])

    assert result == {
        "bank_transaction_id": "bank-001",
        "category": None,
        "category_source": None,
        "category_rule_id": None,
        "category_reason": "No category rule matched.",
        "matched_rule_priority": None,
        "matched_description": "pos software subscription",
        "amount_cents": -5000,
    }


def test_categorize_transaction_does_not_mutate_input_transaction() -> None:
    transaction = bank_transaction()
    original = transaction.copy()

    categorize_transaction(transaction, default_category_rules())

    assert transaction == original


def test_categorize_transactions_preserves_transaction_order() -> None:
    transactions = [
        bank_transaction(bank_transaction_id="bank-002", amount_cents=-5000),
        bank_transaction(
            bank_transaction_id="bank-001",
            description_raw="DEPOSIT OWNER CONTRIBUTION",
            description_normalized="deposit owner contribution",
            amount_cents=500000,
        ),
    ]

    results = categorize_transactions(transactions, default_category_rules())

    assert [result["bank_transaction_id"] for result in results] == [
        "bank-002",
        "bank-001",
    ]


def test_default_category_rules_categorize_demo_like_descriptions() -> None:
    transactions = [
        bank_transaction(
            bank_transaction_id="bank-001",
            description_raw="DEPOSIT OWNER CONTRIBUTION",
            description_normalized="deposit owner contribution",
            amount_cents=500000,
        ),
        bank_transaction(
            bank_transaction_id="bank-002",
            description_raw="POS SOFTWARE SUBSCRIPTION",
            description_normalized="pos software subscription",
            amount_cents=-5000,
        ),
    ]

    results = categorize_transactions(transactions, default_category_rules())

    assert [result["category"] for result in results] == [
        "Owner Contribution",
        "Software",
    ]


def test_default_rules_categorize_owner_contribution() -> None:
    transaction = bank_transaction(
        description_raw="Deposit owner contribution",
        description_normalized="deposit owner contribution",
        amount_cents=500000,
    )

    result = categorize_transaction(transaction, default_category_rules())

    assert result["category"] == "Owner Contribution"


def test_default_rules_categorize_software_subscription() -> None:
    result = categorize_transaction(bank_transaction(), default_category_rules())

    assert result["category"] == "Software"


def test_default_rules_categorize_office_supplies_if_matching_text_exists() -> None:
    transaction = bank_transaction(
        description_raw="Office Supplies Store",
        description_normalized="office supplies store",
        amount_cents=-2500,
    )

    result = categorize_transaction(transaction, default_category_rules())

    assert result["category"] == "Office Supplies"


def test_default_rules_leave_unknown_transaction_uncategorized() -> None:
    transaction = bank_transaction(
        description_raw="Mystery Transaction",
        description_normalized="mystery transaction",
        amount_cents=-1234,
    )

    result = categorize_transaction(transaction, default_category_rules())

    assert result["category"] is None


def test_missing_bank_transaction_id_rejected() -> None:
    transaction = bank_transaction()
    del transaction["bank_transaction_id"]

    with pytest.raises(ValidationError, match="bank_transaction_id"):
        categorize_transaction(transaction, default_category_rules())


def test_blank_bank_transaction_id_rejected() -> None:
    with pytest.raises(ValidationError, match="bank_transaction_id"):
        categorize_transaction(
            bank_transaction(bank_transaction_id="   "),
            default_category_rules(),
        )


def test_missing_amount_rejected() -> None:
    transaction = bank_transaction()
    del transaction["amount_cents"]

    with pytest.raises(ValidationError, match="amount_cents"):
        categorize_transaction(transaction, default_category_rules())


def test_bool_amount_rejected() -> None:
    with pytest.raises(ValidationError, match="amount_cents"):
        categorize_transaction(
            bank_transaction(amount_cents=True),
            default_category_rules(),
        )


def test_non_int_amount_rejected() -> None:
    with pytest.raises(ValidationError, match="amount_cents"):
        categorize_transaction(
            bank_transaction(amount_cents="-50.00"),
            default_category_rules(),
        )


def test_load_bank_transactions_for_categorization_deterministic_order() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    initialize_schema(connection)
    insert_bank_import(connection)
    insert_bank_transaction(
        connection,
        bank_transaction_id="bank-002",
        transaction_date="2026-01-02",
        description_raw="Second Row",
        description_normalized="second row",
        amount_cents=-200,
    )
    insert_bank_transaction(
        connection,
        bank_transaction_id="bank-001",
        transaction_date="2026-01-01",
        description_raw="First Row",
        description_normalized="first row",
        amount_cents=100,
    )

    rows = load_bank_transactions_for_categorization(connection)

    assert [row["bank_transaction_id"] for row in rows] == ["bank-001", "bank-002"]


def test_load_bank_transactions_preserves_descriptions_and_amounts() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    initialize_schema(connection)
    insert_bank_import(connection)
    insert_bank_transaction(
        connection,
        bank_transaction_id="bank-001",
        transaction_date="2026-01-01",
        description_raw="POS SOFTWARE SUBSCRIPTION",
        description_normalized="pos software subscription",
        amount_cents=-5000,
    )

    row = load_bank_transactions_for_categorization(connection)[0]

    assert row["description_raw"] == "POS SOFTWARE SUBSCRIPTION"
    assert row["description_normalized"] == "pos software subscription"
    assert row["amount_cents"] == -5000


def test_load_bank_transactions_does_not_mutate_bank_transactions() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    initialize_schema(connection)
    insert_bank_import(connection)
    insert_bank_transaction(
        connection,
        bank_transaction_id="bank-001",
        transaction_date="2026-01-01",
        description_raw="Office Supplies Store",
        description_normalized="office supplies store",
        amount_cents=-2500,
    )
    before = connection.execute("SELECT * FROM bank_transactions").fetchall()

    load_bank_transactions_for_categorization(connection)

    after = connection.execute("SELECT * FROM bank_transactions").fetchall()
    assert [tuple(row) for row in after] == [tuple(row) for row in before]


def test_load_bank_transactions_does_not_append_ledger_events() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    initialize_schema(connection)
    insert_bank_import(connection)
    insert_bank_transaction(
        connection,
        bank_transaction_id="bank-001",
        transaction_date="2026-01-01",
        description_raw="Office Supplies Store",
        description_normalized="office supplies store",
        amount_cents=-2500,
    )

    load_bank_transactions_for_categorization(connection)

    event_count = connection.execute("SELECT COUNT(*) FROM ledger_events").fetchone()[0]
    assert event_count == 0


def insert_bank_import(connection: sqlite3.Connection) -> None:
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
        ("import-001", "demo", "bank.csv", "hash", "2026-01-01T00:00:00", 1),
    )


def insert_bank_transaction(
    connection: sqlite3.Connection,
    *,
    bank_transaction_id: str,
    transaction_date: str,
    description_raw: str,
    description_normalized: str,
    amount_cents: int,
) -> None:
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            bank_transaction_id,
            "import-001",
            transaction_date,
            transaction_date,
            description_raw,
            description_normalized,
            amount_cents,
            bank_transaction_id,
            None,
            f"hash-{bank_transaction_id}",
            None,
            "2026-01-01T00:00:00",
        ),
    )
