from logging import Logger, LoggerAdapter
from typing import Any, Dict, NewType, Union

LoggerLike = Union[Logger, LoggerAdapter[Any]]
Hostname = NewType("Hostname", str)
MessageId = NewType("MessageId", int)
UriPath = NewType("UriPath", str)
JsonDict = Dict[str, Any]
