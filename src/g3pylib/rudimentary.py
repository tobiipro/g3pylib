import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Awaitable, Tuple, cast

from g3pylib import _utils
from g3pylib._utils import APIComponent, EndpointKind
from g3pylib.g3typing import URI, JSONObject, SignalBody
from g3pylib.websocket import G3WebSocketClientProtocol


class Rudimentary(APIComponent):
    def __init__(self, connection: G3WebSocketClientProtocol, api_uri: URI) -> None:
        self._connection = connection
        self._streams_started = asyncio.Event()
        self.logger: logging.Logger = logging.getLogger(__name__)
        self._keepalive_task = None
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

    async def get_name(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "name")
            ),
        )

    async def get_scene_quality(self) -> int:
        return cast(
            int,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "scene-quality")
            ),
        )

    async def set_scene_quality(self, value: int) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "scene-quality"),
                body=value,
            ),
        )

    async def get_scene_scale(self) -> int:
        return cast(
            int,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "scene-scale")
            ),
        )

    async def set_scene_scale(self, value: int) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "scene-scale"),
                body=value,
            ),
        )

    async def get_sync_port_sample(self) -> JSONObject:
        return await self._connection.require_get(
            self.generate_endpoint_uri(EndpointKind.PROPERTY, "sync-port-sample")
        )

    async def start_streams(self) -> None:
        async def keepalive_task():
            while True:
                self.logger.info("Sending keepalive")
                success = await self.keepalive()
                self._streams_started.set()
                if not success:
                    raise asyncio.CancelledError(
                        "The Glasses rudimentary streams did not want to stay alive"
                    )
                await asyncio.sleep(5)

        self._keepalive_task = _utils.create_task(keepalive_task(), name="keepalive")
        await self._streams_started.wait()

    async def stop_streams(self) -> None:
        if self._keepalive_task is not None:
            self._keepalive_task.cancel()
            try:
                await self._keepalive_task
            except asyncio.CancelledError:
                self.logger.debug("Keepalive task cancelled")
            finally:
                self._streams_started.clear()
                self._keepalive_task = None

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

    @asynccontextmanager
    async def keep_alive_in_context(self):
        """Regularly sends keep alive messages to keep rudimentary streams alive.

        Example usage:
        ```python
        async with g3.rudimentary.keep_alive_in_context():
            for _ in range(100):
                print(await g3.rudimentary.get_gaze_sample())
        ```
        """
        await self.start_streams()
        try:
            yield
        finally:
            await self.stop_streams()
