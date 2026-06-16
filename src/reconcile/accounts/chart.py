"""Chart-of-accounts helpers.

Step 7 keeps this intentionally small. CSV chart loading and demo seeding are
future work.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

from reconcile.accounts.models import Account
from reconcile.accounts.service import open_account


def open_accounts(
    connection: sqlite3.Connection,
    accounts: Iterable[Account],
    *,
    source: str = "manual",
) -> list[Account]:
    """Open multiple accounts through the account-opening service."""
    return [open_account(connection, account, source=source) for account in accounts]
