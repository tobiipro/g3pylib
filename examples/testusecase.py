import websockets
import glasses3.websocket
from glasses3 import Glasses3
import json
import asyncio

g3_hostname = "tg03b-080200045321"
test_request = {"path": "/recorder", "method": "GET"}
test_request_path = "/recorder"
test_request_params = {"help": True}


async def use_case_1():
    async with glasses3.websocket.connect(g3_hostname) as g3ws:
        g3ws.start_receiver_task()
        response = await g3ws.require(test_request)
        response2 = await g3ws.require(test_request)
        print("uc1-r1", json.dumps(response, indent=2))
        print("uc1-r2", json.dumps(response2, indent=2))


async def use_case_2():
    async with websockets.connect(
        "ws://{}/websockets".format(g3_hostname),
        create_protocol=glasses3.websocket.G3WebSocketClientProtocol,
    ) as g3ws:
        g3ws.start_receiver_task()
        response = await g3ws.require(test_request)
        response2 = await g3ws.require(test_request)
        print("uc2-r1", json.dumps(response, indent=2))
        print("uc2-r2", json.dumps(response2, indent=2))


async def use_case_3():
    async with glasses3.websocket.connect(g3_hostname) as g3ws:
        g3ws.start_receiver_task()
        response = await g3ws.require_get(test_request_path)
        print("uc3-r1", json.dumps(response, indent=2))


async def use_case_4():
    g3_list = Glasses3.find()
    async with g3_list[0] as g3:
        recorder = g3.get_recorder()
        recorder.prop1
        await recorder.start()


async def use_case_5():
    async with Glasses3.connect(g3_hostname) as g3:
        print(await g3.get_recorder())


async def handler():
    await asyncio.gather(use_case_5())


def main():
    asyncio.run(handler())


if __name__ == "__main__":
    main()
