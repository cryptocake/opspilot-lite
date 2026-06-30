class OpsPilotError(Exception):
    """Base exception for domain-level workflow errors."""


class NotFoundError(OpsPilotError):
    """Raised when a requested domain object does not exist."""


class InvalidStateError(OpsPilotError):
    """Raised when a workflow transition is not allowed."""


class ConfigurationError(OpsPilotError):
    """Raised when runtime configuration is incomplete or invalid."""


class LLMError(OpsPilotError):
    """Raised when an LLM provider returns an unusable or malformed response."""
