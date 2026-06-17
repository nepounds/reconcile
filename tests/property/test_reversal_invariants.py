"""Property tests for journal reversal invariants."""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from tests.property.conftest import (
    POSTING_SPEC_STRATEGY,
    POSTING_SPECS_STRATEGY,
    account_balance_snapshot,
    build_postings,
    journal_entry_snapshot,
    make_connection,
    open_standard_chart,
    post_generated_entries,
)

from reconcile.exceptions import ValidationError
from reconcile.journal.service import reverse_journal_entry
from reconcile.projections.rebuild import rebuild_projections
from reconcile.reports.trial_balance import generate_trial_balance


@given(posting_spec=POSTING_SPEC_STRATEGY)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_reversing_generated_posted_entry_removes_net_account_balance_impact(
    posting_spec,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    posting = build_postings([posting_spec])[0]
    post_generated_entries(connection, [posting])

    reverse_journal_entry(
        connection,
        posting.journal_entry_id,
        reversal_entry_id=f"rev-{posting.journal_entry_id}",
    )

    balances = account_balance_snapshot(connection)

    assert all(row["balance_cents"] == 0 for row in balances)


@given(posting_spec=POSTING_SPEC_STRATEGY)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_reversal_preserves_activity_totals_by_adding_opposite_side_activity(
    posting_spec,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    posting = build_postings([posting_spec])[0]
    post_generated_entries(connection, [posting])

    reverse_journal_entry(
        connection,
        posting.journal_entry_id,
        reversal_entry_id=f"rev-{posting.journal_entry_id}",
    )

    balances_by_account = {
        row["account_id"]: row for row in account_balance_snapshot(connection)
    }

    debit_account = balances_by_account[posting.debit_account_id]
    credit_account = balances_by_account[posting.credit_account_id]

    assert debit_account["debit_total_cents"] == posting.amount_cents
    assert debit_account["credit_total_cents"] == posting.amount_cents
    assert credit_account["debit_total_cents"] == posting.amount_cents
    assert credit_account["credit_total_cents"] == posting.amount_cents


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_reversing_generated_posted_entries_keeps_trial_balance_balanced(
    posting_specs,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    postings = build_postings(posting_specs)
    post_generated_entries(connection, postings)

    for posting in postings:
        reverse_journal_entry(
            connection,
            posting.journal_entry_id,
            reversal_entry_id=f"rev-{posting.journal_entry_id}",
        )

    rows = generate_trial_balance(connection)
    total_ending_debits = sum(row["ending_debit_balance_cents"] for row in rows)
    total_ending_credits = sum(
        row["ending_credit_balance_cents"] for row in rows
    )

    assert total_ending_debits == total_ending_credits


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_rebuilding_after_generated_reversals_restores_incremental_balances(
    posting_specs,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    postings = build_postings(posting_specs)
    post_generated_entries(connection, postings)

    for posting in postings:
        reverse_journal_entry(
            connection,
            posting.journal_entry_id,
            reversal_entry_id=f"rev-{posting.journal_entry_id}",
        )

    incremental_balances = account_balance_snapshot(connection)

    rebuild_projections(connection)

    assert account_balance_snapshot(connection) == incremental_balances


@given(posting_spec=POSTING_SPEC_STRATEGY)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_reversing_any_valid_generated_entry_creates_linked_reversal_entry(
    posting_spec,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    posting = build_postings([posting_spec])[0]
    reversal_entry_id = f"rev-{posting.journal_entry_id}"
    post_generated_entries(connection, [posting])

    reverse_journal_entry(
        connection,
        posting.journal_entry_id,
        reversal_entry_id=reversal_entry_id,
    )

    entries = {
        row["journal_entry_id"]: row for row in journal_entry_snapshot(connection)
    }

    assert reversal_entry_id in entries
    assert entries[posting.journal_entry_id]["reversed_by_entry_id"] == (
        reversal_entry_id
    )
    assert entries[reversal_entry_id]["reversal_of_entry_id"] == (
        posting.journal_entry_id
    )


@given(posting_spec=POSTING_SPEC_STRATEGY)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_original_entries_are_preserved_after_generated_reversals(
    posting_spec,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    posting = build_postings([posting_spec])[0]
    post_generated_entries(connection, [posting])

    reverse_journal_entry(
        connection,
        posting.journal_entry_id,
        reversal_entry_id=f"rev-{posting.journal_entry_id}",
    )

    original = connection.execute(
        """
        SELECT journal_entry_id, status
        FROM journal_entries
        WHERE journal_entry_id = ?
        """,
        (posting.journal_entry_id,),
    ).fetchone()

    original_lines = connection.execute(
        """
        SELECT side, amount_cents
        FROM journal_entry_lines
        WHERE journal_entry_id = ?
        ORDER BY line_number
        """,
        (posting.journal_entry_id,),
    ).fetchall()

    assert original is not None
    assert original["status"] == "posted"
    assert [row["side"] for row in original_lines] == ["debit", "credit"]
    assert [row["amount_cents"] for row in original_lines] == [
        posting.amount_cents,
        posting.amount_cents,
    ]


@given(posting_spec=POSTING_SPEC_STRATEGY)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_generated_reversal_entries_point_back_to_original_entry(
    posting_spec,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    posting = build_postings([posting_spec])[0]
    reversal_entry_id = f"rev-{posting.journal_entry_id}"
    post_generated_entries(connection, [posting])

    reverse_journal_entry(
        connection,
        posting.journal_entry_id,
        reversal_entry_id=reversal_entry_id,
    )

    reversal = connection.execute(
        """
        SELECT reversal_of_entry_id
        FROM journal_entries
        WHERE journal_entry_id = ?
        """,
        (reversal_entry_id,),
    ).fetchone()

    assert reversal is not None
    assert reversal["reversal_of_entry_id"] == posting.journal_entry_id


@given(posting_spec=POSTING_SPEC_STRATEGY)
@settings(
    max_examples=30,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_attempting_to_reverse_same_generated_entry_twice_raises_validation_error(
    posting_spec,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    posting = build_postings([posting_spec])[0]
    post_generated_entries(connection, [posting])

    reverse_journal_entry(
        connection,
        posting.journal_entry_id,
        reversal_entry_id=f"rev-{posting.journal_entry_id}",
    )

    with pytest.raises(ValidationError):
        reverse_journal_entry(
            connection,
            posting.journal_entry_id,
            reversal_entry_id=f"rev-again-{posting.journal_entry_id}",
        )