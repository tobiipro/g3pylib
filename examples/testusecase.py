import websockets
from glasses3.websocket import G3WebSocketClientProtocol, connect
import json
import asyncio


class G3:
    recorder = '{"path":"/recorder","id":42,"method":"GET"}'
    
class Recorder:
    def start():
        pass

async def handler():
    # print('print:', getattr(await G3WebSocketClientProtocol.connect('tg02b-080105022801'), '__aenter__'))
    async with websockets.connect('ws://tg02b-080105022801/websockets', create_protocol=G3WebSocketClientProtocol) as ws:
        await ws.send(G3.recorder)
        answer = await ws.recv()
        print(json.dumps(json.loads(answer), indent=2))
    async with connect('tg02b-080105022801') as g3ws:
        await g3ws.send(G3.recorder)
        answer = await g3ws.recv()
        print(json.dumps(json.loads(answer), indent=2))


def main():
    asyncio.run(handler())


if __name__ == '__main__':
    main()