import pytest

from g3pylib import Glasses3
from g3pylib.system.battery import BatteryState


async def test_get_charging(g3: Glasses3):
    charging = await g3.system.battery.get_charging()
    assert type(charging) is bool


async def test_get_level(g3: Glasses3):
    level = await g3.system.battery.get_level()
    assert type(level) is float
    assert level >= 0 and level <= 1


async def test_get_name(g3: Glasses3):
    name = await g3.system.battery.get_name()
    assert name == "battery"


async def test_get_remaining_time(g3: Glasses3):
    remaining_time = await g3.system.battery.get_remaining_time()
    assert type(remaining_time) is int
    assert remaining_time >= 0 and remaining_time <= 4294967295


async def test_get_state(g3: Glasses3):
    state = await g3.system.battery.get_state()
    assert type(state) is BatteryState


@pytest.mark.skip(reason="Requires state change which occur very seldom.")
async def test_subscribe_to_state_changed():
    raise NotImplementedError
