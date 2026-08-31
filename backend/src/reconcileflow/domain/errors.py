"""Domain-specific failures with no transport concerns."""


class DomainError(ValueError):
    """Base class for invalid domain input or state."""


class MonetaryFloatError(DomainError):
    """Raised when binary floating point reaches monetary logic."""


class InvalidTransitionError(DomainError):
    """Raised when a run lifecycle transition is not permitted."""


class NormalizationError(DomainError):
    """Raised when source data cannot be normalized without guessing."""
