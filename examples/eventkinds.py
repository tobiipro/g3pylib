from enum import Enum, auto
from http.client import CONTINUE


class ControlEventKind(Enum):
    START_RECORDING = auto()
    STOP_RECORDING = auto()
    DELETE_RECORDING = auto()


class AppEventKind(Enum):
    ENTER_CONTROL_SESSION = auto()
    LEAVE_CONTROL_SESSION = auto()
    START_DISCOVERY = auto()
    STOP = auto()
