from __future__ import annotations

import asyncio
import logging
from asyncio import CancelledError, Future, Task
from contextlib import asynccontextmanager
from types import TracebackType
from typing import AsyncIterator, Coroutine, Dict, Optional, Set, Type

from zeroconf import IPVersion, ServiceListener, Zeroconf
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf

from glasses3 import utils
from glasses3.zeroconf.exceptions import ServiceDiscoveryError, ServiceEventError

logger = logging.getLogger(__name__)


class G3Service:
    def __init__(self, service_info: AsyncServiceInfo) -> None:
        self._service_info = service_info

    @property
    def service_info(self) -> AsyncServiceInfo:
        return self._service_info

    @property
    def hostname(self) -> str:
        return self._service_info.get_name()

    @property
    def type(self) -> str:
        return self._service_info.type

    @property
    def server(self) -> str:
        return self._service_info.server

    @property
    def ipv4_address(self) -> Optional[str]:
        try:
            return self.service_info.parsed_addresses(IPVersion.V4Only)[0]
        except IndexError:
            return None

    @property
    def ipv6_address(self) -> Optional[str]:
        try:
            return self._service_info.parsed_addresses(IPVersion.V6Only)[0]
        except IndexError:
            return None

    def __repr__(self) -> str:
        return "{}({})".format(
            type(self).__name__,
            ", ".join(
                "{}={!r}".format(name, getattr(self, name))
                for name in (
                    "hostname",
                    "type",
                    "server",
                    "ipv4_address",
                    "ipv6_address",
                )
            ),
        )


class _G3ServicesHandler(ServiceListener):
    def __init__(self) -> None:
        self._service_tasks: Set[Task[None]] = set()
        self._future_services: Future[
            Dict[str, G3Service]
        ] = asyncio.get_running_loop().create_future()

    @property
    def services(self):
        return self._future_services.result()

    @property
    def future_services(self):
        return self._future_services

    def update_service(self, zc: Zeroconf, type_: str, name: str):

        logger.debug(f"The service {name} is updated")
        self._create_service_task(
            self._add_or_update_service_task(zc, type_, name), f"update_service_{name}"
        )

    def remove_service(self, zc: Zeroconf, type_: str, name: str):
        if not self._future_services.done():
            raise ServiceEventError(
                "Remove service tried before any service was added."
            )
        logger.debug(f"The service {name} is removed")
        del self.services[self._hostname(type_, name)]

    def add_service(self, zc: Zeroconf, type_: str, name: str):
        logger.debug(f"The service {name} is added")
        self._create_service_task(
            self._add_or_update_service_task(zc, type_, name), f"add_service_{name}"
        )

    async def _add_or_update_service_task(self, zc: Zeroconf, type_: str, name: str):
        if not self._future_services.done():
            self._future_services.set_result(dict())
        hostname = self._hostname(type_, name)
        if hostname in self.services:
            success = await self.services[hostname].service_info.async_request(zc, 3000)
        else:
            service_info = AsyncServiceInfo(type_, name)
            success = await service_info.async_request(zc, 3000)
            self.services[hostname] = G3Service(service_info)
        if not success:
            raise ServiceDiscoveryError(f"Service with name {name} was not discovered.")

    def _create_service_task(self, coro: Coroutine[None, None, None], name: str):
        task = utils.create_task(coro, name=name)
        self._service_tasks.add(task)
        task.add_done_callback(self._service_tasks.discard)

    @staticmethod
    def _hostname(type_: str, name: str) -> str:
        return name[: len(name) - len(type_) - 1]

    async def close(self):
        for task in self._service_tasks:
            task.cancel()
        for task in self._service_tasks:
            try:
                await task
            except CancelledError:
                logger.debug("task in service_tasks cancelled")
        self._service_tasks.clear()

    async def __aenter__(self):
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ):
        await self.close()


class G3ServiceDiscovery:
    G3_SERVICE_TYPE_NAME = "_tobii-g3api._tcp.local."

    def __init__(
        self, async_zeroconf: AsyncZeroconf, services_handler: _G3ServicesHandler
    ) -> None:
        self.async_zeroconf = async_zeroconf
        self._services_handler = services_handler

    @classmethod
    @asynccontextmanager
    async def listen(cls) -> AsyncIterator[G3ServiceDiscovery]:
        async with AsyncZeroconf() as async_zeroconf:
            async with _G3ServicesHandler() as services_handler:
                await async_zeroconf.async_add_service_listener(
                    cls.G3_SERVICE_TYPE_NAME, services_handler
                )
                try:
                    await asyncio.wait_for(services_handler.future_services, 3)
                except TimeoutError:
                    services_handler.future_services.set_result(dict())
                    logger.debug(
                        "No Zeroconf services found before timeout. Services future resolved with empty dict."
                    )

                yield cls(async_zeroconf, services_handler)

    @property
    def services_by_serial_number(self):
        return self._services_handler.services

    @property
    def services(self):
        return list(self._services_handler.services.values())
