import websockets
import glasses3.websocket
import json
import asyncio

g3_hostname = "tg02b-080105022801"
test_request = '{"path":"/recorder", "method":"GET"}'


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


async def handler():
    await asyncio.gather(use_case_1(), use_case_2())


def main():
    asyncio.run(handler())


if __name__ == "__main__":
    main()
