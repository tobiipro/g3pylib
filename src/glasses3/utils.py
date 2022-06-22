from __future__ import annotations

from enum import Enum, auto

from glasses3.g3typing import URI


class APIComponent:
    def __init__(self, api_uri: URI):
        self._api_uri = api_uri

    def generate_endpoint_uri(
        self, endpoint_kind: EndpointKind, endpoint_name: str
    ) -> URI:
        return URI(f"{self._api_uri}{endpoint_kind.uri_delimiter}{endpoint_name}")


class EndpointKind(Enum):
    PROPERTY = auto()
    ACTION = auto()
    SIGNAL = auto()

    @property
    def uri_delimiter(self):
        match self:
            case EndpointKind.PROPERTY:
                return "."
            case EndpointKind.ACTION:
                return "!"
            case EndpointKind.SIGNAL:
                return ":"
