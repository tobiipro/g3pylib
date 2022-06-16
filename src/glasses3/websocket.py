from __future__ import annotations

import asyncio
import functools
import json
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Any, Coroutine, Dict, List, Optional, Tuple, Type

import websockets
import websockets.client
import websockets.legacy.client
from websockets.client import connect as websockets_connect
from websockets.typing import Subprotocol

from .g3typing import (
    Hostname,
    JsonDict,
    MessageId,
    SignalBody,
    SignalId,
    SubscriptionId,
    UriPath,
)

DEFAULT_WEBSOCKET_PATH = UriPath("/websocket")


def connect(
    g3_hostname: Hostname, websocket_path: UriPath = DEFAULT_WEBSOCKET_PATH
) -> websockets.legacy.client.Connect:
    ws_uri = "ws://{}{}".format(g3_hostname, websocket_path)
    return websockets_connect(
        ws_uri,
        create_protocol=G3WebSocketClientProtocol.factory,
        subprotocols=G3WebSocketClientProtocol.DEFAULT_SUBPROTOCOLS,
    )


class UnsubscribeError(Exception):
    """Raised when unsubscribing to a signal is unsuccessful."""


class InvalidResponseError(Exception):
    """Raised when the server responds with an invalid message."""


class SignalSubscriptionHandler(ABC):
    def init_signal_subscription_handling(self) -> None:
        self._subscription_count = 0
        self._signal_id_by_path: Dict[UriPath, SignalId] = {}
        self._signal_queues_by_id: Dict[
            SignalId, Dict[SubscriptionId, asyncio.Queue[SignalBody]]
        ] = defaultdict(dict)

    async def subscribe_to_signal(
        self, signal_uri_path: UriPath
    ) -> Tuple[asyncio.Queue[SignalBody], functools.partial[Coroutine[Any, Any, None]]]:
        self._subscription_count += 1
        signal_id = self._signal_id_by_path.get(signal_uri_path)
        if signal_id is None:
            signal_id = self._signal_id_by_path[
                signal_uri_path
            ] = await self.require_post_subscribe(signal_uri_path)

        signal_queue: asyncio.Queue[SignalBody] = asyncio.Queue()
        self._signal_queues_by_id[signal_id][
            SubscriptionId(self._subscription_count)
        ] = signal_queue
        return (
            signal_queue,
            functools.partial(
                self.unsubscribe_to_signal,
                signal_uri_path,
                signal_id,
                SubscriptionId(self._subscription_count),
            ),
        )

    async def unsubscribe_to_signal(
        self,
        signal_uri_path: UriPath,
        signal_id: SignalId,
        subscription_id: SubscriptionId,
    ) -> None:
        signal_queues = self._signal_queues_by_id[signal_id]
        del signal_queues[subscription_id]
        if len(signal_queues) == 0:
            if not await self.require_post_unsubscribe(signal_uri_path, signal_id):
                raise UnsubscribeError
            del self._signal_id_by_path[signal_uri_path]

    def receive_signal(self, signal_id: SignalId, signal_body: SignalBody):
        for signal_queue in self._signal_queues_by_id[signal_id].values():
            signal_queue.put_nowait(SignalBody(signal_body.copy()))

    @abstractmethod
    async def require_post_subscribe(self, signal_uri_path: UriPath) -> SignalId:
        raise NotImplementedError

    @abstractmethod
    async def require_post_unsubscribe(
        self, signal_uri_path: UriPath, signal_id: SignalId
    ) -> bool:
        raise NotImplementedError


class G3WebSocketClientProtocol(
    websockets.client.WebSocketClientProtocol, SignalSubscriptionHandler
):
    DEFAULT_SUBPROTOCOLS = [Subprotocol("g3api")]

    def __init__(
        self, *, subprotocols: Optional[List[Subprotocol]] = None, **kwargs: Any
    ):
        self.g3_logger = logging.getLogger(__name__)
        self._message_count = 0
        self._future_messages: Dict[MessageId, asyncio.Future[JsonDict]] = {}
        self._event_loop = asyncio.get_running_loop()
        if subprotocols is None:
            subprotocols = self.DEFAULT_SUBPROTOCOLS
        # Type ignored since websockets has not typed this function as strictly as pyright wants
        super().__init__(subprotocols=subprotocols, **kwargs)  # type: ignore
        self.init_signal_subscription_handling()

    @classmethod
    def factory(
        cls: Type[G3WebSocketClientProtocol], *args: Any, **kwargs: Any
    ) -> G3WebSocketClientProtocol:
        return cls(*args, **kwargs)

    def start_receiver_task(self) -> None:
        self.g3_logger.debug("Receiver task starting")
        self._receiver = asyncio.create_task(self._receiver_task(), name="g3_receiver")

    async def _receiver_task(self) -> None:
        async for message in self:
            json_message: JsonDict = json.loads(message)
            self.g3_logger.info(f"Received {json_message}")
            match json_message:
                case {"id": _}:
                    self._future_messages[json_message["id"]].set_result(json_message)
                case {"signal": signal_id, "body": signal_body}:
                    self.receive_signal(signal_id, signal_body)
                case _:
                    raise InvalidResponseError

    async def require(self, request: JsonDict) -> JsonDict:
        self._message_count += 1
        request["id"] = self._message_count
        string_request_with_id = json.dumps(request)
        await self.send(string_request_with_id)
        future = self._future_messages[
            MessageId(self._message_count)
        ] = self._event_loop.create_future()
        return await future

    async def require_get(
        self, path: UriPath, params: Optional[JsonDict] = None
    ) -> JsonDict:
        return await self.require(self.generate_get_request(path, params))

    async def require_post(self, path: UriPath, body: Optional[str] = None) -> JsonDict:
        return await self.require(self.generate_post_request(path, body))

    async def require_post_subscribe(self, signal_uri_path: UriPath) -> SignalId:
        response = await self.require_post(signal_uri_path)
        try:
            return response["body"]
        except (KeyError, json.JSONDecodeError):
            raise InvalidResponseError

    async def require_post_unsubscribe(
        self, signal_uri_path: UriPath, signal_id: SignalId
    ) -> bool:
        response = await self.require_post(signal_uri_path, signal_id)
        try:
            return response["body"]
        except (KeyError, json.JSONDecodeError):
            raise InvalidResponseError

    @staticmethod
    def generate_get_request(
        path: UriPath, params: Optional[JsonDict] = None
    ) -> JsonDict:
        request: JsonDict = {"path": path, "method": "GET"}
        if params is not None:
            request["params"] = params
        return request

    @staticmethod
    def generate_post_request(path: UriPath, body: Optional[str] = None) -> JsonDict:
        return {"path": path, "method": "POST", "body": body}
