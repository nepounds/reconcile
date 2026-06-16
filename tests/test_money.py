from decimal import Decimal

import pytest

from reconcile.exceptions import MoneyError, ReconcileError, ValidationError
from reconcile.money import format_cents, parse_money_to_cents


def test_parse_valid_whole_dollar_amounts():
    assert parse_money_to_cents("12") == 1200
    assert parse_money_to_cents("1,234") == 123400


def test_parse_valid_decimal_amounts():
    assert parse_money_to_cents("12.34") == 1234
    assert parse_money_to_cents(" 12.34 ") == 1234


def test_parse_valid_negative_amounts():
    assert parse_money_to_cents("-12.34") == -1234
    assert parse_money_to_cents("-$12.34") == -1234


def test_parse_valid_comma_and_currency_symbol_amounts():
    assert parse_money_to_cents("1,234.56") == 123456
    assert parse_money_to_cents("$12.34") == 1234


def test_parse_zero_amounts():
    assert parse_money_to_cents("0") == 0
    assert parse_money_to_cents("0.00") == 0


def test_parse_one_cent():
    assert parse_money_to_cents("0.01") == 1


def test_format_zero_cents():
    assert format_cents(0) == "0.00"


def test_format_positive_cents():
    assert format_cents(1) == "0.01"
    assert format_cents(1234) == "12.34"


def test_format_negative_cents():
    assert format_cents(-1234) == "-12.34"


@pytest.mark.parametrize("value", ["", " ", "\t"])
def test_parse_rejects_blank_strings(value):
    with pytest.raises(MoneyError, match="blank"):
        parse_money_to_cents(value)


@pytest.mark.parametrize("value", ["abc", "12..34", "$", "-$", "12.3.4"])
def test_parse_rejects_invalid_text(value):
    with pytest.raises(MoneyError):
        parse_money_to_cents(value)


def test_parse_rejects_too_many_decimal_places():
    with pytest.raises(MoneyError, match="Invalid money value"):
        parse_money_to_cents("12.345")


@pytest.mark.parametrize("value", ["12,34.56", "1,23,456.78", "1234,567.89"])
def test_parse_rejects_malformed_commas(value):
    with pytest.raises(MoneyError):
        parse_money_to_cents(value)


@pytest.mark.parametrize("value", [12, 12.34, Decimal("12.34"), None])
def test_parse_rejects_non_string_input(value):
    with pytest.raises(MoneyError, match="string"):
        parse_money_to_cents(value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["1234", 12.34, Decimal("12.34"), None])
def test_format_rejects_non_int_input(value):
    with pytest.raises(MoneyError, match="integer"):
        format_cents(value)  # type: ignore[arg-type]


def test_format_rejects_bool_input():
    with pytest.raises(MoneyError, match="integer"):
        format_cents(True)  # type: ignore[arg-type]


def test_money_error_uses_custom_exception_hierarchy():
    assert issubclass(MoneyError, ValidationError)
    assert issubclass(ValidationError, ReconcileError)
    assert issubclass(ReconcileError, Exception)
