import asyncio
from typing import Awaitable, Tuple, cast

from g3pylib._utils import APIComponent, EndpointKind
from g3pylib.g3typing import URI, SignalBody
from g3pylib.websocket import G3WebSocketClientProtocol


class Calibrate(APIComponent):
    def __init__(self, connection: G3WebSocketClientProtocol, api_uri: URI) -> None:
        self._connection = connection
        super().__init__(api_uri)

    async def get_name(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "name")
            ),
        )

    async def emit_markers(self) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "emit-markers")
            ),
        )

    async def run(self) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "run")
            ),
        )

    async def subscribe_to_marker(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "marker")
        )
