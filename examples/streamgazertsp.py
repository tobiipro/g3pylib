import asyncio
import logging
import os

import cv2
import dotenv

from glasses3 import connect_to_glasses

logging.basicConfig(level=logging.INFO)


async def stream_rtsp():
    async with connect_to_glasses(os.environ["G3_HOSTNAME"]) as g3:
        async with g3.stream_rtsp(gaze=True) as streams:
            async with streams.gaze.decode() as gaze_stream:
                for _ in range(300):
                    gaze = await gaze_stream.get()

                    if "gaze2d" in gaze:
                        gaze2d = gaze['gaze2d']
                        logging.info(f'Gaze: {gaze2d[0]:9.4f},{gaze2d[1]:9.4f}')


def main():
    asyncio.run(stream_rtsp())


if __name__ == "__main__":
    dotenv.load_dotenv()
    main()
