import asyncio
import logging
import os

import cv2
import dotenv

from g3pylib import connect_to_glasses

logging.basicConfig(level=logging.INFO)


async def stream_rtsp():
    async with connect_to_glasses.with_hostname(os.environ["G3_HOSTNAME"]) as g3:
        async with g3.stream_rtsp(scene_camera=True, gaze=True) as streams:
            async with streams.gaze.decode() as gaze_stream, streams.scene_camera.decode() as scene_stream:
                for i in range(200):
                    frame_timestamp, frame = await scene_stream.get()
                    gaze_timestamp, gaze = await gaze_stream.get()
                    while gaze_timestamp is None or frame_timestamp is None:
                        if frame_timestamp is None:
                            frame_timestamp, frame = await scene_stream.get()
                        if gaze_timestamp is None:
                            gaze_timestamp, gaze = await gaze_stream.get()
                    while gaze_timestamp < frame_timestamp:
                        gaze_timestamp, gaze = await gaze_stream.get()
                        while gaze_timestamp is None:
                            gaze_timestamp, gaze = await gaze_stream.get()
                    cv2.imshow("Video", frame.to_ndarray(format="bgr24"))  # type: ignore
                    cv2.waitKey(1)  # type: ignore
                    logging.info(f"Frame timestamp: {frame_timestamp}")
                    logging.info(f"Gaze timestamp: {gaze_timestamp}")
                    if "gaze2d" in gaze:
                        gaze2d = gaze["gaze2d"]
                        logging.info(f"Gaze2d: {gaze2d[0]:9.4f},{gaze2d[1]:9.4f}")
                    elif i % 50 == 0:
                        logging.info(
                            "No gaze data received. Have you tried putting on the glasses?"
                        )


def main():
    asyncio.run(stream_rtsp())


if __name__ == "__main__":
    dotenv.load_dotenv()
    main()
