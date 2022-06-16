import asyncio
import json
import logging
from typing import cast

from websockets.client import connect as websockets_connect

import glasses3.websocket as g3_websocket
from glasses3 import Glasses3
from glasses3.g3typing import Hostname, UriPath

logging.basicConfig(level=logging.DEBUG)

g3_hostname = Hostname("tg03b-080200045321")
test_request = {"path": "/recorder", "method": "GET"}
test_request_path = UriPath("/recorder")
test_request_params = {"help": True}


async def use_case_1():
    async with g3_websocket.connect(g3_hostname) as g3ws:
        g3ws = cast(g3_websocket.G3WebSocketClientProtocol, g3ws)
        g3ws.start_receiver_task()
        response = await g3ws.require(test_request)
        response2 = await g3ws.require(test_request)
        print("uc1-r1", response)
        print("uc1-r2", response2)


async def use_case_2():
    async with websockets_connect(
        "ws://{}/websockets".format(g3_hostname),
        create_protocol=g3_websocket.G3WebSocketClientProtocol.factory,
    ) as g3ws:
        g3ws = cast(g3_websocket.G3WebSocketClientProtocol, g3ws)
        g3ws.start_receiver_task()
        response = await g3ws.require(test_request)
        response2 = await g3ws.require(test_request)
        print("uc2-r1", response)
        print("uc2-r2", response2)


async def use_case_3():
    async with g3_websocket.connect(g3_hostname) as g3ws:
        g3ws = cast(g3_websocket.G3WebSocketClientProtocol, g3ws)
        g3ws.start_receiver_task()
        response = await g3ws.require_get(test_request_path)
        print("uc3-r1", json.dumps(response, indent=2))


async def use_case_4():
    raise NotImplementedError
    g3_list = Glasses3.find()
    async with g3_list[0] as g3:
        recorder = g3.get_recorder()
        recorder.prop1
        await recorder.start()


async def use_case_5():
    async with Glasses3.connect(g3_hostname) as g3:
        print(g3.recorder)


async def use_case_signal():
    async with g3_websocket.connect(g3_hostname) as g3ws:
        g3ws = cast(g3_websocket.G3WebSocketClientProtocol, g3ws)
        g3ws.start_receiver_task()
        queue1, unsubscribe1 = await g3ws.subscribe_to_signal(
            UriPath("/recorder:started")
        )
        queue2, unsubscribe2 = await g3ws.subscribe_to_signal(
            UriPath("/recorder:started")
        )
        await unsubscribe1()
        logging.info(await queue2.get())
        await unsubscribe2()
        logging.info(await queue1.get())


async def handler():
    await asyncio.gather(use_case_signal())


def main():
    asyncio.run(handler())


if __name__ == "__main__":
    main()
