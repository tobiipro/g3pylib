import asyncio
import logging
from collections.abc import Sequence
from contextlib import asynccontextmanager
from enum import Enum, auto
from typing import Awaitable, Dict, List, Optional, Tuple, Union, cast, overload

from g3pylib import _utils
from g3pylib._utils import APIComponent, EndpointKind
from g3pylib.g3typing import URI, SignalBody
from g3pylib.recordings.recording import Recording
from g3pylib.websocket import G3WebSocketClientProtocol


class RecordingsEventKind(Enum):
    """Defines event kinds for the `Recordings` class. These events are emitted to the `Recordings.events` queue in the context `Recordings.keep_updated_in_context`."""

    ADDED = auto()
    """A recording was added."""
    REMOVED = auto()
    """A recording was removed."""


class Recordings(APIComponent, Sequence[Recording]):
    def __init__(
        self,
        connection: G3WebSocketClientProtocol,
        api_uri: URI,
        http_url: Optional[str],
    ) -> None:
        self._connection = connection
        self._http_url = http_url
        self._children = {}
        self._handle_child_added_task = None
        self._handle_child_removed_task = None
        self._events: asyncio.Queue[
            Tuple[RecordingsEventKind, SignalBody]
        ] = asyncio.Queue()
        self.logger: logging.Logger = logging.getLogger(__name__)
        super().__init__(api_uri)

    async def get_name(self) -> str:
        return cast(
            str,
            await self._connection.require_get(
                self.generate_endpoint_uri(EndpointKind.PROPERTY, "name")
            ),
        )

    async def delete(self, uuid: str) -> bool:
        return cast(
            bool,
            await self._connection.require_post(
                self.generate_endpoint_uri(EndpointKind.ACTION, "delete"), body=[uuid]
            ),
        )

    async def subscribe_to_child_added(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "child-added")
        )

    async def subscribe_to_child_removed(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "child-removed")
        )

    async def subscribe_to_deleted(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "deleted")
        )

    async def subscribe_to_scan_done(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "scan-done")
        )

    async def subscribe_to_scan_start(
        self,
    ) -> Tuple[asyncio.Queue[SignalBody], Awaitable[None]]:
        return await self._connection.subscribe_to_signal(
            self.generate_endpoint_uri(EndpointKind.SIGNAL, "scan-start")
        )

    async def _get_children(self) -> Dict[str, Recording]:
        children = cast(
            Dict[str, List[str]], await self._connection.require_get(self._api_uri)
        )["children"]
        return dict(
            map(
                lambda uuid: (
                    uuid,
                    Recording(self._connection, self._api_uri, uuid, self._http_url),
                ),
                reversed(children),
            )
        )

    async def start_children_handler_tasks(self) -> None:
        async def handle_child_added_task(
            added_children_queue: asyncio.Queue[SignalBody],
        ) -> None:
            while True:
                body = await added_children_queue.get()
                child_uuid = cast(List[str], body)[0]
                self._children[child_uuid] = Recording(
                    self._connection, self._api_uri, child_uuid, self._http_url
                )
                await self._events.put((RecordingsEventKind.ADDED, body))

        async def handle_child_removed_task(
            removed_children_queue: asyncio.Queue[SignalBody],
        ) -> None:
            while True:
                body = await removed_children_queue.get()
                child_uuid = cast(List[str], body)[0]
                del self._children[child_uuid]
                await self._events.put((RecordingsEventKind.REMOVED, body))

        if (
            self._handle_child_added_task is None
            and self._handle_child_removed_task is None
        ):
            self._children = await self._get_children()
            (
                added_children_queue,
                self._unsubscribe_to_child_added,
            ) = await self._connection.subscribe_to_signal(
                self.generate_endpoint_uri(EndpointKind.SIGNAL, "child-added")
            )
            (
                removed_children_queue,
                self._unsubscribe_to_child_removed,
            ) = await self._connection.subscribe_to_signal(
                self.generate_endpoint_uri(EndpointKind.SIGNAL, "child-removed")
            )
            self._handle_child_added_task = _utils.create_task(
                handle_child_added_task(added_children_queue),
                name="child_added_handler",
            )
            self._handle_child_removed_task = _utils.create_task(
                handle_child_removed_task(removed_children_queue),
                name="child_removed_handler",
            )
        else:
            self.logger.warning(
                "Attempted starting children handlers when already started."
            )  # TODO: other type of warning?

    async def stop_children_handler_tasks(self) -> None:
        if (
            self._handle_child_added_task is not None
            and self._handle_child_removed_task is not None
        ):
            await self._unsubscribe_to_child_added
            await self._unsubscribe_to_child_removed
            self._handle_child_added_task.cancel()
            self._handle_child_removed_task.cancel()
            try:
                await self._handle_child_added_task
            except asyncio.CancelledError:
                self.logger.debug("handle_child_added_task cancelled")
            try:
                await self._handle_child_removed_task
            except asyncio.CancelledError:
                self.logger.debug("handle_child_removed_task cancelled")
            self._handle_child_added_task = None
            self._handle_child_removed_task = None
        else:
            self.logger.warning(
                "Attempted stopping children handlers before starting them."
            )  # TODO: other type of warning?

    @property
    def events(self) -> asyncio.Queue[Tuple[RecordingsEventKind, SignalBody]]:
        """An event queue containing added and removed recording events.

        Is kept updated in the context `keep_updated_in_context`."""
        return self._events

    @property
    def children(self) -> List[Recording]:
        """A list of all current recordings.

        This property is not recommended for use since the object itself has functionality of a
        [`collections.abc.Sequence`](https://docs.python.org/3/library/collections.abc.html).

        Is updated in the context `keep_updated_in_context`."""
        return list(reversed(self._children.values()))

    def get_recording(self, uuid: str) -> Recording:
        """Returns the recording specified by `uuid`."""
        return self._children[uuid]

    def __len__(self) -> int:
        return len(self._children)

    @overload
    def __getitem__(self, key: int) -> Recording:
        ...

    @overload
    def __getitem__(self, key: slice) -> List[Recording]:
        ...

    def __getitem__(self, key: Union[int, slice]) -> Union[Recording, List[Recording]]:
        return list(reversed(self._children.values()))[key]

    @asynccontextmanager
    async def keep_updated_in_context(self):
        """Keep the `Recordings` state continuously updated in the context by listening for added and removed recordings.

        Example usage:
        ```python
        async with g3.recordings.keep_updated_in_context():
            await g3.recorder.start()
            await asyncio.sleep(3)
            await g3.recorder.stop()

            print(len(g3.recordings)) # current number of recordings on device
            print(await g3.recordings.events.get()) # next event from the event queue
        ```
        """
        await self.start_children_handler_tasks()
        try:
            yield
        finally:
            await self.stop_children_handler_tasks()
