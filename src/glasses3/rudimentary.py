from glasses3 import APIComponent, EndpointKind, G3WebSocketClientProtocol
from glasses3.g3typing import URI, JSONObject


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

    async def set_scene_quality(self) -> bool:
        raise NotImplementedError

    async def get_scene_scale(self) -> JSONObject:
        return await self._connection.require_get(
            self.generate_endpoint_uri(EndpointKind.PROPERTY, "scene-scale")
        )

    async def set_scene_scale(self) -> bool:
        raise NotImplementedError

    async def get_sync_port_sample(self) -> JSONObject:
        return await self._connection.require_get(
            self.generate_endpoint_uri(EndpointKind.PROPERTY, "sync-port-sample")
        )
