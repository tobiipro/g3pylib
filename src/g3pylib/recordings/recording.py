import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, cast

import aiohttp

from g3pylib._utils import APIComponent, EndpointKind
from g3pylib.exceptions import FeatureNotAvailableError, InvalidResponseError
from g3pylib.g3typing import URI
from g3pylib.websocket import G3WebSocketClientProtocol


class Recording(APIComponent):
    def __init__(
        self,
        connection: G3WebSocketClientProtocol,
        api_base_uri: URI,
        uuid: str,
        http_url: Optional[str],
    ):
        self._connection = connection
        self._http_url = http_url
        self._uuid = uuid
        self.logger: logging.Logger = logging.getLogger(__name__)
        super().__init__(URI(f"{api_base_uri}/{uuid}"))

    async def get_created(self) -> datetime:
        created = cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "created")
            ),
        )
        return datetime.fromisoformat(created.strip("Z"))

    async def get_duration(self) -> Optional[timedelta]:
        duration = cast(
            float,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "duration")
            ),
        )
        if duration == -1:
            return None
        return timedelta(seconds=duration)

    async def get_folder(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "folder")
            ),
        )

    async def get_gaze_overlay(self) -> bool:
        return cast(
            bool,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "gaze-overlay")
            ),
        )

    async def get_gaze_samples(self) -> Optional[int]:
        gaze_samples = cast(
            int,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "gaze-samples")
            ),
        )
        if gaze_samples == -1:
            return None
        return gaze_samples

    async def get_http_path(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "http-path")
            ),
        )

    async def get_name(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "name")
            ),
        )

    async def get_rtsp_path(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "rtsp-path")
            ),
        )

    async def get_timezone(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "timezone")
            ),
        )

    async def get_valid_gaze_samples(self) -> Optional[int]:
        valid_gaze_samples = cast(
            int,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "valid-gaze-samples")
            ),
        )
        if valid_gaze_samples == -1:
            return None
        return valid_gaze_samples

    async def get_visible_name(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "visible-name")
            ),
        )

    async def set_visible_name(self, value: str) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "visible-name"),
                body=value,
            ),
        )

    async def meta_insert(self, key: str, meta: Optional[str]) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "meta-insert"),
                body=[key, meta],
            ),
        )

    async def meta_keys(self) -> List[str]:
        return cast(
            List[str],
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "meta-keys")
            ),
        )

    async def meta_lookup(self, key: str) -> str:
        return cast(
            str,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "meta-lookup"),
                body=[key],
            ),
        )

    async def move(self, folder: str) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "move"), body=[folder]
            ),
        )

    @property
    def uuid(self) -> str:
        """The uuid of the recording."""
        return self._uuid

    async def get_scenevideo_url(self) -> str:
        """Returns a URL to the recording's video file."""
        if self._http_url is None:
            raise FeatureNotAvailableError(
                "This Glasses3 object was initialized without a proper HTTP url."
            )
        data_url = f"{self._http_url}{await self.get_http_path()}"
        async with aiohttp.ClientSession() as session:
            async with session.get(data_url) as response:
                data = json.loads(await response.text())
        try:
            scenevideo_file_name = data["scenecamera"]["file"]
        except KeyError:
            self.logger.warning(
                f"Could not retrieve file name for recording from recording data collected from {data_url}."
            )
            raise InvalidResponseError
        return f"{data_url}/{scenevideo_file_name}"

    async def get_gazedata_url(self) -> str:
        """Returns a URL to the recording's decompressed gaze data file."""
        if self._http_url is None:
            raise FeatureNotAvailableError(
                "This Glasses3 object was initialized without a proper HTTP url."
            )
        data_url = f"{self._http_url}{await self.get_http_path()}"
        async with aiohttp.ClientSession() as session:
            async with session.get(data_url) as response:
                data = json.loads(await response.text())
        try:
            gaze_file_name = data["gaze"]["file"]
        except KeyError:
            self.logger.warning(
                f"Could not retrieve file name for gaze data from recording data collected from {data_url}."
            )
            raise InvalidResponseError
        return f"{data_url}/{gaze_file_name}?use-content-encoding=true"
