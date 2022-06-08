import asyncio
from cProfile import run
import json
import websockets

class G3Websocket:


    def __init__(self, g3hostname, wspath="/websocket"):
        self.wsurl = "ws://{}{}".format(g3hostname, wspath)
        self._msgid = 0
        self.sigs = {}
        self.ids = {}

    async def __aenter__(self):
        self._conn = websockets.connect(self.wsurl, subprotocols=["g3api"])
        self._ws = await self._conn.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs):
        await self._conn.__aexit__(*args, **kwargs)


class Glasses3:
    pass    

async def handler():
    async with G3Websocket('tg02b-080105022801') as websocket:
        await websocket._ws.send('{"path":"/webrtc","id":42,"method":"GET","params":{"help":true}}')
        answer = await websocket._ws.recv()
        
        print(json.dumps(json.loads(answer), indent=2))


def main():
    asyncio.run(handler())


if __name__ == '__main__':
    main()