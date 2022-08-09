from enum import Enum, auto


class ControlEventKind(Enum):
    START_RECORDING = auto()
    STOP_RECORDING = auto()
    DELETE_RECORDING = auto()


class AppEventKind(Enum):
    ENTER_CONTROL_SESSION = auto()
    LEAVE_CONTROL_SESSION = auto()
    STOP_CONTROL = auto()
    START_DISCOVERY = auto()
    STOP_DISCOVERY = auto()
    STOP = auto()
    STOP_HANDLE_CONTROL_EVENTS = auto()
    START_HANDLE_CONTROL_EVENTS = auto()
