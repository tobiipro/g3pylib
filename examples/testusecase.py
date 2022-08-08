import asyncio
import json
import logging
import os
import time
from typing import List, cast

import cv2
import dotenv
from websockets.client import connect as websockets_connect

import glasses3.websocket as g3_websocket
from glasses3 import Glasses3, connect_to_glasses
from glasses3.g3typing import URI, JSONDict
from glasses3.recordings.recording import Recording
from glasses3.zeroconf import G3ServiceDiscovery

logging.basicConfig(level=logging.INFO)

dotenv.load_dotenv()  # type: ignore
g3_hostname = os.environ["G3_HOSTNAME"]
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
    async with connect_to_glasses(g3_hostname) as g3:
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
    async with connect_to_glasses(g3_hostname) as g3:
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
    async with connect_to_glasses(g3_hostname) as g3:
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
    async with connect_to_glasses(g3_hostname) as g3:
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
            print("Timed out. No event sample was received.")
        finally:
            await g3.rudimentary.stop_streams()


async def use_case_zeroconf():
    async with G3ServiceDiscovery.listen() as gsd:
        while True:
            print(gsd.services)
            await asyncio.sleep(10)


async def use_case_auto_connect():
    async with connect_to_glasses() as g3:
        async with g3.recordings.keep_updated_in_context():
            print(cast(Recording, g3.recordings[0]).uuid)


async def use_case_demux():
    async with connect_to_glasses(g3_hostname) as g3:
        async with g3.stream_rtsp() as streams:
            async with streams.scene_camera.demux() as demuxed_stream:
                for _ in range(10):
                    nal_unit = await demuxed_stream.get()
                    print(nal_unit.type, nal_unit.nri)


async def use_case_decode():
    async with connect_to_glasses(g3_hostname) as g3:
        async with g3.stream_rtsp(scene_camera=False, eye_cameras=True) as streams:
            async with streams.eye_cameras.decode() as decoded_stream:
                for _ in range(500):
                    frame = await decoded_stream.get()
                    t0 = time.perf_counter()
                    image = frame.to_ndarray(format="bgr24")
                    t1 = time.perf_counter()
                    logging.debug(f"Converted to nd_array in {t1 - t0:.6f} seconds")
                    cv2.imshow("Video", image)  # type: ignore
                    cv2.waitKey(1)
                logging.debug(streams.eye_cameras.stats)


async def use_case_two_streams():
    async with connect_to_glasses(g3_hostname) as g3:
        async with g3.stream_rtsp(scene_camera=True, eye_cameras=True) as streams:
            async with (
                streams.eye_cameras.decode() as eye_cameras,
                streams.scene_camera.decode() as scene_camera,
            ):
                for _ in range(100):
                    eye_frame = await eye_cameras.get()
                    await eye_cameras.get()
                    scene_frame = await scene_camera.get()
                    t0 = time.perf_counter()
                    image = eye_frame.to_ndarray(format="bgr24")
                    image2 = scene_frame.to_ndarray(format="bgr24")
                    t1 = time.perf_counter()
                    logging.debug(f"Converted to nd_array in {t1 - t0:.6f} seconds")
                    cv2.imshow("Eye", image)  # type: ignore
                    cv2.waitKey(1)
                    cv2.imshow("Scene", image2)  # type: ignore
                    cv2.waitKey(1)
                logging.debug(streams.eye_cameras.stats)


async def handler():
    await asyncio.gather(use_case_decode())


def main():
    asyncio.run(handler())


if __name__ == "__main__":
    main()
