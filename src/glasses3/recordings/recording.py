from glasses3.g3typing import URI
from glasses3.utils import APIComponent
from glasses3.websocket import G3WebSocketClientProtocol


class Recording(APIComponent):
    def __init__(
        self, connection: G3WebSocketClientProtocol, api_base_uri: URI, uuid: str
    ):
        self._connection = connection
        self._uuid = uuid
        super().__init__(URI(f"{api_base_uri}/{uuid}"))

    @property
    def uuid(self):
        return self._uuid
