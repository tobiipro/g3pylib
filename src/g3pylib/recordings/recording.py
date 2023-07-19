import asyncio
import base64
import json
import logging
import os
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

    async def get_json_data(self) -> str:
        """Returns a JSON string that holds metadata for all of the recording files."""
        if self._http_url is None:
            raise FeatureNotAvailableError(
                "This Glasses3 object was initialized without a proper HTTP url."
            )
        data_url = f"{self._http_url}{await self.get_http_path()}"
        async with aiohttp.ClientSession() as session:
            async with session.get(data_url) as response:
                return await response.text()

    def _get_file_name_from_json_data(
        self, data_str: str, key: str, data_url: str
    ) -> str:
        """Extracts the desired file name from `data_str` collected from `data_url` represented by `key`. `data_url` is used exclusively for the error message."""
        data = json.loads(data_str)
        try:
            file_name = data[key]["file"]
        except KeyError as exc:
            self.logger.warning(
                f"Could not retrieve file name for {key} data from recording data collected from {data_url}."
            )
            raise InvalidResponseError from exc
        return file_name

    async def get_scenevideo_url(self) -> str:
        """Returns a URL to the recording's video file."""
        data_url = f"{self._http_url}{await self.get_http_path()}"
        scenevideo_file_name = self._get_file_name_from_json_data(
            await self.get_json_data(), "scenecamera", data_url
        )
        return f"{data_url}/{scenevideo_file_name}"

    async def get_gazedata_url(self) -> str:
        """Returns a URL to the recording's decompressed gaze data file."""
        data_url = f"{self._http_url}{await self.get_http_path()}"
        gaze_file_name = self._get_file_name_from_json_data(
            await self.get_json_data(), "gaze", data_url
        )
        return f"{data_url}/{gaze_file_name}?use-content-encoding=true"

    async def download_files(self, path: str = ".") -> str:
        """
        Downloads all recording files into one folder under the specified `path`.
        Returns name of the downloaded folder under `path`.
        """
        data_url = f"{self._http_url}{await self.get_http_path()}"
        data_str = await self.get_json_data()
        data_json = json.loads(data_str)

        # workaround for making subsequent aiohttp clientsessions
        # TODO: find a more appropriate solution
        await asyncio.sleep(0.5)

        # create download folder and the meta folder within it
        folder_name = data_json["name"]
        os.makedirs(os.path.join(path, folder_name), exist_ok=True)
        meta_folder_name = data_json["meta-folder"]
        os.makedirs(os.path.join(path, folder_name, meta_folder_name), exist_ok=True)

        # write json data to recording.g3 file
        with open(os.path.join(path, folder_name, "recording.g3"), "w") as f:
            f.write(data_str)

        # generate filenames and file urls
        scenevideo_file_name = self._get_file_name_from_json_data(
            data_str, "scenecamera", data_url
        )
        scenevideo_url = f"{data_url}/{scenevideo_file_name}"

        gazedata_file_name = self._get_file_name_from_json_data(
            data_str, "gaze", data_url
        )
        gazedata_url = f"{data_url}/{gazedata_file_name}"

        eventdata_file_name = self._get_file_name_from_json_data(
            data_str, "events", data_url
        )
        eventdata_url = f"{data_url}/{eventdata_file_name}"

        imudata_file_name = self._get_file_name_from_json_data(
            data_str, "imu", data_url
        )
        imudata_url = f"{data_url}/{imudata_file_name}"

        async with aiohttp.ClientSession() as session:

            async def download(url: str, file_name: str) -> None:
                async with session.get(url) as response:
                    with open(os.path.join(path, folder_name, file_name), "wb") as f:
                        f.write(await response.read())

            async def download_meta(key: str) -> None:
                with open(
                    os.path.join(path, folder_name, meta_folder_name, key), "w"
                ) as f:
                    encoded_value = await self.meta_lookup(key)
                    # decode returned string if it is base64 encoded, otherwise write it raw
                    try:
                        value = base64.b64decode(encoded_value).decode()
                    except ValueError:
                        value = encoded_value
                    f.write(value)

            # get meta keys
            meta_keys = await self.meta_keys()

            # create tasks that download files and meta files
            task_list = [
                download(scenevideo_url, scenevideo_file_name),
                download(gazedata_url, gazedata_file_name),
                download(eventdata_url, eventdata_file_name),
                download(imudata_url, imudata_file_name),
            ] + [download_meta(key) for key in meta_keys]

            await asyncio.gather(*task_list)

        return folder_name
