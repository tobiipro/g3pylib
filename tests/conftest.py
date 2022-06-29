import asyncio
import os
from typing import AsyncIterable

import pytest

from glasses3 import Glasses3
from glasses3.g3typing import Hostname

g3_hostname = Hostname(os.environ["G3_HOSTNAME"])


@pytest.fixture(scope="module")
async def g3() -> AsyncIterable[Glasses3]:
    async with Glasses3.connect(g3_hostname) as g3:
        await g3.recordings.start_children_handler_tasks()
        yield g3
        await g3.recordings.stop_children_handler_tasks()


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
