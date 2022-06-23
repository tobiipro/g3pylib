import pytest

from glasses3.g3typing import Hostname


@pytest.mark.asyncio
async def test_get_created(g3):
    created = await g3.recorder.get_created()
    assert created == None


@pytest.mark.asyncio
async def test_get_name(g3):
    name = await g3.recorder.get_name()
    assert name == "recorder"
