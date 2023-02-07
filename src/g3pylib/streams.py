"""
*Alpha version note:* Only the scene_camera, eye_camera and gaze attributes are implemented so far.
"""

from __future__ import annotations

import asyncio
import functools
import json
import logging
from abc import ABC, abstractmethod, abstractproperty
from contextlib import AsyncExitStack, asynccontextmanager
from enum import Enum, auto
from functools import cached_property
from typing import Any, AsyncIterator, Dict, List, Optional, Set, Tuple, Union, cast
from urllib.parse import urlparse

import av  # type: ignore
from aiortsp.rtcp.parser import RTCP, SR  # type: ignore
from aiortsp.rtsp.connection import RTSPConnection  # type: ignore
from aiortsp.rtsp.session import (  # type: ignore
    MediaStreamConfiguration,
    MediaType,
    RTSPMediaSession,
)
from aiortsp.transport import (  # type: ignore
    RTPTransport,
    RTPTransportClient,
    transport_for_scheme,
)
from dpkt.rtp import RTP  # type: ignore

from g3pylib import _utils
from g3pylib.g3typing import JSONObject

TIMESTAMP_GRANULARITY = 90000
FRAME_QUEUE_SIZE = 10
DATA_QUEUE_SIZE = 100
RTCP_QUEUE_SIZE = 100

_logger: logging.Logger = logging.getLogger(__name__)


class StreamType(Enum):
    """Defines the different stream types in an RTSP stream."""

    SCENE_CAMERA = auto()
    AUDIO = auto()
    EYE_CAMERAS = auto()
    GAZE = auto()
    SYNC = auto()
    IMU = auto()
    EVENTS = auto()

    @property
    def property_name(self) -> str:
        """The stream type's property name as a string."""
        match self:
            case StreamType.SCENE_CAMERA:
                return "scene_camera"
            case StreamType.AUDIO:
                return "audio"
            case StreamType.EYE_CAMERAS:
                return "eye_cameras"
            case StreamType.GAZE:
                return "gaze"
            case StreamType.SYNC:
                return "sync"
            case StreamType.IMU:
                return "imu"
            case StreamType.EVENTS:
                return "events"


class NALUnit:
    """Represents a RTP or H264 NAL unit

    The structure of RTP NAL units are described in detail in [RFC 6184](https://www.rfc-editor.org/rfc/rfc6184)
    and H.264 NAL units are described in the [H.264 specification](https://www.itu.int/rec/T-REC-H.264/en)
    """

    _START_CODE_PREFIX = b"\x00\x00\x01"
    _F_MASK = 0b10000000
    _F_SHIFT = 7
    _NRI_MASK = 0b01100000
    _NRI_SHIFT = 5
    _TYPE_MASK = 0b00011111
    _TYPE_SHIFT = 0
    _S_MASK = 0b10000000
    _S_SHIFT = 7
    _E_MASK = 0b01000000
    _E_SHIFT = 6
    _R_MASK = 0b00100000
    _R_SHIFT = 5

    data: bytearray
    """Header and payload."""

    def __init__(self, data: Union[bytes, bytearray, memoryview]) -> None:
        self.data = bytearray(data)

    @cached_property
    def f(self) -> int:
        """Forbidden zero bit."""
        return (self.header & self._F_MASK) >> self._F_SHIFT

    @cached_property
    def nri(self) -> int:
        """NAL ref IDC."""
        return (self.header & self._NRI_MASK) >> self._NRI_SHIFT

    @cached_property
    def type(self) -> int:
        """NAL unit type."""
        return (self.header & self._TYPE_MASK) >> self._TYPE_SHIFT

    @cached_property
    def header(self) -> int:
        """The header of the NAL unit or FU indicator in the case of a fragmentation unit."""
        return self.data[0]

    @property
    def payload(self) -> bytes:
        """The payload of the NAL unit."""
        if isinstance(self, FUA):
            return self.data[2:]
        return self.data[1:]

    @property
    def data_with_prefix(self) -> bytes:
        """The header and payload of the NAL unit with start code prefix prepended."""
        return self._START_CODE_PREFIX + self.data

    @classmethod
    def from_rtp_payload(cls, rtp_payload: bytes) -> NALUnit:
        """Constructs `NALUnit` from an rtp payload."""
        nal_unit = cls(rtp_payload)
        if nal_unit.type == 28:
            return FUA(rtp_payload)
        return nal_unit

    @classmethod
    def from_fu_a(cls, fu_a: FUA) -> NALUnit:
        """Constructs `NALUnit` from an FUA.

        Note that fragmented NAL unit payloads must be aggregated before they can get parsed.
        """
        header = fu_a.header & (cls._F_MASK | cls._NRI_MASK) | fu_a.original_type
        data = bytearray()
        data.append(header)
        data += fu_a.payload
        return cls(data)


class FUA(NALUnit):
    """A specific type of RTP NAL unit called FU-A (Fragmentation Unit type A).
    Described in detail in RFC 6184 section [5.8](https://datatracker.ietf.org/doc/html/rfc6184#section-5.8).
    """

    @cached_property
    def s(self) -> int:
        """Start bit for fragmentation unit."""
        return (self.fu_header & self._S_MASK) >> self._S_SHIFT

    @cached_property
    def e(self) -> int:
        """End bit for fragmentation unit."""
        return (self.fu_header & self._E_MASK) >> self._E_SHIFT

    @cached_property
    def original_type(self) -> int:
        """The type of the NAL unit contained in the fragmentation unit."""
        return (self.fu_header & self._TYPE_MASK) >> self._TYPE_SHIFT

    @cached_property
    def fu_header(self) -> int:
        """The extra header in fragmentation units."""
        return self.data[1]


class Stream(RTPTransportClient, ABC):
    """Abstract class for a RTSP media stream."""

    transport: RTPTransport
    """A wrapper around a pair of UDP (or TCP) sockets."""
    rtp_queue: asyncio.Queue[Tuple[RTP, Optional[float]]]
    """The queue where all received raw RTP packets get queued for demuxing and decoding."""
    rtcp_queue: asyncio.Queue[RTCP]
    """The queue where all received raw RTCP packets get queued for demuxing and decoding."""
    type: StreamType
    """The type of this media stream. For example scene camera or gaze."""
    _last_rtcp_timestamp: Optional[int]
    _last_ntp_time: Optional[float]

    def __init__(self, transport: RTPTransport, type: StreamType) -> None:
        transport.subscribe(self)
        self.transport = transport
        self.rtp_queue = asyncio.Queue()
        self.rtcp_queue = asyncio.Queue(RTCP_QUEUE_SIZE)
        self.type = type
        self._last_rtcp_timestamp = None
        self._last_ntp_time = None

    def handle_rtp(self, rtp: RTP) -> None:
        """A callback which is called everytime a new RTP packet is received. Queues the packet and
        calculates its absolute NTP timestamp."""
        if self._last_ntp_time is not None and self._last_rtcp_timestamp is not None:
            time_delta = cast(int, rtp.ts) - self._last_rtcp_timestamp  # type: ignore
            ntp_timestamp = self._last_ntp_time + time_delta / TIMESTAMP_GRANULARITY
        else:
            ntp_timestamp = None
        self.rtp_queue.put_nowait((rtp, ntp_timestamp))
        # _logger.debug(f"{self.type}: {rtp.ts}")
        # _logger.debug(f"RTP size: {len(rtp.data)}")

    def handle_rtcp(self, rtcp: RTCP) -> None:
        """A callback which is called everytime a new RTCP packet is received. Queues the packet and
        extracts information needed for calculations of absolute time."""
        try:
            self.rtcp_queue.put_nowait(rtcp)
        except asyncio.QueueFull:
            _logger.warning(
                "RTCP queue full. New RTCP packages will be thrown away. Consume the queue to prevent this from happening."
            )
        sender_report = cast(Optional[SR], rtcp.get(200))
        if sender_report is None:
            return
        self._last_ntp_time = sender_report.ntp
        self._last_rtcp_timestamp = sender_report.ts

    @abstractproperty
    def stats(self) -> Dict[str, int]:
        """Should contain some media stream statistics. Used mainly for debugging purposes."""
        raise NotImplementedError

    @property
    def media_stream_configuration(self) -> MediaStreamConfiguration:
        """A `MediaStreamConfiguration` for this media stream which is used for configuring the `RTSPMediaSession`"""
        return MediaStreamConfiguration(
            self.transport, self.media_type, self.media_index
        )

    @abstractproperty
    def media_type(self) -> MediaType:
        """Should be the media type identifier of the `Stream` subclass."""
        raise NotImplementedError

    @property
    def media_index(self) -> int:
        """The media index of the stream.

        Every separate media stream in the RTSP media session is identified by its `media_type` and its `media_index`.
        """
        match self.type:
            case StreamType.SCENE_CAMERA:
                return 0
            case StreamType.AUDIO:
                return 0
            case StreamType.EYE_CAMERAS:
                return 1
            case StreamType.GAZE:
                return 0
            case StreamType.SYNC:
                return 1
            case StreamType.IMU:
                return 2
            case StreamType.EVENTS:
                return 3

    @classmethod
    @asynccontextmanager
    async def setup(
        cls, connection: RTSPConnection, stream_type: StreamType, scheme: str
    ) -> AsyncIterator[Stream]:
        """The main entry point of a `Stream`.

        Sets up a transport for RTP and RTCP packets and instantiates a `Stream` object containing the transport.
        """
        transport_class = transport_for_scheme(scheme)
        async with transport_class(connection) as transport:
            yield cls(transport, stream_type)

    @abstractmethod
    @asynccontextmanager
    async def demux(self) -> AsyncIterator[asyncio.Queue[Tuple[Any, Optional[float]]]]:
        """Should return a queue with tuples containing the demuxed RTP stream along with timestamps."""
        raise NotImplementedError
        yield

    @abstractmethod
    @asynccontextmanager
    async def decode(self) -> AsyncIterator[asyncio.Queue[Tuple[Any, Optional[float]]]]:
        """Should return a queue with tuples containing the demuxed and decoded RTP stream along with timestamps."""
        raise NotImplementedError
        yield


class DataStream(Stream):
    def __init__(self, transport: RTPTransport, stream_type: StreamType) -> None:
        super().__init__(transport, stream_type)

    @property
    def media_type(self) -> MediaType:
        return "application"

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "samples": 0,
        }

    @asynccontextmanager
    async def demux(
        self,
    ) -> AsyncIterator[asyncio.Queue[Tuple[bytes, Optional[float]]]]:
        data_queue: asyncio.Queue[Tuple[bytes, Optional[float]]] = asyncio.Queue(
            DATA_QUEUE_SIZE
        )

        async def demuxer():
            while True:
                rtp, timestamp = await self.rtp_queue.get()
                await data_queue.put((cast(bytes, rtp.data), timestamp))  # type: ignore

        demuxer_task = _utils.create_task(demuxer(), name="demuxer")
        try:
            yield data_queue
        finally:
            demuxer_task.cancel()
            try:
                await demuxer_task
            except asyncio.CancelledError:
                pass

    @asynccontextmanager
    async def decode(
        self,
    ) -> AsyncIterator[asyncio.Queue[Tuple[JSONObject, Optional[float]]]]:
        json_queue: asyncio.Queue[Tuple[JSONObject, Optional[float]]] = asyncio.Queue(
            DATA_QUEUE_SIZE
        )

        async def decoder():
            async with self.demux() as data_queue:
                while True:
                    data, timestamp = await data_queue.get()
                    try:
                        json_message: JSONObject = json.loads(data)
                    except json.JSONDecodeError:
                        _logger.debug(
                            f"Received data that couldn't be decoded{' since it was empty.' if len(data) == 0 else '.'}"
                        )
                        continue
                    await json_queue.put((json_message, timestamp))

        decoder_task = _utils.create_task(decoder(), name="decoder")
        try:
            yield json_queue
        finally:
            decoder_task.cancel()
            try:
                await decoder_task
            except asyncio.CancelledError:
                pass


class VideoStream(Stream):
    """Represents a RTSP video stream.

    Handles demuxing and decoding of video frames.
    """

    _nal_unit_builder: Tuple[NALUnit, Optional[float]]

    def __init__(self, transport: RTPTransport, stream_type: StreamType) -> None:
        super().__init__(transport, stream_type)
        self.codec_context: Any = av.CodecContext.create("h264", "r")  # type: ignore
        self.sps_or_pps_received = False
        self._demux_in_count = 0
        self._demux_out_count = 0
        self._decode_count = 0
        self._fragment_count = 0

    @property
    def media_type(self) -> MediaType:
        """The media type identifier of a `VideoStream`."""
        return "video"

    @property
    def stats(self) -> Dict[str, int]:
        """Contains some media stream statistics. Used mainly for debugging purposes."""
        return {
            "demux_in_count": self._demux_in_count,
            "demux_out_count": self._demux_out_count,
            "decode_count": self._decode_count,
        }

    @asynccontextmanager
    async def demux(
        self,
    ) -> AsyncIterator[asyncio.Queue[Tuple[NALUnit, Optional[float]]]]:
        """Returns a queue with tuples containing the demuxed RTP stream along with timestamps.

        Spawns a demuxer task which parses the NAL units received in the RTP payloads.
        It also aggregates fragmentation units of larger NAL units sent in multiple RTP packets.
        """
        nal_unit_queue: asyncio.Queue[Tuple[NALUnit, Optional[float]]] = asyncio.Queue(
            FRAME_QUEUE_SIZE
        )

        async def demuxer():
            while True:
                rtp, timestamp = await self.rtp_queue.get()
                self._demux_in_count += 1
                # t0 = time.perf_counter()
                nal_unit = NALUnit.from_rtp_payload(cast(bytes, rtp.data))  # type: ignore
                if nal_unit.type in [7, 8]:
                    # SPS or PPS is queued
                    self.sps_or_pps_received = True
                    await nal_unit_queue.put((nal_unit, timestamp))
                    self._demux_out_count += 1
                    continue
                if not self.sps_or_pps_received:
                    # SPS or PPS should be the first NAL unit to be queued
                    continue
                if nal_unit.type in [1, 5]:
                    # Self contained NAL unit is queued
                    await nal_unit_queue.put((nal_unit, timestamp))
                    self._demux_out_count += 1
                    continue
                if isinstance(nal_unit, FUA):
                    # Fragmented NAL units need to be aggregated
                    if nal_unit.s:
                        self._nal_unit_builder = (
                            NALUnit.from_fu_a(nal_unit),
                            timestamp,
                        )
                        self._fragment_count = 1
                        # t1 = time.perf_counter()
                        # logger.debug(f"Demuxed FU-A start in {t1 - t0:.6f} seconds")
                        continue
                    self._nal_unit_builder[0].data += nal_unit.payload
                    self._fragment_count += 1
                    # t1 = time.perf_counter()
                    # logger.debug(f"Demuxed FU-A in {t1 - t0:.6f} seconds")
                    if nal_unit.e:
                        # logger.debug(f"NAL unit built of {self._fragment_count} FU-As")
                        await nal_unit_queue.put(self._nal_unit_builder)
                        self._demux_out_count += 1
                else:
                    _logger.warning(f"Unhandled NAL unit of type {nal_unit.type}")

        demuxer_task = _utils.create_task(demuxer(), name="demuxer")
        try:
            yield nal_unit_queue
        finally:
            demuxer_task.cancel()
            try:
                await demuxer_task
            except asyncio.CancelledError:
                pass

    @asynccontextmanager
    async def decode(self) -> AsyncIterator[asyncio.Queue[Tuple[Any, Optional[float]]]]:
        """Returns a queue with tuples containing the demuxed and decoded RTP stream along with timestamps.

        Spawns a decoder task which uses PyAV (ffmpeg) to parse and decode the demuxed NAL units.

        The returned queue contains PyAVs `av.VideoFrame` objects along with timestamps.
        """
        frame_queue: asyncio.Queue[Tuple[Any, Optional[float]]] = asyncio.Queue(
            FRAME_QUEUE_SIZE
        )

        async def decoder():
            async with self.demux() as nal_unit_queue:
                while True:
                    nal_unit, timestamp = await nal_unit_queue.get()
                    # t0 = time.perf_counter()
                    packets = cast(
                        List[Any],
                        self.codec_context.parse(nal_unit.data_with_prefix),
                    )
                    frames = functools.reduce(
                        lambda frame_acc, packet: frame_acc
                        + self.codec_context.decode(packet),
                        packets,
                        [],
                    )
                    # t1 = time.perf_counter()
                    # logger.debug(f"Decoded NAL unit in {t1 - t0:.6f} seconds")
                    for frame in frames:
                        await frame_queue.put((frame, timestamp))
                        self._decode_count += 1

        decoder_task = _utils.create_task(decoder(), name="decoder")
        try:
            yield frame_queue
        finally:
            decoder_task.cancel()
            try:
                await decoder_task
            except asyncio.CancelledError:
                pass


class Streams:
    """Handles a `RTSPMediaSession` with one or multiple media streams.

    Exposes a `connect` function which is used to set up an RTSP media session and create an instance of this object.
    Gives easy access to the different streams.

    After the setup process is completed, await the `play` coroutine to start the streaming.
    """

    def __init__(self, session: RTSPMediaSession, streams: Set[Stream]) -> None:
        self.session = session
        self.streams: Dict[StreamType, Stream] = {
            stream.type: stream for stream in streams
        }

    @property
    def scene_camera(self) -> VideoStream:
        return cast(VideoStream, self._get_stream(StreamType.SCENE_CAMERA))

    @property
    def audio(self) -> Stream:
        return self._get_stream(StreamType.AUDIO)

    @property
    def eye_cameras(self) -> Stream:
        return self._get_stream(StreamType.EYE_CAMERAS)

    @property
    def gaze(self) -> Stream:
        return self._get_stream(StreamType.GAZE)

    @property
    def sync(self) -> Stream:
        return self._get_stream(StreamType.SYNC)

    @property
    def imu(self) -> Stream:
        return self._get_stream(StreamType.IMU)

    @property
    def events(self) -> Stream:
        return self._get_stream(StreamType.EVENTS)

    def _get_stream(self, stream_type: StreamType) -> Stream:
        try:
            return self.streams[stream_type]
        except KeyError:
            raise AttributeError(
                f"The {stream_type.name} stream was never initialized.",
                name=stream_type.property_name,  # type: ignore
                obj=self,  # type: ignore
            )

    @classmethod
    @asynccontextmanager
    async def connect(
        cls,
        rtsp_url: str,
        scene_camera: bool = True,
        audio: bool = False,
        eye_cameras: bool = False,
        gaze: bool = False,
        sync: bool = False,
        imu: bool = False,
        events: bool = False,
    ) -> AsyncIterator[Streams]:
        """Sets up an RTSP media session with the specified streams and creates an instance of `Streams`."""
        parsed_url = urlparse(rtsp_url)
        async with RTSPConnection(parsed_url.hostname, parsed_url.port) as connection:
            async with AsyncExitStack() as stack:
                streams: Set[Stream] = set()
                if scene_camera:
                    streams.add(
                        await stack.enter_async_context(
                            VideoStream.setup(
                                connection, StreamType.SCENE_CAMERA, parsed_url.scheme
                            )
                        )
                    )
                if eye_cameras:
                    streams.add(
                        await stack.enter_async_context(
                            VideoStream.setup(
                                connection, StreamType.EYE_CAMERAS, parsed_url.scheme
                            )
                        )
                    )
                if gaze:
                    streams.add(
                        await stack.enter_async_context(
                            DataStream.setup(
                                connection, StreamType.GAZE, parsed_url.scheme
                            )
                        )
                    )
                if audio or sync or imu or events:
                    raise NotImplementedError()

                async with RTSPMediaSession(
                    connection,
                    rtsp_url,
                    media_stream_configurations=list(
                        map(lambda s: s.media_stream_configuration, streams)
                    ),
                ) as session:
                    yield cls(session, streams)

    async def play(self) -> None:
        """Starts the streaming in the RTSP media session."""
        await self.session.play()  # type: ignore
