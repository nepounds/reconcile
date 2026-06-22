"""Thin script wrapper for rebuilding Reconcile projections."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from reconcile.db import connect, initialize_schema
from reconcile.projections.rebuild import rebuild_projections

LOGGER = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Rebuild Reconcile projections from ledger events."
    )
    parser.add_argument(
        "--db-path",
        default="exports/reconcile.db",
        help="Path to the SQLite database. Defaults to exports/reconcile.db.",
    )
    return parser.parse_args()


def main() -> None:
    """Run the projection rebuild workflow."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)

    args = parse_args()
    db_path = Path(args.db_path)

    with connect(db_path) as connection:
        initialize_schema(connection)
        rebuild_projections(connection)

    LOGGER.info("Projection rebuild complete: %s", db_path)


if __name__ == "__main__":
    main()