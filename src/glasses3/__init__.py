from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from enum import Enum, auto
from typing import AsyncIterator, Optional, cast

import glasses3.websocket
from glasses3.recordings import Recordings

from .g3typing import URI, Hostname, LoggerLike
from .recorder import Recorder
from .websocket import G3WebSocketClientProtocol


class Glasses3:
    def __init__(
        # Type ignored in this file since LoggerAdapter does not support generic typing
        self,
        connection: G3WebSocketClientProtocol,
        logger: Optional[LoggerLike] = None,
    ) -> None:
        self.logger = logging.getLogger(__name__) if logger is None else logger
        self._connection: G3WebSocketClientProtocol = connection
        self._recorder: Optional[Recorder] = None
        self._recordings: Optional[Recordings] = None

    @property
    def recorder(self):
        if self._recorder is None:
            self._recorder = Recorder(self._connection, URI("recorder"))
        return self._recorder

    @property
    def recordings(self):
        if self._recordings is None:
            self._recordings = Recordings(self._connection, URI("/recordings"))
        return self._recordings

    @classmethod
    @asynccontextmanager
    async def connect(cls, g3_hostname: Hostname) -> AsyncIterator[Glasses3]:
        async with glasses3.websocket.connect(g3_hostname) as g3:
            g3 = cast(G3WebSocketClientProtocol, g3)
            g3.start_receiver_task()
            yield cls(g3)


class APIComponent:
    def __init__(self, api_uri: URI):
        self._api_uri = api_uri

    def generate_endpoint_uri(
        self, endpoint_kind: EndpointKind, endpoint_name: str
    ) -> URI:
        return URI(f"/{self._api_uri}{endpoint_kind.uri_delimiter}{endpoint_name}")


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
