import asyncio
import json
import websockets
import websockets.client


def connect(g3_hostname, wspath="/websocket"):
    ws_uri = "ws://{}{}".format(g3_hostname, wspath)
    return websockets.connect(
        ws_uri,
        create_protocol=G3WebSocketClientProtocol,
        subprotocols=G3WebSocketClientProtocol.DEFAULT_SUBPROTOCOLS,
    )


class G3WebSocketClientProtocol(websockets.client.WebSocketClientProtocol):
    DEFAULT_SUBPROTOCOLS = ["g3api"]

    def __init__(self, *, subprotocols=None, **kwargs):
        self._message_count = 0
        self._message_map = {}
        self._signals_map = {}
        self._event_loop = asyncio.get_running_loop()
        if not subprotocols:
            subprotocols = self.DEFAULT_SUBPROTOCOLS
        super().__init__(subprotocols=subprotocols, **kwargs)

    def start_receiver_task(self):
        self._receiver = asyncio.create_task(self._receiver_task())

    async def _receiver_task(self):
        async for message in self:
            json_message = json.loads(message)
            self._message_map[json_message["id"]].set_result(json_message)

    async def require(self, request):
        self._message_count += 1
        json_request = json.loads(request)
        json_request["id"] = self._message_count
        updated_request = json.dumps(json_request)
        await self.send(updated_request)
        future = self._message_map[
            self._message_count
        ] = self._event_loop.create_future()
        return await future
