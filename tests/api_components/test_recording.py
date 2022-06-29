from datetime import datetime, timedelta
from typing import cast

import pytest

from glasses3 import Glasses3
from glasses3.recordings.recording import Recording


@pytest.mark.asyncio
async def test_get_created(g3: Glasses3):
    created = await cast(Recording, g3.recordings[0]).get_created()
    assert type(created) is datetime


@pytest.mark.asyncio
async def test_get_duration(g3: Glasses3):
    duration = await cast(Recording, g3.recordings[0]).get_duration()
    assert type(duration) is timedelta
    assert (
        duration.total_seconds() >= 0
        and duration.total_seconds() <= 1.7976931348623157e308
    )  # vill vi kolla övre gränser?


@pytest.mark.asyncio
async def test_get_folder_and_move(g3: Glasses3):
    folder = await cast(Recording, g3.recordings[0]).get_folder()
    assert type(folder) is str
    unique_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    await cast(Recording, g3.recordings[0]).move(f"movefolder{unique_id}")
    assert (
        await cast(Recording, g3.recordings[0]).get_folder() == f"movefolder{unique_id}"
    )


@pytest.mark.asyncio
async def test_get_gaze_overlay(
    g3: Glasses3,
):
    assert not await cast(Recording, g3.recordings[0]).get_gaze_overlay()


@pytest.mark.asyncio
async def test_get_gaze_samples(g3: Glasses3):
    gaze_samples = await cast(Recording, g3.recordings[0]).get_gaze_samples()
    assert type(gaze_samples) is int
    assert gaze_samples >= 0 and gaze_samples <= 9223372036854776000


@pytest.mark.asyncio
async def test_get_http_path(g3: Glasses3):
    http_path = await cast(Recording, g3.recordings[0]).get_http_path()
    assert type(http_path) is str
    assert http_path == f"/recordings/{cast(Recording, g3.recordings[0]).uuid}"


@pytest.mark.asyncio
async def test_get_name(g3: Glasses3):
    name = await cast(Recording, g3.recordings[0]).get_name()
    assert type(name) is str
    assert name == cast(Recording, g3.recordings[0]).uuid


@pytest.mark.asyncio
async def test_get_rtsp_path(g3: Glasses3):
    rtsp_path = await cast(Recording, g3.recordings[0]).get_rtsp_path()
    assert type(rtsp_path) is str
    assert rtsp_path == f"/recordings?uuid={cast(Recording, g3.recordings[0]).uuid}"


@pytest.mark.asyncio
async def test_get_timezone(g3: Glasses3):
    name = await cast(Recording, g3.recordings[0]).get_timezone()
    assert type(name) is str


@pytest.mark.asyncio
async def test_get_valid_gaze_samples(g3: Glasses3):
    valid_gaze_samples = await cast(
        Recording, g3.recordings[0]
    ).get_valid_gaze_samples()
    assert type(valid_gaze_samples) is int
    assert valid_gaze_samples >= 0 and valid_gaze_samples <= 9223372036854776000


@pytest.mark.asyncio
async def test_get_visible_name(g3: Glasses3):
    visible_name = await cast(Recording, g3.recordings[0]).get_visible_name()
    assert type(visible_name) is str
    await cast(Recording, g3.recordings[0]).set_visible_name("myname")
    assert await cast(Recording, g3.recordings[0]).get_visible_name() == "myname"


@pytest.mark.asyncio
async def test_meta_data(g3: Glasses3):
    insert_success = await cast(Recording, g3.recordings[0]).meta_insert("key1", "val1")
    assert insert_success
    insert_success = await cast(Recording, g3.recordings[0]).meta_insert("key2", "val2")
    assert insert_success
    meta_keys = await cast(Recording, g3.recordings[0]).meta_keys()
    assert meta_keys == ["RuVersion", "HuSerial", "RuSerial", "key1", "key2"]
    value1 = await cast(Recording, g3.recordings[0]).meta_lookup("key1")
    assert value1 == "val1"
    await cast(Recording, g3.recordings[0]).meta_insert("key2", None)
    meta_keys = await cast(Recording, g3.recordings[0]).meta_keys()
    assert meta_keys == ["RuVersion", "HuSerial", "RuSerial", "key1"]
    non_existing_message = await cast(Recording, g3.recordings[0]).meta_lookup("key3")
    assert non_existing_message == None
