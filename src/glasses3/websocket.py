import websockets
import websockets.client


def connect(g3_hostname, wspath="/websocket"):
    ws_uri = "ws://{}{}".format(g3_hostname, wspath)
    return websockets.connect(ws_uri, create_protocol=G3WebSocketClientProtocol, subprotocols=G3WebSocketClientProtocol.DEFAULT_SUBPROTOCOLS)

class G3WebSocketClientProtocol(websockets.client.WebSocketClientProtocol):
    DEFAULT_SUBPROTOCOLS = ['g3api']

    def __init__(self, subprotocols, **kwargs):
        self._message_count = 0
        self._signals_map = {}
        self._message_map = {}
        if not subprotocols:
            subprotocols = self.DEFAULT_SUBPROTOCOLS
        super().__init__(subprotocols=subprotocols, **kwargs)
     