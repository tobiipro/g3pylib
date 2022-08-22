class SubscribeError(Exception):
    """Raised when subscribing to a signal is unsuccessful."""


class UnsubscribeError(Exception):
    """Raised when unsubscribing to a signal is unsuccessful."""


class GlassesError(Exception):
    """Raised when the glasses responds with an error websocket message."""

    error_code: int
    """The received error code."""

    def __init__(self, message: str, error_code: int) -> None:
        self.error_code = error_code
        super().__init__(message)
