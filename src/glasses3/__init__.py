"""This is the g3pylib package root."""
from __future__ import annotations

__version__ = "0.1.0-alpha"

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, cast

import glasses3.websocket
from glasses3.g3typing import URI, Hostname, LoggerLike
from glasses3.recorder import Recorder
from glasses3.recordings import Recordings
from glasses3.rudimentary import Rudimentary
from glasses3.system import System
from glasses3.utils import APIComponent
from glasses3.websocket import G3WebSocketClientProtocol


class Glasses3(APIComponent):
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
        self._rudimentary: Optional[Rudimentary] = None
        self._system: Optional[System] = None

    @property
    def recorder(self):
        if self._recorder is None:
            self._recorder = Recorder(self._connection, URI("/recorder"))
        return self._recorder

    @property
    def recordings(self):
        if self._recordings is None:
            self._recordings = Recordings(self._connection, URI("/recordings"))
        return self._recordings

    @property
    def rudimentary(self):
        if self._rudimentary is None:
            self._rudimentary = Rudimentary(self._connection, URI("/rudimentary"))
        return self._rudimentary

    @property
    def system(self):
        if self._system is None:
            self._system = System(self._connection, URI("/system"))
        return self._system

    @classmethod
    @asynccontextmanager
    async def connect(cls, g3_hostname: Hostname) -> AsyncIterator[Glasses3]:
        async with glasses3.websocket.connect(g3_hostname) as g3:
            g3 = cast(G3WebSocketClientProtocol, g3)
            g3.start_receiver_task()
            yield cls(g3)
