from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Type

import websockets
import websockets.client
import websockets.legacy.client
from websockets.client import connect as websockets_connect
from websockets.typing import Subprotocol


def connect(g3_hostname, wspath="/websocket") -> websockets.legacy.client.Connect:
    ws_uri = "ws://{}{}".format(g3_hostname, wspath)
    return websockets_connect(
        ws_uri,
        create_protocol=G3WebSocketClientProtocol.factory,
        subprotocols=G3WebSocketClientProtocol.DEFAULT_SUBPROTOCOLS,
    )


class G3WebSocketClientProtocol(websockets.client.WebSocketClientProtocol):
    DEFAULT_SUBPROTOCOLS = [Subprotocol("g3api")]

    def __init__(self, *, subprotocols=None, **kwargs):
        self.g3_logger = logging.getLogger(__name__)
        self._message_count = 0
        self._future_messages = {}
        self._signals_map = {}
        self._event_loop = asyncio.get_running_loop()
        if subprotocols is None:
            subprotocols = self.DEFAULT_SUBPROTOCOLS
        super().__init__(subprotocols=subprotocols, **kwargs)

    @classmethod
    def factory(
        cls: Type[G3WebSocketClientProtocol], *args, **kwargs
    ) -> G3WebSocketClientProtocol:
        return cls(*args, **kwargs)

    def start_receiver_task(self) -> None:
        self.logger.debug("Receiver task starting")
        self._receiver = asyncio.create_task(self._receiver_task(), name="g3_receiver")

    async def _receiver_task(self) -> None:
        async for message in self:
            json_message = json.loads(message)
            self._future_messages[json_message["id"]].set_result(json_message)

    async def require(self, request: Dict) -> Dict:
        self._message_count += 1
        request["id"] = self._message_count
        string_request_with_id = json.dumps(request)
        await self.send(string_request_with_id)
        future = self._future_messages[
            self._message_count
        ] = self._event_loop.create_future()
        return await future

    async def require_get(self, path, params=None) -> Dict:
        return await self.require(self.generate_get_request(path, params))

    async def require_post(self, path, body=None) -> Dict:
        return await self.require(self.generate_post_request(path, body))

    @staticmethod
    def generate_get_request(path, params=None) -> Dict:
        request = {"path": path, "method": "GET"}
        if params is not None:
            request["params"] = params
        return request

    @staticmethod
    def generate_post_request(path, body=None) -> Dict:
        return {"path": path, "method": "POST", "body": body}
