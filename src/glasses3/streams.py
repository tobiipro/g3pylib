from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import AsyncIterator, Dict, Optional, Set, TypeVar, Union, cast
from urllib.parse import urlparse

import av
from aiortsp.rtcp.parser import RTCP
from aiortsp.transport import RTPTransport, RTPTransportClient
from dpkt.rtp import RTP

from glasses3 import Glasses3, utils

T = TypeVar("T")


class StreamType(Enum):
    SCENE_CAMERA = auto()
    AUDIO = auto()
    EYE_CAMERAS = auto()
    GAZE = auto()
    SYNC = auto()
    IMU = auto()
    EVENTS = auto()

    @property
    def property_name(self) -> str:
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


@dataclass
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

    f: int
    """Forbidden zero bit"""
    nri: int
    """NAL ref IDC"""
    type: int
    """NAL unit type"""
    header: int
    """The header of the NAL unit or FU indicator in the case of a fragamentation unit"""
    payload: Union[bytes, bytearray]
    """The payload of the NAL unit"""
    data: Optional[bytes] = field(default=None, init=False)
    """Header and payload"""

    @classmethod
    def from_rtp_payload(cls, rtp_payload: bytes) -> NALUnit:
        header = rtp_payload[0]
        f = (header & cls._F_MASK) >> cls._F_SHIFT
        nri = (header & cls._NRI_MASK) >> cls._NRI_SHIFT
        type = (header & cls._TYPE_MASK) >> cls._TYPE_SHIFT
        if type == 28:
            fu_header = rtp_payload[1]
            s = (fu_header & cls._S_MASK) >> cls._S_SHIFT
            e = (fu_header & cls._E_MASK) >> cls._E_SHIFT
            original_type = (fu_header & cls._TYPE_MASK) >> cls._TYPE_SHIFT
            payload = rtp_payload[2:]
            return FUA(f, nri, type, header, payload, s, e, original_type, fu_header)
        payload = rtp_payload[1:]
        return cls(f, nri, type, header, payload)

    @classmethod
    def from_fu_a(cls, fu_a: FUA):
        header = fu_a.f | fu_a.nri | fu_a.original_type
        payload = bytearray()
        payload += fu_a.payload
        return cls(fu_a.f, fu_a.nri, fu_a.original_type, header, payload)


@dataclass
class FUA(NALUnit):
    """A specific type of RTP NAL unit called FU-A (Fragmentation Unit type A).
    Described in detail in RFC 6184 section [5.8](https://datatracker.ietf.org/doc/html/rfc6184#section-5.8)."""

    s: int
    """Start bit for fragmentation unit"""
    e: int
    """End bit for fragmentation unit"""
    original_type: int
    """The type of the NAL unit contained in the fragmentation unit"""
    fu_header: int
    """The extra header in fragmentation units"""


class Stream(RTPTransportClient):
    transport: RTPTransport
    rtp_queue: asyncio.Queue[RTP]
    rtcp_queue: asyncio.Queue[RTCP]
    type: StreamType
    nal_unit_builder: NALUnit

    def __init__(
        self,
    ) -> None:
        raise NotImplementedError

    def handle_rtp(self, rtp: RTP) -> None:
        self.rtp_queue.put_nowait(rtp)

    def handle_rtcp(self, rtcp: RTCP) -> None:
        self.rtcp_queue.put_nowait(rtcp)

    @asynccontextmanager
    async def demux(self) -> AsyncIterator[asyncio.Queue[NALUnit]]:
        nal_unit_queue: asyncio.Queue[NALUnit] = asyncio.Queue()

        async def demuxer():
            while True:
                rtp = await self.rtp_queue.get()
                # TODO: Should maybe run in processpool
                nal_unit = NALUnit.from_rtp_payload(cast(bytes, rtp.data))  # type: ignore
                if nal_unit.type in [7, 8]:
                    await nal_unit_queue.put(nal_unit)
                if isinstance(nal_unit, FUA):
                    if nal_unit.s:
                        self.nal_unit_builder = NALUnit.from_fu_a(nal_unit)
                        continue
                    self.nal_unit_builder.payload += nal_unit.payload
                    if nal_unit.e:
                        await nal_unit_queue.put(self.nal_unit_builder)

        demuxer_task = utils.create_task(demuxer())
        yield nal_unit_queue
        demuxer_task.cancel()
        await demuxer_task

    def decode(self) -> AsyncIterator[asyncio.Queue[av.VideoFrame]]:
        raise NotImplementedError


class Streams:
    def __init__(self, url: str, streams: Set[Stream]) -> None:
        self.parsed_url = urlparse(url)
        self.media_url = url
        self.streams: Dict[StreamType, Stream] = {
            stream.type: stream for stream in streams
        }

    @property
    def scene_camera(self) -> Stream:
        return self._get_stream(StreamType.SCENE_CAMERA)

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
    async def connect_using_g3(
        cls,
        g3: Glasses3,
        scene_camera: bool = True,
        audio: bool = False,
        eye_cameras: bool = False,
        gaze: bool = False,
        sync: bool = False,
        imu: bool = False,
        events: bool = False,
    ) -> AsyncIterator[Streams]:
        raise NotImplementedError
        yield cls()

    def play(self) -> None:
        raise NotImplementedError
