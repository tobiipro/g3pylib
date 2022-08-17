from datetime import datetime

from g3pylib import Glasses3


async def test_get_head_unit_serial(g3: Glasses3):
    assert type(await g3.system.get_head_unit_serial()) is str


async def test_get_name(g3: Glasses3):
    assert type(await g3.system.get_name()) is str


async def test_get_ntp_is_enabled(g3: Glasses3):
    assert type(await g3.system.get_ntp_is_enabled()) is bool


async def test_get_ntp_is_synchronized(g3: Glasses3):
    assert type(await g3.system.get_ntp_is_synchronized()) is bool


async def test_get_recording_unit_serial(g3: Glasses3):
    assert type(await g3.system.get_recording_unit_serial()) is str


async def test_get_time(g3: Glasses3):
    assert type(await g3.system.get_time()) is datetime


async def test_get_timezone(g3: Glasses3):
    assert type(await g3.system.get_timezone()) is str


async def test_get_version(g3: Glasses3):
    assert type(await g3.system.get_version()) is str


async def test_available_gaze_frequencies(g3: Glasses3):
    available_gaze_frequencies = await g3.system.available_gaze_frequencies()
    assert type(available_gaze_frequencies) is list
    assert type(available_gaze_frequencies[0]) is int


async def test_use_ntp_and_set_time(g3: Glasses3):
    assert await g3.system.use_ntp(False)
    assert await g3.system.set_time(
        datetime.fromisoformat("2000-01-01T00:00:00.000000")
    )
    assert await g3.system.use_ntp(True)


async def test_set_timezone(g3: Glasses3):
    assert await g3.system.set_timezone("Europe/Stockholm")
    assert await g3.system.set_timezone("CET")
