from logging import Logger, LoggerAdapter
from typing import TYPE_CHECKING, Any, Dict, List, NewType, Union

if TYPE_CHECKING:
    LoggerLike = Union[Logger, LoggerAdapter[Any]]
else:
    LoggerLike = Union[Logger, LoggerAdapter]
MessageId = NewType("MessageId", int)
"""An id corresponding to a request-response pair of messages on the websocket."""
URI = NewType("URI", str)
"""URI for an for API endpoint."""
JSONObject = Union[int, str, bool, Dict[str, "JSONObject"], List["JSONObject"], None]
"""An attribute with the structure of a JSON object."""
JSONDict = Dict[str, JSONObject]
"""An attribute with the structure of a JSON dict."""
SignalId = NewType("SignalId", str)
"""An id corresponding to a Glasses3-signal."""
SignalBody = NewType("SignalBody", List[JSONObject])
"""The body of a received signal websocket message."""
SubscriptionId = NewType("SubscriptionId", int)
"""An id corresponding to a subscription to a Glasses3-signal."""
