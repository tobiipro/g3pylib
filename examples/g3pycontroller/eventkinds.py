from enum import Enum, auto


class ControlEventKind(Enum):
    START_RECORDING = auto()
    STOP_RECORDING = auto()
    DELETE_RECORDING = auto()
    START_LIVE = auto()
    STOP_LIVE = auto()
    PLAY_RECORDING = auto()


class AppEventKind(Enum):
    ENTER_CONTROL_SESSION = auto()
    LEAVE_CONTROL_SESSION = auto()
    START_DISCOVERY = auto()
    STOP = auto()
