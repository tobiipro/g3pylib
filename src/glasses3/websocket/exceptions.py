class UnsubscribeError(Exception):
    """Raised when unsubscribing to a signal is unsuccessful."""


class InvalidResponseError(Exception):
    """Raised when the server responds with an invalid message."""
