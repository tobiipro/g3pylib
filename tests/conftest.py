import asyncio
import os
from typing import AsyncIterable

import pytest

from g3pylib import Glasses3, connect_to_glasses


@pytest.fixture(scope="module")
async def g3() -> AsyncIterable[Glasses3]:
    g3_hostname = os.environ["G3_HOSTNAME"]
    async with connect_to_glasses.with_hostname(g3_hostname) as g3:
        await g3.recordings.start_children_handler_tasks()
        yield g3
        await g3.recordings.stop_children_handler_tasks()


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
