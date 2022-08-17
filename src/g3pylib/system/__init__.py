from datetime import datetime
from typing import List, Optional, cast

from g3pylib._utils import APIComponent, EndpointKind
from g3pylib.g3typing import URI
from g3pylib.system.battery import Battery
from g3pylib.websocket import G3WebSocketClientProtocol


class System(APIComponent):
    def __init__(self, connection: G3WebSocketClientProtocol, api_uri: URI) -> None:
        self._connection = connection
        self._battery: Optional[Battery] = None
        super().__init__(api_uri)

    @property
    def battery(self) -> Battery:
        if self._battery is None:
            self._battery = Battery(self._connection, URI(self._api_uri + "/battery"))
        return self._battery

    async def get_head_unit_serial(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "head-unit-serial")
            ),
        )

    async def get_name(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "name")
            ),
        )

    async def get_ntp_is_enabled(self) -> bool:
        return cast(
            bool,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "ntp-is-enabled")
            ),
        )

    async def get_ntp_is_synchronized(self) -> bool:
        return cast(
            bool,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "ntp-is-synchronized")
            ),
        )

    async def get_recording_unit_serial(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(
                    EndpointKind.PROPERTY, "recording-unit-serial"
                )
            ),
        )

    async def get_time(self) -> datetime:
        date_time = cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "time")
            ),
        )
        return datetime.fromisoformat(date_time.strip("Z"))

    async def get_timezone(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "timezone")
            ),
        )

    async def get_version(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "version")
            ),
        )

    async def available_gaze_frequencies(self) -> List[int]:
        return cast(
            List[int],
            await self._connection.require_post(
                self.generate_endpoint_uri(
                    EndpointKind.ACTION, "available-gaze-frequencies"
                )
            ),
        )

    async def set_time(self, value: datetime) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "set-time"),
                body=[f"{datetime.isoformat(value)}Z"],
            ),
        )

    async def set_timezone(self, value: str) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "set-timezone"),
                body=[value],
            ),
        )

    async def use_ntp(self, value: bool) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "use-ntp"), body=[value]
            ),
        )
