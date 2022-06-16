from logging import Logger, LoggerAdapter
from typing import TYPE_CHECKING, Any, Dict, List, NewType, Union

if TYPE_CHECKING:
    LoggerLike = Union[Logger, LoggerAdapter[Any]]
else:
    LoggerLike = Union[Logger, LoggerAdapter]
Hostname = NewType("Hostname", str)
MessageId = NewType("MessageId", int)
UriPath = NewType("UriPath", str)
JsonDict = Dict[str, Any]
SignalType = NewType("SignalType", str)
SignalId = NewType("SignalId", str)
SignalBody = NewType("SignalBody", List[Any])
SubscriptionId = NewType("SubscriptionId", int)
