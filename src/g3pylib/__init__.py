"""
.. include:: ../../README.md

g3pylib is a python wrapper around the Glasses3 web API which lets you control Glasses3 devices.

## API Endpoints
All endpoints in the `g3pylib` module corresponding to an endpoint in the Glasses3 web API are undocumented and placed first in each module.
The following naming convention is used to translate web API endpoint names to `g3pylib
` API endpoint names:
 - Properties: example_property -> get_example_property/set_example_property
 - Actions: example_action -> example_action
 - Signals: example_signal -> subscribe_to_example_signal

The web API endpoints can be browsed in the Glasses3 Example web client accessed via http://*your-g3-address*.

## Useful information
In any code examples, `g3` will be a connected instance of `Glasses3`.

The default hostname of a Glasses3 device is its serial number.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from types import TracebackType
from typing import Any, AsyncIterator, Coroutine, Generator, Optional, Tuple, Type, cast


import g3pylib.websocket
from g3pylib._utils import APIComponent
from g3pylib.calibrate import Calibrate
from g3pylib.exceptions import FeatureNotAvailableError
from g3pylib.g3typing import URI, LoggerLike
from g3pylib.recorder import Recorder
from g3pylib.recordings import Recordings
from g3pylib.rudimentary import Rudimentary
from g3pylib.settings import Settings
from g3pylib.streams import Streams
from g3pylib.system import System
from g3pylib.websocket import G3WebSocketClientProtocol
from g3pylib.zeroconf import DEFAULT_WEBSOCKET_PATH, G3Service, G3ServiceDiscovery

__version__ = "0.3.1-alpha"

DEFAULT_RTSP_LIVE_PATH = "/live/all"
DEFAULT_RTSP_PORT = 8554
DEFAULT_HTTP_PORT = 80

_logger = logging.getLogger(__name__)


class Glasses3(APIComponent):
    """
    Represents a Glasses3 device.

    Holds the API components and a WebSocket connection to a Glasses3 device.
    The `stream_rtsp` context can be used for live stream functionality.

    For the recommended way to create a connected instance of Glasses3, see `connect_to_glasses`.
    """

    def __init__(
        self,
        connection: G3WebSocketClientProtocol,
        rtsp_url: Optional[str],
        http_url: Optional[str],
        logger: Optional[LoggerLike] = None,
    ) -> None:
        self.logger: LoggerLike = (
            logging.getLogger(__name__) if logger is None else logger
        )
        self._rtsp_url = rtsp_url
        self._http_url = http_url
        self._connection: G3WebSocketClientProtocol = connection
        self._recorder: Optional[Recorder] = None
        self._recordings: Optional[Recordings] = None
        self._rudimentary: Optional[Rudimentary] = None
        self._system: Optional[System] = None
        self._calibrate: Optional[Calibrate] = None
        self._settings: Optional[Settings] = None

    @property
    def calibrate(self) -> Calibrate:
        if self._calibrate is None:
            self._calibrate = Calibrate(self._connection, URI("/calibrate"))
        return self._calibrate

    @property
    def recorder(self) -> Recorder:
        if self._recorder is None:
            self._recorder = Recorder(self._connection, URI("/recorder"))
        return self._recorder

    @property
    def recordings(self) -> Recordings:
        if self._recordings is None:
            self._recordings = Recordings(
                self._connection, URI("/recordings"), self._http_url
            )
        return self._recordings

    @property
    def rudimentary(self) -> Rudimentary:
        if self._rudimentary is None:
            self._rudimentary = Rudimentary(self._connection, URI("/rudimentary"))
        return self._rudimentary

    @property
    def system(self) -> System:
        if self._system is None:
            self._system = System(self._connection, URI("/system"))
        return self._system

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = Settings(self._connection, URI("/settings"))
        return self._settings

    @property
    def rtsp_url(self) -> Optional[str]:
        """The RTSP URL used for live stream."""
        return self._rtsp_url

    @asynccontextmanager
    async def stream_rtsp(
        self,
        scene_camera: bool = True,
        audio: bool = False,
        eye_cameras: bool = False,
        gaze: bool = False,
        sync: bool = False,
        imu: bool = False,
        events: bool = False,
    ) -> AsyncIterator[Streams]:
        """Set up an RTSP connection in the form of a Streams object with the Stream properties indicated by the arguments.

        The Stream objects can be used to demux/decode their stream. For example, `stream_rtsp()` can be used as follows:
        ```python
        async with connect_to_glasses(g3_hostname) as g3:
            async with g3.stream_rtsp() as streams:
                async with streams.scene_camera.decode() as decoded_stream:
                    for _ in range(500):
                        frame, _timestamp = await decoded_stream.get()
                        image = frame.to_ndarray(format="bgr24")
                        cv2.imshow("Video", image)
                        cv2.waitKey(1)
        ```

        *Alpha version note:* Only the scene_camera, eye_camera and gaze attributes are implemented so far.
        """
        if self.rtsp_url is None:
            raise FeatureNotAvailableError(
                "This Glasses3 object was initialized without a proper RTSP url."
            )
        async with Streams.connect(
            self.rtsp_url,
            scene_camera=scene_camera,
            audio=audio,
            eye_cameras=eye_cameras,
            gaze=gaze,
            sync=sync,
            imu=imu,
            events=events,
        ) as streams:
            await streams.play()
            yield streams

    async def close(self) -> None:
        """Close down the underlying websocket connection to the Glasses3 device."""
        await self._connection.close()


class connect_to_glasses:
    """This class contains a set of classmethods which are used to connect to a pair of glasses.

    The preferred way to use this class is as an async context manager like this:

    ```python
    async with connect_to_glasses.with_hostname(glasses_serial_number) as g3:
        # Here you can call the glasses
        await g3.get_name()
    # Here the connection is closed
    ```

    It does however also support usage without a `with`-block like this:

    ```python
    g3 = await connect_to_glasses.with_hostname(glasses_serial_number)
    # Here you can call the glasses
    await g3.get_name()
    # You have to remember to close the connection like this:
    g3.close()
    # And here g3 still exists but it is unusable
    ```
    """

    def __init__(
        self,
        url_generator: Coroutine[Any, Any, Tuple[str, Optional[str], Optional[str]]],
    ) -> None:
        """You should probably not use this constructor unless you need to generate the URLs to your glasses in a very specific way.
        The regular use cases are covered in the alternative constructors below: `with_url`, `with_zeroconf`, `with_hostname` and `with_service`.

        If you want to use this constructor you need to supply a couroutine which returns a tuple that contains two URLs.
        The first URL should point to the websocket and the second URL should point to the RTSP endpoint.
        """
        self.url_generator = url_generator

    @staticmethod
    async def _urls_from_zeroconf(
        using_ip: bool, timeout: float
    ) -> Tuple[str, Optional[str], Optional[str]]:
        async with G3ServiceDiscovery.listen() as service_discovery:
            service = await service_discovery.wait_for_single_service(
                service_discovery.events,
                timeout,
            )
        return await connect_to_glasses._urls_from_service(service, using_ip)

    @staticmethod
    async def _urls_from_service(
        service: G3Service, using_ip: bool
    ) -> Tuple[str, Optional[str], Optional[str]]:
        return (
            service.ws_url(using_ip),
            service.rtsp_url(using_ip),
            service.http_url(using_ip),
        )

    @staticmethod
    async def _urls_from_hostname(
        hostname: str, using_zeroconf: bool, using_ip: bool
    ) -> Tuple[str, Optional[str], Optional[str]]:
        if not using_zeroconf:
            return (
                f"ws://{hostname}{DEFAULT_WEBSOCKET_PATH}",
                f"rtsp://{hostname}:{DEFAULT_RTSP_PORT}{DEFAULT_RTSP_LIVE_PATH}",
                f"http://{hostname}:{DEFAULT_HTTP_PORT}",
            )
        else:
            service = await G3ServiceDiscovery.request_service(hostname)
            return await connect_to_glasses._urls_from_service(service, using_ip)

    @classmethod
    def with_zeroconf(
        cls, using_ip: bool = True, timeout: float = 3000
    ) -> connect_to_glasses:
        """Connects by listening for available glasses on the network using zeroconf.
        Connects to the first pair of glasses that answers so if there are multiple glasses on the
        network the behavior is undefined.

        If `using_ip` is set to True (default) we will generate the the URL used for connection with the ip.
        If it's set to False we will use the hostname, which will depend on DNS working as it should.

        `timeout` defines the time in milliseconds before `asyncio.TimeoutError` is raised.
        """
        return cls(cls._urls_from_zeroconf(using_ip, timeout))

    @classmethod
    def with_hostname(
        cls, hostname: str, using_zeroconf: bool = False, using_ip: bool = True
    ) -> connect_to_glasses:
        """Connects to the pair of glasses with the given hostname.

        If `using_zeroconf` is set to False (default) we will not depend on zeroconf
        for fetching details on how to generate the URL and instead use detault values for the URL components specified
        in the [developer guide](https://www.tobiipro.com/product-listing/tobii-pro-glasses3-api/#ResourcesSpecifications).
        If it's set to True, all URL components are fetched with zeroconf.

        `using_ip` specifies if the ip or the hostname should be used in the URL used for connecting when zeroconf is used.
        If the hostname is used, it depends on DNS working as it should."""
        return cls(cls._urls_from_hostname(hostname, using_zeroconf, using_ip))

    @classmethod
    def with_service(
        cls, service: G3Service, using_ip: bool = True
    ) -> connect_to_glasses:
        """Connects to the pair of glasses referred to by the given service.

        `using_ip` specifies if the ip or the hostname should be used in the URL used for connecting.
        If the hostname is used, it depends on DNS working as it should.
        """
        return cls(cls._urls_from_service(service, using_ip))

    @classmethod
    def with_url(
        cls, ws_url: str, rtsp_url: Optional[str] = None, http_url: Optional[str] = None
    ):
        """Connects to the pair of glasses at the specified URL. `ws_url` should
        be a websocket URL (starting with `ws://`) and `rtsp_url` should be an RTSP
        url (starting with `rtsp://` or `rtspt://`)."""

        async def urls():
            return (ws_url, rtsp_url, http_url)

        return cls(urls())

    def __await__(self) -> Generator[Any, None, Glasses3]:
        return self.__await_impl__().__await__()

    async def __await_impl__(self) -> Glasses3:
        ws_url, rtsp_url, http_url = await self.url_generator
        _logger.info(
            f"Attempting connection to websocket {ws_url}, RTSP {rtsp_url} and HTTP {http_url}"
        )
        connection = cast(
            G3WebSocketClientProtocol, await g3pylib.websocket.connect(ws_url)
        )
        connection.start_receiver_task()
        self.connection = connection
        return Glasses3(connection, rtsp_url, http_url)

    async def __aenter__(self) -> Glasses3:
        return await self

    async def __aexit__(
        self,
        exception_type: Optional[Type[BaseException]],
        exception_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        await self.connection.close()
