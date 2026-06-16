import pytest

from reconcile.accounts import Account, expected_normal_balance
from reconcile.exceptions import ValidationError


def make_account(**overrides):
    values = {
        "account_id": "acct-1000",
        "code": "1000",
        "name": "Cash",
        "account_type": "asset",
        "normal_balance": "debit",
        "is_active": True,
        "opened_at": "2026-01-01T00:00:00",
        "closed_at": None,
    }
    values.update(overrides)
    return Account(**values)


@pytest.mark.parametrize(
    ("account_type", "normal_balance"),
    [
        ("asset", "debit"),
        ("liability", "credit"),
        ("equity", "credit"),
        ("revenue", "credit"),
        ("expense", "debit"),
    ],
)
def test_create_valid_account_for_each_account_type(account_type, normal_balance):
    account = make_account(account_type=account_type, normal_balance=normal_balance)

    assert account.account_type == account_type
    assert account.normal_balance == normal_balance


@pytest.mark.parametrize(
    ("account_type", "normal_balance"),
    [
        ("asset", "debit"),
        ("expense", "debit"),
        ("liability", "credit"),
        ("equity", "credit"),
        ("revenue", "credit"),
    ],
)
def test_expected_normal_balance_returns_official_balance(account_type, normal_balance):
    assert expected_normal_balance(account_type) == normal_balance


@pytest.mark.parametrize(
    "field_name",
    ["account_id", "code", "name", "opened_at"],
)
def test_account_rejects_blank_required_text_fields(field_name):
    with pytest.raises(ValidationError, match=f"{field_name} cannot be blank"):
        make_account(**{field_name: "   "})


def test_account_rejects_invalid_account_type():
    with pytest.raises(ValidationError, match="account_type must be one of"):
        make_account(account_type="contra_asset")


def test_expected_normal_balance_rejects_invalid_account_type():
    with pytest.raises(ValidationError, match="account_type must be one of"):
        expected_normal_balance("not-real")


def test_account_rejects_invalid_normal_balance():
    with pytest.raises(ValidationError, match="normal_balance must be one of"):
        make_account(normal_balance="left")


def test_account_rejects_normal_balance_that_does_not_match_account_type():
    with pytest.raises(
        ValidationError,
        match="normal_balance does not match account_type",
    ):
        make_account(account_type="asset", normal_balance="credit")


@pytest.mark.parametrize("is_active", ["true", "false", 1, 0, None])
def test_account_rejects_non_bool_is_active(is_active):
    with pytest.raises(ValidationError, match="is_active must be a bool"):
        make_account(is_active=is_active)


def test_account_allows_closed_at_none():
    account = make_account(closed_at=None)

    assert account.closed_at is None


def test_account_rejects_blank_closed_at_when_provided():
    with pytest.raises(ValidationError, match="closed_at cannot be blank"):
        make_account(closed_at="   ")


def test_invalid_account_data_raises_validation_error():
    with pytest.raises(ValidationError):
        make_account(account_id="")
