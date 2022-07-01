from __future__ import annotations

import asyncio
from asyncio import Task
from contextlib import asynccontextmanager
from typing import AsyncIterator, Coroutine, Dict, Set

from zeroconf import IPVersion, ServiceListener, Zeroconf
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf

from glasses3.zeroconf.exceptions import ServiceDiscoveryError


class ZeroconfListener(ServiceListener):
    def __init__(self, services_handler: _G3ServicesHandler):
        self._services_handler = services_handler

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self._services_handler.update_service(zc, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self._services_handler.remove_service(name)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self._services_handler.add_service(zc, type_, name)


class G3Service:
    def __init__(self, service_info: AsyncServiceInfo) -> None:
        self._service_info = service_info

    @property
    def service_info(self):
        return self._service_info

    @property
    def hostname(self):
        return self._service_info.get_name()

    @property
    def type(self):
        return self._service_info.type

    @property
    def server(self):
        return self._service_info.server

    @property
    def ipv4_address(self):
        return self.service_info.parsed_addresses(IPVersion.V4Only)[0]

    @property
    def ipv6_address(self):
        return self._service_info.parsed_addresses(IPVersion.V6Only)[0]

    def __repr__(self) -> str:
        return "{}({})".format(
            type(self).__name__,
            ", ".join(
                "{}={!r}".format(name, getattr(self, name))
                for name in (
                    "hostname",
                    "type",
                    "ipv4_address",
                    "ipv6_address",
                    "server",
                )
            ),
        )


class _G3ServicesHandler:
    def __init__(self) -> None:
        self._service_tasks: Set[Task[None]] = set()
        self._services: Dict[str, G3Service] = dict()

    @property
    def services(self):
        return self._services

    def update_service(self, zc: Zeroconf, name: str):
        async def update_service_task():
            service_info = self._services[name].service_info
            if not await service_info.async_request(zc, 3000):
                raise ServiceDiscoveryError(
                    f"Service with name {service_info.name} was not discovered."
                )

        self._create_service_task(update_service_task(), f"update_service_{name}")

    def remove_service(self, name: str):
        del self._services[name]

    def add_service(self, zc: Zeroconf, type_: str, name: str):
        async def add_service_task():
            service_info = AsyncServiceInfo(type_, name)
            self._services[service_info.get_name()] = G3Service(service_info)
            if not await service_info.async_request(zc, 3000):
                raise ServiceDiscoveryError(f"{service_info}")

        self._create_service_task(add_service_task(), f"add_service_{name}")

    def _create_service_task(self, coro: Coroutine[None, None, None], name: str):
        task = asyncio.create_task(coro, name=name)
        self._service_tasks.add(task)
        task.add_done_callback(self._service_tasks.discard)


class G3ServiceDiscovery:
    G3_SERVICE_TYPE_NAME = "_tobii-g3api._tcp.local."

    def __init__(
        self, async_zeroconf: AsyncZeroconf, services_handler: _G3ServicesHandler
    ) -> None:
        self.async_zeroconf = async_zeroconf
        self._services_handler = services_handler

    @classmethod
    @asynccontextmanager
    async def connect(cls) -> AsyncIterator[G3ServiceDiscovery]:
        async with AsyncZeroconf() as async_zeroconf:
            services_handler = _G3ServicesHandler()
            zeroconf_listener = ZeroconfListener(services_handler)
            await async_zeroconf.async_add_service_listener(
                cls.G3_SERVICE_TYPE_NAME, zeroconf_listener
            )
            yield cls(async_zeroconf, services_handler)

    @property
    def services_by_serial_number(self):
        return self._services_handler.services

    @property
    def services(self):
        return list(self._services_handler.services.values())
