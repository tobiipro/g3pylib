import asyncio
import logging
import os

import dotenv

from g3pylib import connect_to_glasses

logging.basicConfig(level=logging.INFO)


async def stream_rtsp():
    async with connect_to_glasses.with_hostname(os.environ["G3_HOSTNAME"]) as g3:
        async with g3.stream_rtsp(gaze=True) as streams:
            async with streams.gaze.decode() as gaze_stream:
                for i in range(300):
                    gaze = await gaze_stream.get()
                    if "gaze2d" in gaze:
                        gaze2d = gaze["gaze2d"]
                        logging.info(f"Gaze2d: {gaze2d[0]:9.4f},{gaze2d[1]:9.4f}")
                    elif i % 50 == 0:
                        logging.info(
                            "No gaze data received. have you tried putting on the glasses?"
                        )


def main():
    asyncio.run(stream_rtsp())


if __name__ == "__main__":
    dotenv.load_dotenv()
    main()
