from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from enum import Enum, auto
from types import TracebackType
from typing import AsyncIterator, Dict, Optional, Tuple, Type

from zeroconf import IPVersion, ServiceListener, Zeroconf
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf

from glasses3 import utils

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


class EventKind(Enum):
    ADDED = auto()
    REMOVED = auto()
    UPDATED = auto()


class _G3ServicesHandler(ServiceListener):
    def __init__(self, zc: Zeroconf) -> None:
        self.zc = zc
        self._services: Dict[str, G3Service] = dict()
        self._events: asyncio.Queue[Tuple[EventKind, G3Service]] = asyncio.Queue()
        self._unhandled_events: asyncio.Queue[
            Tuple[EventKind, G3Service]
        ] = asyncio.Queue()
        self.service_handler_task = utils.create_task(
            self.service_handler(), name="service_handler"
        )

    @property
    def services(self):
        return self._services

    @property
    def events(self):
        return self._events

    def update_service(self, zc: Zeroconf, type_: str, name: str):
        logger.debug(f"The service {name} is updated")
        self._unhandled_events.put_nowait(
            (EventKind.UPDATED, G3Service(AsyncServiceInfo(type_, name)))
        )

    def remove_service(self, zc: Zeroconf, type_: str, name: str):
        logger.debug(f"The service {name} is removed")
        self._unhandled_events.put_nowait(
            (EventKind.REMOVED, G3Service(AsyncServiceInfo(type_, name)))
        )

    def add_service(self, zc: Zeroconf, type_: str, name: str):
        logger.debug(f"The service {name} is added")
        self._unhandled_events.put_nowait(
            (EventKind.ADDED, G3Service(AsyncServiceInfo(type_, name)))
        )

    async def service_handler(self):
        while True:
            event = await self._unhandled_events.get()
            match event:
                case (EventKind.ADDED, service):
                    await service.service_info.async_request(self.zc, 3000)
                    self._services[service.hostname] = service
                    await asyncio.shield(self._events.put(event))
                case (EventKind.UPDATED, service):
                    service = self.services[service.hostname]
                    await asyncio.shield(
                        service.service_info.async_request(self.zc, 3000)
                    )
                    await asyncio.shield(self._events.put((EventKind.UPDATED, service)))
                case (EventKind.REMOVED, service):
                    del self.services[service.hostname]
                    await asyncio.shield(self._events.put(event))
                case _:
                    pass

    @staticmethod
    def _hostname(type_: str, name: str) -> str:
        return name[: len(name) - len(type_) - 1]

    async def close(self):
        self.service_handler_task.cancel()

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
            async with _G3ServicesHandler(async_zeroconf.zeroconf) as services_handler:
                await async_zeroconf.async_add_service_listener(
                    cls.G3_SERVICE_TYPE_NAME, services_handler
                )
                yield cls(async_zeroconf, services_handler)

    @property
    def services_by_serial_number(self):
        return self._services_handler.services

    @property
    def events(self):
        return self._services_handler.events

    @property
    def services(self):
        return list(self._services_handler.services.values())

    @staticmethod
    async def wait_for_single_service(
        events: asyncio.Queue[Tuple[EventKind, G3Service]],
        ip_version: IPVersion = IPVersion.All,
    ):
        while True:
            event = await events.get()
            if event[0] in [EventKind.UPDATED, EventKind.ADDED]:
                service = event[1]
                match ip_version:
                    case IPVersion.All:
                        if service.ipv4_address and service.ipv6_address:
                            return service
                    case IPVersion.V4Only:
                        if service.ipv4_address:
                            return service
                    case IPVersion.V6Only:
                        if service.ipv6_address:
                            return service
