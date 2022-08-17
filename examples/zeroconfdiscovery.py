import asyncio
import logging

from g3pylib.zeroconf import EventKind, G3ServiceDiscovery

logging.basicConfig(level=logging.INFO)


async def zeroconf_discovery():
    async with G3ServiceDiscovery.listen() as service_discovery:
        logging.info("Listening for glasses3")
        service_found = False
        try:
            while True:
                match await service_discovery.events.get():
                    case (EventKind.ADDED, service):
                        logging.info(f"The service {service.hostname} was added")
                        service_found = True
                    case (EventKind.UPDATED, service):
                        logging.info(f"The service {service.hostname} was updated")
                        service_found = True
                    case (EventKind.REMOVED, service):
                        logging.info(f"The service {service.hostname} was removed")
                        service_found = True
                    case _:
                        pass
        finally:
            if not service_found:
                logging.info("No services found")
            logging.info("Stop listening")


async def zeroconf_discovery_with_timeout():
    try:
        await asyncio.wait_for(zeroconf_discovery(), 5)
    except asyncio.TimeoutError:
        pass


def main():
    asyncio.run(zeroconf_discovery_with_timeout())


if __name__ == "__main__":
    main()
