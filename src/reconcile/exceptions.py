"""Custom exception types for Reconcile."""


class ReconcileError(Exception):
    """Base exception for Reconcile errors."""


class ValidationError(ReconcileError):
    """Raised when project data fails validation."""


class MoneyError(ValidationError):
    """Raised when money parsing or formatting fails."""
