"""Account domain models and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from reconcile.exceptions import ValidationError


class AccountType(StrEnum):
    """Supported chart-of-accounts account types."""

    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class NormalBalance(StrEnum):
    """Supported normal balance sides."""

    DEBIT = "debit"
    CREDIT = "credit"


VALID_ACCOUNT_TYPES = tuple(account_type.value for account_type in AccountType)
VALID_NORMAL_BALANCES = tuple(balance.value for balance in NormalBalance)

_NORMAL_BALANCE_BY_ACCOUNT_TYPE = {
    AccountType.ASSET.value: NormalBalance.DEBIT.value,
    AccountType.EXPENSE.value: NormalBalance.DEBIT.value,
    AccountType.LIABILITY.value: NormalBalance.CREDIT.value,
    AccountType.EQUITY.value: NormalBalance.CREDIT.value,
    AccountType.REVENUE.value: NormalBalance.CREDIT.value,
}


def _validate_non_blank_string(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string.")

    cleaned_value = value.strip()
    if not cleaned_value:
        raise ValidationError(f"{field_name} cannot be blank.")

    return cleaned_value


def validate_account_type(account_type: str) -> str:
    """Validate and return an official account type string."""

    cleaned_account_type = _validate_non_blank_string(account_type, "account_type")
    if cleaned_account_type not in VALID_ACCOUNT_TYPES:
        valid_values = ", ".join(VALID_ACCOUNT_TYPES)
        raise ValidationError(
            f"account_type must be one of: {valid_values}. "
            f"Received {cleaned_account_type!r}."
        )

    return cleaned_account_type


def validate_normal_balance(normal_balance: str) -> str:
    """Validate and return an official normal balance string."""

    cleaned_normal_balance = _validate_non_blank_string(
        normal_balance,
        "normal_balance",
    )
    if cleaned_normal_balance not in VALID_NORMAL_BALANCES:
        valid_values = ", ".join(VALID_NORMAL_BALANCES)
        raise ValidationError(
            f"normal_balance must be one of: {valid_values}. "
            f"Received {cleaned_normal_balance!r}."
        )

    return cleaned_normal_balance


def expected_normal_balance(account_type: str) -> str:
    """Return the required normal balance for an account type."""

    cleaned_account_type = validate_account_type(account_type)
    return _NORMAL_BALANCE_BY_ACCOUNT_TYPE[cleaned_account_type]


@dataclass(frozen=True)
class Account:
    """Validated chart-of-accounts account model."""

    account_id: str
    code: str
    name: str
    account_type: str
    normal_balance: str
    is_active: bool
    opened_at: str
    closed_at: str | None = None

    def __post_init__(self) -> None:
        account_id = _validate_non_blank_string(self.account_id, "account_id")
        code = _validate_non_blank_string(self.code, "code")
        name = _validate_non_blank_string(self.name, "name")
        account_type = validate_account_type(self.account_type)
        normal_balance = validate_normal_balance(self.normal_balance)

        if normal_balance != expected_normal_balance(account_type):
            expected_balance = expected_normal_balance(account_type)
            raise ValidationError(
                "normal_balance does not match account_type. "
                f"Account type {account_type!r} requires {expected_balance!r}. "
                f"Received {normal_balance!r}."
            )

        if not isinstance(self.is_active, bool):
            raise ValidationError("is_active must be a bool.")

        opened_at = _validate_non_blank_string(self.opened_at, "opened_at")

        closed_at = self.closed_at
        if closed_at is not None:
            closed_at = _validate_non_blank_string(closed_at, "closed_at")

        object.__setattr__(self, "account_id", account_id)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "account_type", account_type)
        object.__setattr__(self, "normal_balance", normal_balance)
        object.__setattr__(self, "opened_at", opened_at)
        object.__setattr__(self, "closed_at", closed_at)
