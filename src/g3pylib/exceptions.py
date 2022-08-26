class InvalidResponseError(Exception):
    """Raised when the server responds with an invalid message."""


class FeatureNotAvailableError(Exception):
    """Raised when a requested feature is not available due to improper initialization."""
