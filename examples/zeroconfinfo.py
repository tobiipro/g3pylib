import asyncio
import logging
import os

import dotenv

from g3pylib.zeroconf import G3ServiceDiscovery

logging.basicConfig(level=logging.INFO)


async def zeroconf_info():
    service = await G3ServiceDiscovery.request_service(os.environ["G3_HOSTNAME"])
    logging.info(f"Received service {service}")


def main():
    asyncio.run(zeroconf_info())


if __name__ == "__main__":
    dotenv.load_dotenv()
    main()
