"""Thin script wrapper for the Reconcile CLI."""

from __future__ import annotations

from reconcile.cli import main

if __name__ == "__main__":
    raise SystemExit(main())