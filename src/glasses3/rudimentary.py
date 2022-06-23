import asyncio
from typing import Awaitable, Tuple, cast

from glasses3.g3typing import URI, JSONObject, SignalBody
from glasses3.utils import APIComponent, EndpointKind
from glasses3.websocket import G3WebSocketClientProtocol


class Rudimentary(APIComponent):
    def __init__(self, connection: G3WebSocketClientProtocol, api_uri: URI) -> None:
        self._connection = connection
        super().__init__(api_uri)

    async def get_event_sample(self) -> JSONObject:
        return await self._connection.require_get(
            self.generate_endpoint_uri(EndpointKind.PROPERTY, "event-sample")
        )

    async def get_gaze_sample(self) -> JSONObject:
        return await self._connection.require_get(
            self.generate_endpoint_uri(EndpointKind.PROPERTY, "gaze-sample")
        )

    async def get_imu_sample(self) -> JSONObject:
        return await self._connection.require_get(
            self.generate_endpoint_uri(EndpointKind.PROPERTY, "imu-sample")
        )

    async def get_name(self) -> JSONObject:
        return await self._connection.require_get(
            self.generate_endpoint_uri(EndpointKind.PROPERTY, "name")
        )

    async def get_scene_quality(self) -> JSONObject:
        return await self._connection.require_get(
            self.generate_endpoint_uri(EndpointKind.PROPERTY, "scene-quality")
        )

    async def set_scene_quality(self, value: int) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "scene-quality"),
                body=[value],
            ),
        )

    async def get_scene_scale(self) -> JSONObject:
        return await self._connection.require_get(
            self.generate_endpoint_uri(EndpointKind.PROPERTY, "scene-scale")
        )

    async def set_scene_scale(self, value: int) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "scene-quality"),
                body=[value],
            ),
        )

    async def get_sync_port_sample(self) -> JSONObject:
        return await self._connection.require_get(
            self.generate_endpoint_uri(EndpointKind.PROPERTY, "sync-port-sample")
        )

    def start_streams(self) -> None:
        async def keepalive_task():
            while True:
                success = await self.keepalive()
                if not success:
                    raise asyncio.CancelledError(
                        "The Glasses rudimentary streams did not want to stay alive"
                    )
                await asyncio.sleep(5)

        self._keepalive_task = asyncio.create_task(keepalive_task())

    def stop_streams(self) -> None:
        self._keepalive_task.cancel()

    async def calibrate(self) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "calibrate")
            ),
        )

    async def keepalive(self) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "keepalive")
            ),
        )

    async def send_event(self, tag: str, object: JSONObject) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "send-event"),
                [tag, object],
            ),
        )

    async def subscribe_to_event(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "event")
        )

    async def subscribe_to_gaze(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "gaze")
        )

    async def subscribe_to_imu(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "imu")
        )

    async def subscribe_to_scene(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "scene")
        )

    async def subscribe_to_sync_port(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "sync-port")
        )
