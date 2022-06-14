from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator, cast

import glasses3.websocket

from .recorder import Recorder
from .websocket import G3WebSocketClientProtocol


class Glasses3:
    def __init__(self, connection, logger=None) -> None:
        self.logger = logging.getLogger(__name__) if logger is None else logger
        self._connection: G3WebSocketClientProtocol = connection

    @classmethod
    @asynccontextmanager
    async def connect(cls, g3_hostname) -> AsyncIterator[Glasses3]:
        async with glasses3.websocket.connect(g3_hostname) as g3:
            g3 = cast(G3WebSocketClientProtocol, g3)
            g3.start_receiver_task()
            yield cls(g3)

    async def get_recorder(self) -> Recorder:
        return await self._connection.require_get("/recorder")
