"""Property tests for projection replay invariants."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from tests.property.conftest import (
    POSTING_SPECS_STRATEGY,
    account_balance_snapshot,
    build_postings,
    event_snapshot,
    make_connection,
    open_standard_chart,
    post_generated_entries,
    trial_balance_snapshot,
)

from reconcile.projections.rebuild import rebuild_projections
from reconcile.reports.trial_balance import generate_trial_balance


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_rebuilding_generated_posted_entries_restores_same_account_balances(
    posting_specs,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    post_generated_entries(connection, build_postings(posting_specs))

    before_rebuild = account_balance_snapshot(connection)

    rebuild_projections(connection)

    assert account_balance_snapshot(connection) == before_rebuild


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_rebuilding_generated_posted_entries_restores_same_trial_balance(
    posting_specs,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    post_generated_entries(connection, build_postings(posting_specs))

    before_rebuild = trial_balance_snapshot(generate_trial_balance(connection))

    rebuild_projections(connection)

    after_rebuild = trial_balance_snapshot(generate_trial_balance(connection))
    assert after_rebuild == before_rebuild


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_rebuilding_generated_posted_entries_does_not_change_event_count(
    posting_specs,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    post_generated_entries(connection, build_postings(posting_specs))

    events_before = event_snapshot(connection)

    rebuild_projections(connection)

    events_after = event_snapshot(connection)
    assert len(events_after) == len(events_before)


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_rebuilding_generated_posted_entries_does_not_change_event_ids(
    posting_specs,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    post_generated_entries(connection, build_postings(posting_specs))

    event_ids_before = [event["event_id"] for event in event_snapshot(connection)]

    rebuild_projections(connection)

    event_ids_after = [event["event_id"] for event in event_snapshot(connection)]
    assert event_ids_after == event_ids_before


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_rebuilding_generated_posted_entries_does_not_change_event_sequences(
    posting_specs,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    post_generated_entries(connection, build_postings(posting_specs))

    sequences_before = [
        event["event_sequence"] for event in event_snapshot(connection)
    ]

    rebuild_projections(connection)

    sequences_after = [
        event["event_sequence"] for event in event_snapshot(connection)
    ]
    assert sequences_after == sequences_before


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_running_rebuild_twice_is_deterministic(posting_specs, tmp_path):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    post_generated_entries(connection, build_postings(posting_specs))

    rebuild_projections(connection)
    first_rebuild_balances = account_balance_snapshot(connection)
    first_rebuild_trial_balance = trial_balance_snapshot(
        generate_trial_balance(connection)
    )

    rebuild_projections(connection)
    second_rebuild_balances = account_balance_snapshot(connection)
    second_rebuild_trial_balance = trial_balance_snapshot(
        generate_trial_balance(connection)
    )

    assert second_rebuild_balances == first_rebuild_balances
    assert second_rebuild_trial_balance == first_rebuild_trial_balance


@given(posting_specs=POSTING_SPECS_STRATEGY)
@settings(
    max_examples=25,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_generated_event_replay_is_deterministic_when_ordered_by_sequence(
    posting_specs,
    tmp_path,
):
    connection = make_connection(tmp_path)
    open_standard_chart(connection)
    post_generated_entries(connection, build_postings(posting_specs))

    rebuild_projections(connection)
    first_event_snapshot = event_snapshot(connection)
    first_balance_snapshot = account_balance_snapshot(connection)

    rebuild_projections(connection)
    second_event_snapshot = event_snapshot(connection)
    second_balance_snapshot = account_balance_snapshot(connection)

    assert second_event_snapshot == first_event_snapshot
    assert second_balance_snapshot == first_balance_snapshot