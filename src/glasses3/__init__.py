"""This is the g3pylib package root."""
from __future__ import annotations

from types import TracebackType

from glasses3.calibrate import Calibrate

__version__ = "0.1.0-alpha"

import logging
from typing import Optional, Type, cast

import glasses3.websocket
from glasses3.g3typing import URI, LoggerLike
from glasses3.recorder import Recorder
from glasses3.recordings import Recordings
from glasses3.rudimentary import Rudimentary
from glasses3.settings import Settings
from glasses3.system import System
from glasses3.utils import APIComponent
from glasses3.websocket import G3WebSocketClientProtocol
from glasses3.zeroconf import G3Service, G3ServiceDiscovery


class Glasses3(APIComponent):
    def __init__(
        # Type ignored in this file since LoggerAdapter does not support generic typing
        self,
        connection: G3WebSocketClientProtocol,
        logger: Optional[LoggerLike] = None,
    ) -> None:
        self.logger = logging.getLogger(__name__) if logger is None else logger
        self._connection: G3WebSocketClientProtocol = connection
        self._recorder: Optional[Recorder] = None
        self._recordings: Optional[Recordings] = None
        self._rudimentary: Optional[Rudimentary] = None
        self._system: Optional[System] = None
        self._calibrate: Optional[Calibrate] = None
        self._settings: Optional[Settings] = None

    @property
    def calibrate(self):
        if self._calibrate is None:
            self._calibrate = Calibrate(self._connection, URI("/calibrate"))
        return self._calibrate

    @property
    def recorder(self):
        if self._recorder is None:
            self._recorder = Recorder(self._connection, URI("/recorder"))
        return self._recorder

    @property
    def recordings(self):
        if self._recordings is None:
            self._recordings = Recordings(self._connection, URI("/recordings"))
        return self._recordings

    @property
    def rudimentary(self):
        if self._rudimentary is None:
            self._rudimentary = Rudimentary(self._connection, URI("/rudimentary"))
        return self._rudimentary

    @property
    def system(self):
        if self._system is None:
            self._system = System(self._connection, URI("/system"))
        return self._system

    @property
    def settings(self):
        if self._settings is None:
            self._settings = Settings(self._connection, URI("/settings"))
        return self._settings

    async def close(self):
        await self._connection.close()


class connect_to_glasses:
    def __init__(
        self,
        g3_hostname: Optional[str] = None,
        service: Optional[G3Service] = None,
    ) -> None:
        self.g3_hostname = g3_hostname
        self.service = service

    def __await__(self):
        return self.__await_impl__().__await__()

    async def __await_impl__(self):
        if not self.g3_hostname and not self.service:
            async with G3ServiceDiscovery.listen() as service_discovery:
                self.service = await service_discovery.wait_for_single_service(
                    service_discovery.events
                )

        if not self.g3_hostname:
            self.g3_hostname = cast(G3Service, self.service).hostname

        connection = await glasses3.websocket.connect(self.g3_hostname)
        connection = cast(G3WebSocketClientProtocol, connection)
        connection.start_receiver_task()
        self.connection = connection
        return Glasses3(connection)

    async def __aenter__(self) -> Glasses3:
        return await self

    async def __aexit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ):
        await self.connection.close()
