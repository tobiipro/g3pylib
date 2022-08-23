import asyncio
import logging
import os

import cv2
import dotenv

from g3pylib import connect_to_glasses

logging.basicConfig(level=logging.INFO)


async def stream_rtsp():
    async with connect_to_glasses.with_hostname(os.environ["G3_HOSTNAME"]) as g3:
        async with g3.stream_rtsp(scene_camera=True) as streams:
            async with streams.scene_camera.decode() as decoded_stream:
                for _ in range(300):
                    frame, _timestamp = await decoded_stream.get()
                    image = frame.to_ndarray(format="bgr24")
                    cv2.imshow("Video", image)  # type: ignore
                    cv2.waitKey(1)  # type: ignore
                logging.debug(streams.scene_camera.stats)


def main():
    asyncio.run(stream_rtsp())


if __name__ == "__main__":
    dotenv.load_dotenv()
    main()
