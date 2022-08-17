import asyncio
import logging
import os

import dotenv

from g3pylib import connect_to_glasses

logging.basicConfig(level=logging.INFO)


async def subscribe_to_signal():
    async with connect_to_glasses.with_hostname(os.environ["G3_HOSTNAME"]) as g3:
        signal_queue, unsubscribe = await g3.recordings.subscribe_to_child_added()
        await g3.recorder.start()
        await asyncio.sleep(3)
        await g3.recorder.stop()
        signal_body = await signal_queue.get()
        logging.info(f"Received signal: {signal_body}")
        await unsubscribe


def main():
    asyncio.run(subscribe_to_signal())


if __name__ == "__main__":
    dotenv.load_dotenv()
    main()
