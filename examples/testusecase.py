import asyncio
import json
import logging
import os
from typing import List, cast

import dotenv
from websockets.client import connect as websockets_connect

import glasses3.websocket as g3_websocket
from glasses3 import Glasses3
from glasses3.g3typing import URI, Hostname, JSONDict
from glasses3.recordings.recording import Recording
from glasses3.zeroconf import G3ServiceDiscovery

logging.basicConfig(level=logging.DEBUG)

dotenv.load_dotenv()  # type: ignore
g3_hostname = Hostname(os.environ["G3_HOSTNAME"])
test_request: JSONDict = {"path": "/recorder", "method": "GET"}
test_request_path = URI("/recorder")
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
        f"ws://{g3_hostname}/websockets",
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
        print(await g3.recorder.get_created())


async def use_case_signal():
    async with g3_websocket.connect(g3_hostname) as g3ws:
        g3ws = cast(g3_websocket.G3WebSocketClientProtocol, g3ws)
        g3ws.start_receiver_task()
        queue1, unsubscribe1 = await g3ws.subscribe_to_signal(URI("/recorder:started"))
        queue2, unsubscribe2 = await g3ws.subscribe_to_signal(URI("/recorder:started"))
        logging.info(await queue1.get())
        logging.info(await queue2.get())
        await unsubscribe1
        await unsubscribe2


async def use_case_list_of_recordings():
    async with Glasses3.connect(g3_hostname) as g3:
        await g3.recordings.start_children_handler_tasks()
        print("Initial last 3 recordings: ")
        for recording in cast(List[Recording], g3.recordings[:3]):
            print(recording.uuid)
        await g3.recorder.start()
        await asyncio.sleep(3)
        await g3.recorder.stop()
        print("Last 3 after making a recording: ")
        for recording in cast(List[Recording], g3.recordings[:3]):
            print(recording.uuid)
        await g3.recordings.delete(cast(Recording, g3.recordings[0]).uuid)
        print("Last 3 after removing the most recent recording: ")
        for recording in cast(List[Recording], g3.recordings[:3]):
            print(recording.uuid)
        print("Last 3 accessed via children property: ")
        for child in g3.recordings.children[:3]:
            print(child.uuid)
        await g3.recordings.stop_children_handler_tasks()


async def use_case_rudimentary_streams():
    async with Glasses3.connect(g3_hostname) as g3:
        queue, unsubscribe = await g3.rudimentary.subscribe_to_gaze()

        async def task():
            count = 0
            while True:
                count += 1
                print(count, await queue.get())
                await asyncio.sleep(0.02)
                queue.task_done()

        await g3.rudimentary.start_streams()
        logging.debug("Streams started")
        await asyncio.sleep(1)
        t = asyncio.create_task(task())
        await asyncio.sleep(14)
        await g3.rudimentary.stop_streams()
        logging.debug("Streams stopped")
        await queue.join()
        t.cancel()
        await unsubscribe


async def use_case_crash_receiver_task():
    async with Glasses3.connect(g3_hostname) as g3:
        await g3.rudimentary.start_streams()
        assert await g3.rudimentary.send_event("my-tag", {"my-key": "my-value"})

        async def retry_get_event_sample():
            event_sample = await g3.rudimentary.get_event_sample()
            while event_sample == {}:
                event_sample = (
                    await g3.rudimentary.get_event_sample()
                )  # shield this coroutine to protect future from cancellation
            return event_sample

        try:
            print(
                f"Event sample: {await asyncio.wait_for(retry_get_event_sample(), timeout=1)}"
            )
        except asyncio.TimeoutError:
            print("TimeoutError")
        finally:
            await g3.rudimentary.stop_streams()


async def use_case_zeroconf():
    async with G3ServiceDiscovery.connect() as gsd:
        print(gsd.services)


async def handler():
    await asyncio.gather(use_case_zeroconf())


def main():
    asyncio.run(handler())


if __name__ == "__main__":
    main()
