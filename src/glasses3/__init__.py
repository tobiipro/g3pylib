from __future__ import annotations
from typing import AsyncIterator, cast
from contextlib import asynccontextmanager
from .recorder import Recorder
import glasses3.websocket
from .websocket import G3WebSocketClientProtocol
from contextlib import asynccontextmanager


class Glasses3:
    def __init__(self, connection) -> None:
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
