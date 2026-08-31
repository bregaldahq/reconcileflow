"""Failures surfaced by application use cases."""

from __future__ import annotations

from dataclasses import dataclass


class ApplicationError(RuntimeError):
    """Base class for expected application failures."""


class NotFoundError(ApplicationError):
    """Requested aggregate does not exist."""


class ConflictError(ApplicationError):
    """Requested action conflicts with aggregate state."""


class AuthorizationError(ApplicationError):
    """Actor is not authorized for the action."""


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    row: int | None = None
    field: str | None = None


class DatasetValidationError(ApplicationError):
    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        super().__init__("a validação da fonte de dados falhou")
        self.issues = issues


class RetryableApplicationError(ApplicationError):
    """Transient failure that a worker may safely retry."""


class PermanentApplicationError(ApplicationError):
    """Permanent failure that must not be retried."""
