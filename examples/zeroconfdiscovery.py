import asyncio
import logging

from glasses3.zeroconf import EventKind, G3ServiceDiscovery

logging.basicConfig(level=logging.INFO)


async def zeroconf_discovery():
    async with G3ServiceDiscovery.listen() as service_discovery:
        while True:
            match await service_discovery.events.get():
                case (EventKind.ADDED, service):
                    logging.info(f"The service {service.hostname} was added")
                case (EventKind.UPDATED, service):
                    logging.info(f"The service {service.hostname} was updated")
                case (EventKind.REMOVED, service):
                    logging.info(f"The service {service.hostname} was removed")
                case _:
                    pass


def main():
    asyncio.run(zeroconf_discovery())


if __name__ == "__main__":
    main()
