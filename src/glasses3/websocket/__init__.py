from __future__ import annotations

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Awaitable, Dict, List, Optional, Tuple, Type, cast

import websockets
import websockets.client
import websockets.legacy.client
from websockets.client import connect as websockets_connect
from websockets.typing import Subprotocol

from ..g3typing import (
    Hostname,
    JSONDict,
    JSONObject,
    MessageId,
    SignalBody,
    SignalId,
    SubscriptionId,
    UriPath,
)
from .exceptions import InvalidResponseError, UnsubscribeError

DEFAULT_WEBSOCKET_PATH = UriPath("/websocket")


def connect(
    g3_hostname: Hostname, websocket_path: UriPath = DEFAULT_WEBSOCKET_PATH
) -> websockets.legacy.client.Connect:
    """Sets up a websocket connection with a Glasses3 device.

    Uses WebSocketClientProtocol from websockets to create a connection with the supplied hostname
    and websocket path.

    Takes the hostname (which by default is the serial number of the recording unit) and websocket
    connection path as input.

    Returns a Connect object that communicates with Glasses3.
    """
    ws_uri = "ws://{}{}".format(g3_hostname, websocket_path)
    return websockets_connect(
        ws_uri,
        create_protocol=G3WebSocketClientProtocol.factory,
        subprotocols=G3WebSocketClientProtocol.DEFAULT_SUBPROTOCOLS,
    )


class SignalSubscriptionHandler(ABC):
    """Manages (un)subscriptions to Glasses3 signals.

    Keeps track of all current subscriptions and adds/removes subscriptions as needed. Upon any
    signal event all subscribers get the body of the response added to a queue to be handled.
    """

    def _init_signal_subscription_handling(self) -> None:
        """Initialize a subclass inheriting `SignalSubscriptionHandler` with the properties needed
        to handle signal subscriptions. **Has to be run in the constructor of the inheriting subclass.**"""
        self._subscription_count = 0
        self._signal_id_by_path: Dict[UriPath, SignalId] = {}
        self._signal_queues_by_id: Dict[
            SignalId, Dict[SubscriptionId, asyncio.Queue[SignalBody]]
        ] = defaultdict(dict)

    async def subscribe_to_signal(
        self, signal_uri_path: UriPath
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        """Sets up a subscription to the signal with the specified `signal_uri_path`.

        Returns a tuple with a queue and an awaitable. Upon receiving signals messages, the message
        body is added to the queue. The awaitable can be awaited to unsubscribe to the signal.
        """
        self._subscription_count += 1
        signal_id = self._signal_id_by_path.get(signal_uri_path)
        if signal_id is None:
            signal_id = self._signal_id_by_path[
                signal_uri_path
            ] = await self._require_post_subscribe(signal_uri_path)

        signal_queue: asyncio.Queue[SignalBody] = asyncio.Queue()
        self._signal_queues_by_id[signal_id][
            SubscriptionId(self._subscription_count)
        ] = signal_queue
        return (
            signal_queue,
            self._unsubscribe_to_signal(
                signal_uri_path,
                signal_id,
                SubscriptionId(self._subscription_count),
            ),
        )

    async def _unsubscribe_to_signal(
        self,
        signal_uri_path: UriPath,
        signal_id: SignalId,
        subscription_id: SubscriptionId,
    ) -> None:
        """Unsubscribes to the signal with the specified `subscription_id`."""
        signal_queues = self._signal_queues_by_id[signal_id]
        del signal_queues[subscription_id]
        if len(signal_queues) == 0:
            if not await self._require_post_unsubscribe(signal_uri_path, signal_id):
                raise UnsubscribeError
            del self._signal_id_by_path[signal_uri_path]

    def receive_signal(self, signal_id: SignalId, signal_body: SignalBody):
        """Passes on received signal message body with the specified `signal_id` to all
        subscribed queues."""

        for signal_queue in self._signal_queues_by_id[signal_id].values():
            signal_queue.put_nowait(SignalBody(signal_body.copy()))

    @abstractmethod
    async def _require_post_subscribe(self, signal_uri_path: UriPath) -> SignalId:
        """Should send a signal subscription post request over the inheriting subclass protocol and
        retrieve a signal id."""
        raise NotImplementedError

    @abstractmethod
    async def _require_post_unsubscribe(
        self, signal_uri_path: UriPath, signal_id: SignalId
    ) -> bool:
        """Should send a signal unsubscription post request over the inheriting subclass protocol
        and return a boolean indicating its success."""
        raise NotImplementedError


class G3WebSocketClientProtocol(
    websockets.client.WebSocketClientProtocol, SignalSubscriptionHandler
):
    DEFAULT_SUBPROTOCOLS = [Subprotocol("g3api")]

    def __init__(
        self, *, subprotocols: Optional[List[Subprotocol]] = None, **kwargs: Any
    ):
        """Initializes super class properties and additional properties needed for the communication."""
        self.g3_logger = logging.getLogger(__name__)
        self._message_count = 0
        self._future_messages: Dict[MessageId, asyncio.Future[JSONObject]] = {}
        self._event_loop = asyncio.get_running_loop()
        if subprotocols is None:
            subprotocols = self.DEFAULT_SUBPROTOCOLS
        # Type ignored since websockets has not typed this function as strictly as pyright wants
        super().__init__(subprotocols=subprotocols, **kwargs)  # type: ignore
        self._init_signal_subscription_handling()

    @classmethod
    def factory(
        cls: Type[G3WebSocketClientProtocol], *args: Any, **kwargs: Any
    ) -> G3WebSocketClientProtocol:
        """This is needed to deal with typing problems since the websockets.connect parameter
        create_protocol takes a callable as input.

        For example, a connection can be established as follows:
        ```python
        async with websockets.client.connect(
            "ws://{}/websockets".format(g3_hostname),
            create_protocol=G3WebSocketClientProtocol.factory,
        ) as g3ws:
            g3ws = cast(G3WebSocketClientProtocol, g3ws)
            g3ws.start_receiver_task()
            ...
        ```
        """
        return cls(*args, **kwargs)

    def start_receiver_task(self) -> None:
        """Creates a task handling all incoming messages."""
        self.g3_logger.debug("Receiver task starting")
        self._receiver = asyncio.create_task(self._receiver_task(), name="g3_receiver")

    async def _receiver_task(self) -> None:
        """Listens for and handles/delegates incoming messages."""
        async for message in self:
            json_message: JSONObject = json.loads(message)
            self.g3_logger.info(f"Received {json_message}")
            match json_message:
                case {"id": message_id, "body": message_body}:
                    del json_message["id"]
                    self._future_messages[cast(MessageId, message_id)].set_result(
                        message_body
                    )
                case {"signal": signal_id, "body": signal_body}:
                    self.receive_signal(
                        cast(SignalId, signal_id), cast(SignalBody, signal_body)
                    )
                case _:
                    raise InvalidResponseError

    async def require(self, request: JSONDict) -> JSONObject:
        """Sends a request  with a unique id and returns the response."""
        self._message_count += 1
        request["id"] = self._message_count
        string_request_with_id = json.dumps(request)
        await self.send(string_request_with_id)
        future = self._future_messages[
            MessageId(self._message_count)
        ] = self._event_loop.create_future()
        return await future

    async def require_get(
        self, path: UriPath, params: Optional[JSONObject] = None
    ) -> JSONObject:
        """Sends a GET request and returns the response."""
        return await self.require(self.generate_get_request(path, params))

    async def require_post(
        self, path: UriPath, body: Optional[JSONObject] = None
    ) -> JSONObject:
        """Sends a POST request and returns the response."""
        return await self.require(self.generate_post_request(path, body))

    async def _require_post_subscribe(self, signal_uri_path: UriPath) -> SignalId:
        """Sends a subscription POST request and returns the signal id specified in the response."""
        return cast(SignalId, await self.require_post(signal_uri_path))

    async def _require_post_unsubscribe(
        self, signal_uri_path: UriPath, signal_id: SignalId
    ) -> bool:
        """Sends an unsubscription POST request and returns a boolean indicating its success."""
        return cast(bool, await self.require_post(signal_uri_path, signal_id))

    @staticmethod
    def generate_get_request(
        path: UriPath, params: Optional[JSONObject] = None
    ) -> JSONDict:
        """Generates a GET request."""
        request: JSONDict = {"path": path, "method": "GET"}
        if params is not None:
            request["params"] = params
        return request

    @staticmethod
    def generate_post_request(
        path: UriPath, body: Optional[JSONObject] = None
    ) -> JSONDict:
        """Generates a POST request."""
        return {"path": cast(str, path), "method": "POST", "body": body}
