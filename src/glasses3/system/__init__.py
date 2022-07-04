from typing import Optional, cast

from glasses3.g3typing import URI
from glasses3.system.battery import Battery
from glasses3.utils import APIComponent, EndpointKind
from glasses3.websocket import G3WebSocketClientProtocol


class System(APIComponent):
    def __init__(self, connection: G3WebSocketClientProtocol, api_uri: URI) -> None:
        self._connection = connection
        self._battery: Optional[Battery] = None
        super().__init__(api_uri)

    @property
    def battery(self):
        if self._battery is None:
            self._battery = Battery(self._connection, URI(self._api_uri + "/battery"))
        return self._battery

    async def get_name(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "name")
            ),
        )
