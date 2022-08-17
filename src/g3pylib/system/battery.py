import asyncio
from enum import Enum
from typing import Awaitable, Tuple, cast

from g3pylib._utils import APIComponent, EndpointKind
from g3pylib.g3typing import URI, SignalBody
from g3pylib.websocket import G3WebSocketClientProtocol


class BatteryState(Enum):
    """Defines battery levels."""

    FULL = "full"
    GOOD = "good"
    LOW = "low"
    VERY_LOW = "verylow"
    UNKNOWN = "unknown"


class Battery(APIComponent):
    def __init__(self, connection: G3WebSocketClientProtocol, api_uri: URI) -> None:
        self._connection = connection
        super().__init__(api_uri)

    async def get_charging(self) -> bool:
        return cast(
            bool,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "charging")
            ),
        )

    async def get_level(self) -> float:
        return cast(
            float,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "level")
            ),
        )

    async def get_name(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "name")
            ),
        )

    async def get_remaining_time(self) -> int:
        return cast(
            int,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "remaining-time")
            ),
        )

    async def get_state(self) -> BatteryState:
        return BatteryState(
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "state")
            ),
        )

    async def subscribe_to_state_changed(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "state-changed")
        )
