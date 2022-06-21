import asyncio
import logging
from typing import Awaitable, List, Tuple, Union, cast

from glasses3.g3typing import JSONDict, SignalBody, UriPath
from glasses3.websocket import G3WebSocketClientProtocol


class Recordings:
    def __init__(self, connection: G3WebSocketClientProtocol) -> None:
        self._connection = connection
        self._children = []
        self._handle_child_added_task = None
        self._handle_child_removed_task = None
        self.logger = logging.getLogger(__name__)

    async def get_string(self):
        return await self._connection.require_get(UriPath("/recordings.name"))

    async def delete(self, uuid: str) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                UriPath("/recordings!delete"), body=uuid
            ),
        )

    async def subscribe_to_child_added(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            UriPath("/recordings:child-added")
        )

    async def subscribe_to_child_removed(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            UriPath("/recordings:child-removed")
        )

    async def subscribe_to_deleted(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            UriPath("/recordings:deleted")
        )

    async def subscribe_to_scan_done(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            UriPath("/recordings:scan-done")
        )

    async def subscribe_to_scan_start(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            UriPath("/recordings:scan-start")
        )

    async def _get_children(self) -> List[str]:
        body = cast(
            JSONDict, await self._connection.require_get(UriPath("/recordings"))
        )
        return cast(List[str], body["children"])

    async def start_children_handler_tasks(self):
        if (
            self._handle_child_added_task is None
            and self._handle_child_removed_task is None
        ):
            self._children = await self._get_children()
            (
                added_children_queue,
                self._unsubscribe_to_child_added,
            ) = await self._connection.subscribe_to_signal(
                UriPath("/recordings:child-added")
            )
            (
                removed_children_queue,
                self._unsubscribe_to_child_removed,
            ) = await self._connection.subscribe_to_signal(
                UriPath("/recordings:child-removed")
            )
            self._handle_child_added_task = asyncio.create_task(
                self._handle_child_added(added_children_queue)
            )
            self._handle_child_removed_task = asyncio.create_task(
                self._handle_child_removed(removed_children_queue)
            )
        else:
            self.logger.warn(
                "Attempted starting children handlers when already started."
            )  # TODO: other type of warning?

    async def stop_children_handlers(self):
        if (
            self._handle_child_added_task is not None
            and self._handle_child_removed_task is not None
        ):
            self._handle_child_added_task.cancel()
            self._handle_child_removed_task.cancel()
            await self._unsubscribe_to_child_added
            await self._unsubscribe_to_child_removed
        else:
            self.logger.warn(
                "Attempted stopping children handlers before starting them."
            )  # TODO: other type of warning?

    async def _handle_child_added(
        self, added_children_queue: asyncio.Queue[SignalBody]
    ) -> None:
        while True:
            child = cast(List[str], await added_children_queue.get())
            self._children.insert(0, child[0])

    async def _handle_child_removed(
        self, removed_children_queue: asyncio.Queue[SignalBody]
    ) -> None:
        while True:
            child = cast(List[str], await removed_children_queue.get())
            self._children.remove(child[0])

    @property
    def children(self) -> List[str]:
        """This property is not recommended for use since the object itself has functionality of a list. See `__iter__` and `__getitem__` methods."""
        return self._children

    def __iter__(self):
        yield from self._children

    def __len__(self):
        return len(self._children)

    def __getitem__(self, key: Union[int, slice]) -> Union[str, List[str]]:
        return self._children[key]
