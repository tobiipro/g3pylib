from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Set, Type, TypeVar
from urllib.parse import urlparse

from aiortsp.transport import RTPTransport
from av import VideoFrame
from dpkt.rtp import RTP

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
    """Represents a RTP or H264 NAL Unit

    The structure of RTP NAL Units are described in detail in [RFC 6184](https://www.rfc-editor.org/rfc/rfc6184)
    and H.264 NAL Units are described in the [H.264 specification](https://www.itu.int/rec/T-REC-H.264/en)
    """

    _START_CODE_PREFIX = b"\x00\x00\x01"
    _F_MASK = 0b10000000
    _F_SHIFT = 7
    _NRI_MASK = 0b01100000
    _NRI_SHIFT = 5
    _F_NRI_MASK = 0b11100000
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
    """The header of the NAL Unit"""
    payload: bytes
    """The payload of the NAL Unit"""
    data: bytes
    """Header and payload"""

    @classmethod
    def from_bytes(cls, data: bytes) -> NALUnit:
        header = data[0]
        f = (header & cls._F_MASK) >> cls._F_SHIFT
        nri = (header & cls._NRI_MASK) >> cls._NRI_SHIFT
        type = (header & cls._TYPE_MASK) >> cls._TYPE_SHIFT
        if type == 28:
            fu_header = data[1]
            s = (header & cls._S_MASK) >> cls._S_SHIFT
            e = (header & cls._E_MASK) >> cls._E_SHIFT
            r = (header & cls._R_MASK) >> cls._R_SHIFT
            payload = data[2:]
            return FUA(f, nri, type, header, payload, data, fu_header, s, e, r)
        payload = data[1:]
        return cls(f, nri, type, header, payload, data)


@dataclass
class FUA(NALUnit):
    fu_header: int
    """The extra header in fragmentation units"""
    s: int
    """Start bit for fragmentation unit"""
    e: int
    """End bit for fragmentation unit"""
    r: int
    """Reserved bit for fragmentation unit"""


class Stream:
    transport: RTPTransport
    queue: asyncio.Queue[RTP]
    type: StreamType

    def __init__(
        self,
    ) -> None:
        raise NotImplementedError

    def demux(self) -> asyncio.Queue[NALUnit]:
        raise NotImplementedError

    def decode(self) -> asyncio.Queue[VideoFrame]:
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
        except KeyError as e:
            raise AttributeError(
                f"The {stream_type.name} stream was never initialized.",
                name=stream_type.property_name,
                obj=self,
            ) from e

    @classmethod
    def connect(cls, scene_camera: bool = True, gaze: bool = False) -> Streams:
        raise NotImplementedError

    def play(self) -> None:
        raise NotImplementedError
