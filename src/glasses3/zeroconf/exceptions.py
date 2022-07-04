class ServiceDiscoveryError(Exception):
    """Raised when service discovery is unsuccessful."""


class ServiceEventError(Exception):
    """Raised when a service is removed or updated before addition."""
