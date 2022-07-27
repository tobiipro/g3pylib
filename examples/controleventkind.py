from enum import Enum, auto


class ControlEventKind(Enum):
    START_RECORDING = auto()
    STOP_RECORDING = auto()
    DELETE_RECORDING = auto()
