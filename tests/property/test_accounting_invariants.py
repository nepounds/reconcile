"""Property tests for core double-entry accounting invariants."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from tests.property.conftest import (
    POSTING_SPEC_STRATEGY,
    POSTING_SPECS_STRATEGY,
    build_postings,
    expanded_accounting_equation,
    make_connection,
    make_journal_entry,
    make_unbalanced_journal_entry,
    open_standard_chart,
    post_generated_entries,
)

from reconcile.events.store import load_events
from reconcile.exceptions import ValidationError
from reconcile.journal.service import post_journal_entry
from reconcile.journal.validation import validate_journal_entry
from reconcile.reports.trial_balance import generate_trial_balance


@given(posting_spec=POSTING_SPEC_STRATEGY)
@settings(max_examples=50, deadline=None)
def test_generated_balanced_journal_entries_validate_successfully(posting_spec):
    posting = build_postings([posting_spec])[0]

    validate_journal_entry(make_journal_entry(posting))


@given(posting_spec=POSTING_SPEC_STRATEGY)
@settings(max_examples=50, deadline=None)
def test_generated_unbalanced_journal_entries_raise_validation_error(posting_spec):
    posting = build_postings([posting_spec])[0]

    with pytest.raises(ValidationError):
        validate_journal_entry(make_unbalanced_journal_entry(posting))


@given(posting_spec=POSTING_SPEC_STRATEGY)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_generated_valid_posted_entry_keeps_trial_balance_balanced(
    posting_spec,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    posting = build_postings([posting_spec])[0]

    post_journal_entry(connection, make_journal_entry(posting))

    rows = generate_trial_balance(connection)
    total_ending_debits = sum(row["ending_debit_balance_cents"] for row in rows)
    total_ending_credits = sum(
        row["ending_credit_balance_cents"] for row in rows
    )

    assert total_ending_debits == total_ending_credits


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_generated_sequences_of_valid_posted_entries_keep_trial_balance_balanced(
    posting_specs,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    postings = build_postings(posting_specs)

    post_generated_entries(connection, postings)

    rows = generate_trial_balance(connection)
    total_ending_debits = sum(row["ending_debit_balance_cents"] for row in rows)
    total_ending_credits = sum(
        row["ending_credit_balance_cents"] for row in rows
    )

    assert total_ending_debits == total_ending_credits


@given(posting_spec=POSTING_SPEC_STRATEGY)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_invalid_generated_entries_do_not_enter_event_store(posting_spec, tmp_path):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    event_count_before = len(load_events(connection))
    posting = build_postings([posting_spec])[0]

    with pytest.raises(ValidationError):
        post_journal_entry(
            connection,
            entry=make_unbalanced_journal_entry(posting),
        )

    assert len(load_events(connection)) == event_count_before


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_generated_posted_entries_keep_expanded_accounting_equation_balanced(
    posting_specs,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    postings = build_postings(posting_specs)

    post_generated_entries(connection, postings)

    left_side, right_side = expanded_accounting_equation(connection)

    assert left_side == right_side