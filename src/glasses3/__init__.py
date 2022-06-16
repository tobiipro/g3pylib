from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, Optional, cast

import glasses3.websocket

from .g3typing import Hostname, LoggerLike
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

    @property
    def recorder(self):
        if self._recorder is None:
            self._recorder = Recorder(self._connection)
        return self._recorder

    @classmethod
    @asynccontextmanager
    async def connect(cls, g3_hostname: Hostname) -> AsyncIterator[Glasses3]:
        async with glasses3.websocket.connect(g3_hostname) as g3:
            g3 = cast(G3WebSocketClientProtocol, g3)
            g3.start_receiver_task()
            yield cls(g3)
