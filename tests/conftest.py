import asyncio

import pytest_asyncio

from glasses3 import Glasses3
from glasses3.g3typing import Hostname

g3_hostname = Hostname("tg02b-080105022801")


@pytest_asyncio.fixture(scope="module")
async def g3():
    async with Glasses3.connect(g3_hostname) as g3:
        yield g3


@pytest_asyncio.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
