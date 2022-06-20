import asyncio
from typing import Awaitable, List, Optional, Tuple, cast

from glasses3.g3typing import JSONObject, SignalBody, UriPath
from glasses3.websocket import G3WebSocketClientProtocol


class Recorder:
    def __init__(self, connection: G3WebSocketClientProtocol) -> None:
        self._connection = connection

    async def get_created(self) -> JSONObject:
        return await self._connection.require_get(UriPath("/recorder.created"))

    async def get_current_gaze_frequency(self) -> JSONObject:
        return await self._connection.require_get(
            UriPath("/recorder.current-gaze-frequency")
        )

    async def get_duration(self) -> JSONObject:
        return await self._connection.require_get(UriPath("/recorder.duration"))

    async def get_folder(self) -> JSONObject:
        return await self._connection.require_get(UriPath("/recorder.folder"))

    # async def set_folder(self):

    async def get_gaze_overlay(self) -> JSONObject:
        return await self._connection.require_get(UriPath("/recorder.gaze-overlay"))

    async def get_gaze_samples(self) -> JSONObject:
        return await self._connection.require_get(UriPath("/recorder.gaze-samples"))

    async def get_name(self) -> JSONObject:
        return await self._connection.require_get(UriPath("/recorder.name"))

    async def get_remaining_time(self) -> JSONObject:
        return await self._connection.require_get(UriPath("/recorder.remaining-time"))

    async def get_timezone(self) -> JSONObject:
        return await self._connection.require_get(UriPath("/recorder.timezone"))

    async def get_uuid(self) -> JSONObject:
        return await self._connection.require_get(UriPath("/recorder.uuid"))

    async def get_valid_gaze_samples(self) -> JSONObject:
        return await self._connection.require_get(
            UriPath("/recorder.valid-gaze-samples")
        )

    async def get_visible_name(self) -> JSONObject:
        return await self._connection.require_get(UriPath("/recorder.visible-name"))

    async def cancel(self):
        await self._connection.require_post(UriPath("/recorder!cancel"), body=[])

    async def meta_insert(self, key: str, meta: str) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                UriPath("/recorder!meta-insert"), body=[key, meta]
            ),
        )

    async def meta_keys(self) -> List[str]:
        return cast(
            List[str],
            await self._connection.require_post(
                UriPath("/recorder!meta-keys"), body=[]
            ),
        )

    async def meta_lookup(self, key: str) -> Optional[str]:
        return cast(
            Optional[str],
            await self._connection.require_post(
                UriPath("/recorder!meta-lookup"), body=[key]
            ),
        )

    async def send_event(self, tag: str, object: JSONObject) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                UriPath("/recorder!send-event"), body=[tag, object]
            ),
        )

    async def snapshot(self) -> bool:
        return cast(
            bool,
            await self._connection.require_post(UriPath("/recorder!snapshot"), body=[]),
        )

    async def start(self) -> bool:
        return cast(
            bool,
            await self._connection.require_post(UriPath("/recorder!start"), body=[]),
        )

    async def stop(self) -> bool:
        return cast(
            bool,
            await self._connection.require_post(UriPath("/recorder!stop"), body=[]),
        )

    async def subscribe_to_started(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(UriPath("/recorder:started"))

    async def subscribe_to_stopped(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(UriPath("/recorder:stopped"))
