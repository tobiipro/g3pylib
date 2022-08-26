from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from enum import Enum, auto
from types import TracebackType
from typing import AsyncIterator, Dict, List, Optional, Tuple, Type, cast

from zeroconf import IPVersion, ServiceListener, Zeroconf
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf

from g3pylib import _utils

_logger: logging.Logger = logging.getLogger(__name__)

RTSP_SERVICE_TYPE = "_rtsp._tcp.local."
G3_SERVICE_TYPE = "_tobii-g3api._tcp.local."
DEFAULT_WEBSOCKET_PATH = "/websocket"


class ServiceNotFoundError(Exception):
    """Raised when a service request is not successful."""


class IncompleteServiceError(Exception):
    """Raised when a service is missing an expected property."""


class G3Service:
    """A service representing a Glasses3 device on the network.

    Holds information about the g3api-service and the corresponding rtsp-service of a Glasses3 device. Unless explicitly stated, properties refer to the g3api-service.

    To discover Glasses3 services on a network, see `G3ServiceDiscovery`.
    """

    def __init__(self, service_info: AsyncServiceInfo) -> None:
        self._service_info = service_info
        self._rtsp_service_info = None

    @property
    def service_info(self) -> AsyncServiceInfo:
        """The `AsyncServiceInfo` object containing all information about the service."""
        return self._service_info

    @property
    def rtsp_service_info(self) -> Optional[AsyncServiceInfo]:
        """The `AsyncServiceInfo` object containing all information about the corresponding RTSP-service."""
        return self._rtsp_service_info

    @property
    def hostname(self) -> str:
        """The Glasses3 device's hostname."""
        return self._service_info.get_name()

    @property
    def type(self) -> str:
        """The type of the service."""
        return self._service_info.type

    @property
    def server(self) -> str:
        """The name of the service host."""
        return self._service_info.server

    @property
    def ipv4_address(self) -> Optional[str]:
        """The IPv4 address of the service."""
        try:
            return self.service_info.parsed_addresses(IPVersion.V4Only)[0]
        except IndexError:
            return None

    @property
    def ipv6_address(self) -> Optional[str]:
        """The IPv6 address of the service."""
        try:
            return self._service_info.parsed_addresses(IPVersion.V6Only)[0]
        except IndexError:
            return None

    def _ip_or_hostname(self, using_ip: bool, ip_version: IPVersion) -> str:
        if using_ip:
            if ip_version == IPVersion.V4Only:
                if self.ipv4_address is None:
                    raise IncompleteServiceError("Missing IPV4 address.")
                return self.ipv4_address
            elif ip_version == IPVersion.V6Only:
                if self.ipv6_address is None:
                    raise IncompleteServiceError("Missing IPV6 address.")
                return self.ipv6_address
            else:
                raise ValueError("This function only support either IPV4 or IPV6.")
        else:
            return self.hostname

    def ws_url(
        self, using_ip: bool = False, ip_version: IPVersion = IPVersion.V4Only
    ) -> str:
        ip_or_hostname = self._ip_or_hostname(using_ip, ip_version)
        return f"ws://{ip_or_hostname}{DEFAULT_WEBSOCKET_PATH}"

    def rtsp_url(
        self, using_ip: bool = False, ip_version: IPVersion = IPVersion.V4Only
    ) -> Optional[str]:
        """The url used to connect to an RTSP client to the live stream."""
        if self.rtsp_service_info is None:
            return None
        ip_or_hostname = self._ip_or_hostname(using_ip, ip_version)
        return f"rtsp://{ip_or_hostname}:{self.rtsp_port}{self.rtsp_live_path}"

    def http_url(
        self, using_ip: bool = False, ip_version: IPVersion = IPVersion.V4Only
    ) -> Optional[str]:
        """The url used to make HTTP requests to the device."""
        ip_or_hostname = self._ip_or_hostname(using_ip, ip_version)
        return f"http://{ip_or_hostname}:{self.service_info.port}"

    @property
    def rtsp_port(self) -> Optional[int]:
        """The port used for the RTSP service."""
        if self.rtsp_service_info is None:
            return None
        return self.rtsp_service_info.port

    @property
    def rtsp_live_path(self) -> Optional[str]:
        """The RTSP-service live path"""
        if self.rtsp_service_info is None:
            return None
        return cast(Dict[bytes, bytes], self.rtsp_service_info.properties)[b"path"].decode("ascii")  # type: ignore

    @property
    def rtsp_recordings_path(self) -> Optional[str]:
        """The RTSP-service recordings path."""
        # Possibly unnecessary. This path can be fetched from the API.
        if self.rtsp_service_info is None:
            return None
        return cast(Dict[bytes, bytes], self.rtsp_service_info.properties)[b"recordings"].decode("ascii")  # type: ignore

    async def request(self, zc: Zeroconf, timeout: float = 3000) -> None:
        """Attempts to update the services' information and raises `ServiceNotFoundError` when the services can't be found on the network."""
        success = await self.service_info.async_request(zc, timeout)
        if not success:
            raise ServiceNotFoundError
        rtsp_service_info = AsyncServiceInfo(
            RTSP_SERVICE_TYPE, f"{self.hostname}.{RTSP_SERVICE_TYPE}"
        )
        if await rtsp_service_info.async_request(zc, timeout):
            self._rtsp_service_info = rtsp_service_info

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

    @classmethod
    def from_hostname(cls, hostname: str) -> G3Service:
        """TODO: can be used to ... recommended G3disc"""
        return cls(AsyncServiceInfo(G3_SERVICE_TYPE, f"{hostname}.{G3_SERVICE_TYPE}"))


class EventKind(Enum):
    """Defines service events."""

    ADDED = auto()
    REMOVED = auto()
    UPDATED = auto()


class _G3ServicesHandler(ServiceListener):
    def __init__(self, zc: Zeroconf, timeout: float = 3000) -> None:
        self.zc = zc
        self._services: Dict[str, G3Service] = dict()
        self._events: asyncio.Queue[Tuple[EventKind, G3Service]] = asyncio.Queue()
        self._unhandled_events: asyncio.Queue[
            Tuple[EventKind, G3Service]
        ] = asyncio.Queue()
        self.service_handler_task: asyncio.Task[None] = _utils.create_task(
            self.service_handler(timeout), name="service_handler"
        )

    @property
    def services(self) -> Dict[str, G3Service]:
        return self._services

    @property
    def events(self) -> asyncio.Queue[Tuple[EventKind, G3Service]]:
        return self._events

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        _logger.debug(f"The service {name} is updated")
        self._unhandled_events.put_nowait(
            (EventKind.UPDATED, G3Service(AsyncServiceInfo(type_, name)))
        )

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        _logger.debug(f"The service {name} is removed")
        self._unhandled_events.put_nowait(
            (EventKind.REMOVED, G3Service(AsyncServiceInfo(type_, name)))
        )

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        _logger.debug(f"The service {name} is added")
        self._unhandled_events.put_nowait(
            (EventKind.ADDED, G3Service(AsyncServiceInfo(type_, name)))
        )

    async def service_handler(self, timeout: float) -> None:
        while True:
            event = await self._unhandled_events.get()
            match event:
                case (EventKind.ADDED, service):
                    await service.request(self.zc, timeout)
                    self._services[service.hostname] = service
                    await asyncio.shield(self._events.put(event))
                case (EventKind.UPDATED, service):
                    service = self.services[service.hostname]
                    await asyncio.shield(service.request(self.zc, timeout))
                    await asyncio.shield(self._events.put((EventKind.UPDATED, service)))
                case (EventKind.REMOVED, service):
                    del self.services[service.hostname]
                    await asyncio.shield(self._events.put(event))
                case _:
                    pass

    @staticmethod
    def _hostname(type_: str, name: str) -> str:
        return name[: len(name) - len(type_) - 1]

    async def close(self) -> None:
        self.service_handler_task.cancel()

    async def __aenter__(self) -> _G3ServicesHandler:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        await self.close()


class G3ServiceDiscovery:
    """Tools for discovering Glasses3 services.

    To get a Glasses3 service by hostname, see `request_service`.

    To continuously handle Glasses3 services on the network, see `listen`.
    """

    def __init__(
        self,
        async_zeroconf: AsyncZeroconf,
        services_handler: _G3ServicesHandler,
    ) -> None:
        self.async_zeroconf = async_zeroconf
        self._services_handler = services_handler

    @staticmethod
    async def request_service(hostname: str, timeout: float = 3000) -> G3Service:
        """Request information about a single specific service identified by its hostname.
        Raises `ServiceNotFoundError` when the service can't be found on the network.
        """
        service = G3Service.from_hostname(hostname)
        async with AsyncZeroconf() as async_zeroconf:
            await service.request(async_zeroconf.zeroconf, timeout)
        return service

    @classmethod
    @asynccontextmanager
    async def listen(cls, timeout: float = 3000) -> AsyncIterator[G3ServiceDiscovery]:
        """Keeps discovery updated in the context including:

        `services_by_serial_number`: dict containing all available services.
        `events`: queue with all service events
        `services`: list of all available services.

        Additionally, `wait_for_single_service` may be called to obtain the first available Glasses3 service.
        """
        async with AsyncZeroconf() as async_zeroconf:
            async with _G3ServicesHandler(
                async_zeroconf.zeroconf, timeout
            ) as services_handler:
                await async_zeroconf.async_add_service_listener(
                    G3_SERVICE_TYPE, services_handler
                )
                yield cls(async_zeroconf, services_handler)

    @property
    def services_by_serial_number(self) -> Dict[str, G3Service]:
        """A dict mapping serial number to `G3Service` for all available Glasses3 services.

        Is kept updated in the `listen` context.
        """
        return self._services_handler.services

    @property
    def events(self) -> asyncio.Queue[Tuple[EventKind, G3Service]]:
        """A queue where service events are put.

        The events consists of tuples where
         - the first entry indicates the type of event
         - the second entry contains the relevant `G3Service`.

        Is kept updated in the `listen` context.
        """
        return self._services_handler.events

    @property
    def services(self) -> List[G3Service]:
        """A list of all available `G3Service`.

        Is kept updated in the `listen` context.
        """
        return list(self._services_handler.services.values())

    @staticmethod
    async def wait_for_single_service(
        events: asyncio.Queue[Tuple[EventKind, G3Service]],
        timeout: float = 3000,
        ip_version: IPVersion = IPVersion.All,
    ) -> G3Service:
        """Returns the first available `G3Service`.

        `events` is the `G3DiscoveryService.events` queue used to look for service events.
        `ip_version` specifies what type(s) of ip address are required in the returned service.
        `timeout` defines the time in milliseconds before `asyncio.TimeoutError` is raised.

        Must be called in the `listen` context to find a service.
        """
        t_start = time.time()
        t_done = t_start + timeout / 1000
        while True:
            time_left = t_done - time.time()
            if time_left > 0:
                event = await asyncio.wait_for(events.get(), timeout=time_left)
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
