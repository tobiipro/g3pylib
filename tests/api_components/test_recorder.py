import asyncio
import base64
from datetime import datetime, timedelta
from types import NoneType
from typing import List, cast

import pytest

from glasses3 import Glasses3, recorder
from glasses3.g3typing import Hostname, JSONObject
from glasses3.recordings.recording import Recording


@pytest.mark.asyncio
async def test_get_created(g3: Glasses3):
    start_time = datetime.utcnow()
    await g3.recorder.start()

    created = await g3.recorder.get_created()
    assert type(created) is datetime
    time_delta = abs(start_time - created)  # may raise error related to time zones
    assert time_delta.total_seconds() < 1

    await g3.recorder.cancel()

    created = await g3.recorder.get_created()
    assert type(await g3.recorder.get_created()) is NoneType


@pytest.mark.asyncio
async def test_get_current_gaze_frequency(g3: Glasses3):
    await g3.recorder.start()

    current_gaze_frequency = await g3.recorder.get_current_gaze_frequency()
    assert type(current_gaze_frequency) is int
    assert current_gaze_frequency >= 0 and current_gaze_frequency <= 100

    await g3.recorder.cancel()

    current_gaze_frequency = await g3.recorder.get_current_gaze_frequency()
    assert type(current_gaze_frequency) is int
    assert current_gaze_frequency == 0


@pytest.mark.asyncio
async def test_get_duration(g3: Glasses3):
    start_time = datetime.utcnow()
    await g3.recorder.start()
    duration = await g3.recorder.get_duration()
    assert type(duration) is timedelta
    assert (
        duration.total_seconds() >= 0
        and duration.total_seconds() <= 1.7976931348623157e308
    )  # vill vi kolla övre gränser?
    estimated_duration = (datetime.utcnow() - start_time).total_seconds()
    assert (estimated_duration - duration.total_seconds()) < 2

    await g3.recorder.cancel()
    duration = await g3.recorder.get_duration()
    assert type(duration) is NoneType
    assert duration == None


@pytest.mark.asyncio
async def test_get_folder(g3: Glasses3):
    await g3.recorder.start()
    folder = await g3.recorder.get_folder()
    assert type(folder) is str
    await g3.recorder.set_folder(f"myfolder{folder}")
    assert await g3.recorder.get_folder() == f"myfolder{folder}"

    await g3.recorder.cancel()
    folder = await g3.recorder.get_folder()
    assert type(folder) is str
    await g3.recorder.set_folder(f"myotherfolder{folder}")
    assert await g3.recorder.get_folder() == f"{folder}"


@pytest.mark.asyncio
async def test_get_gaze_overlay(g3: Glasses3):
    await g3.recorder.start()
    gaze_overlay = await g3.recorder.get_gaze_overlay()
    assert type(gaze_overlay) is bool

    await g3.recorder.cancel()
    gaze_overlay = await g3.recorder.get_gaze_overlay()
    assert type(gaze_overlay) is bool


@pytest.mark.asyncio
async def test_get_gaze_samples(g3: Glasses3):
    await g3.recorder.start()
    gaze_samples = await g3.recorder.get_gaze_samples()
    assert type(gaze_samples) is int
    assert gaze_samples >= 0 and gaze_samples <= 9223372036854776000

    await g3.recorder.cancel()
    gaze_samples = await g3.recorder.get_gaze_samples()
    assert type(gaze_samples) is int
    assert gaze_samples == 0


@pytest.mark.asyncio
async def test_get_name(g3: Glasses3):
    await g3.recorder.start()
    name = await g3.recorder.get_name()
    assert name == "recorder"

    await g3.recorder.cancel()
    name = await g3.recorder.get_name()
    assert type(name) is str
    assert name == "recorder"


@pytest.mark.asyncio
async def test_get_remaining_time(g3: Glasses3):
    await g3.recorder.start()
    remaining_time = await g3.recorder.get_remaining_time()
    assert type(remaining_time) is timedelta
    assert (
        remaining_time.total_seconds() >= 0
        and remaining_time.total_seconds() <= 4294967295
    )

    await g3.recorder.cancel()
    remaining_time = await g3.recorder.get_remaining_time()
    assert type(remaining_time) is timedelta
    assert (
        remaining_time.total_seconds() >= 0
        and remaining_time.total_seconds() <= 4294967295
    )


@pytest.mark.asyncio
async def test_get_timezone(g3: Glasses3):
    await g3.recorder.start()
    timezone = await g3.recorder.get_timezone()
    assert type(timezone) is str

    await g3.recorder.cancel()
    timezone = await g3.recorder.get_timezone()
    assert type(timezone) is NoneType


@pytest.mark.asyncio
async def test_get_uuid(g3: Glasses3):
    await g3.recorder.start()
    uuid = await g3.recorder.get_uuid()
    assert type(uuid) is str

    await g3.recorder.stop()
    uuid = await g3.recorder.get_uuid()
    assert type(uuid) is NoneType


@pytest.mark.asyncio
async def test_get_valid_gaze_samples(g3: Glasses3):
    await g3.recorder.start()
    valid_gaze_samples = await g3.recorder.get_valid_gaze_samples()
    assert type(valid_gaze_samples) is int
    assert valid_gaze_samples >= 0 and valid_gaze_samples <= 9223372036854776000

    await g3.recorder.cancel()
    valid_gaze_samples = await g3.recorder.get_valid_gaze_samples()
    assert type(valid_gaze_samples) is int
    assert valid_gaze_samples == 0


@pytest.mark.asyncio
async def test_get_and_set_visible_name(g3: Glasses3):
    await g3.recorder.start()
    visible_name = await g3.recorder.get_visible_name()
    assert type(visible_name) is NoneType
    await g3.recorder.set_visible_name("myname")
    assert await g3.recorder.get_visible_name() == "myname"

    await g3.recorder.cancel()
    visible_name = await g3.recorder.get_visible_name()
    assert type(visible_name) is NoneType
    await g3.recorder.set_visible_name("myname")
    assert await g3.recorder.get_visible_name() == None


@pytest.mark.asyncio
async def test_meta_keys(g3: Glasses3):
    await g3.recorder.start()
    insert_success = await g3.recorder.meta_insert("key1", "val1")
    assert insert_success
    insert_success = await g3.recorder.meta_insert("key2", "val2")
    assert insert_success
    meta_keys = await g3.recorder.meta_keys()
    assert meta_keys == ["key1", "key2"]
    value1 = await g3.recorder.meta_lookup("key1")
    assert value1 == "val1"
    await g3.recorder.meta_insert("key2", None)
    meta_keys = await g3.recorder.meta_keys()
    assert meta_keys == ["key1"]
    non_existing_message = await g3.recorder.meta_lookup("key3")
    assert non_existing_message == None

    await g3.recorder.cancel()


@pytest.mark.skip(reason="Need action handler to test this feature.")
@pytest.mark.asyncio
async def test_send_event(g3: Glasses3):
    raise NotImplementedError


@pytest.mark.asyncio
async def test_snapshot(g3: Glasses3):
    await g3.recorder.start()
    assert await g3.recorder.snapshot()
    await g3.recorder.cancel()


@pytest.mark.asyncio
async def test_start_stop_and_signals(g3: Glasses3):
    queue_of_started, unsubscribe_to_started = await g3.recorder.subscribe_to_started()
    queue_of_stopped, unsubscribe_to_stopped = await g3.recorder.subscribe_to_stopped()

    start_response = await g3.recorder.start()
    assert start_response == True

    uuid_of_started_recording = cast(List[str], await queue_of_started.get())[0]
    assert type(uuid_of_started_recording[0]) is str

    stop_response = await g3.recorder.stop()
    assert stop_response == True  # always true..?

    folder_of_stopped_recording = cast(List[str], await queue_of_stopped.get())[0]
    assert type(folder_of_stopped_recording) is str

    assert cast(Recording, g3.recordings[0]).uuid == uuid_of_started_recording
    assert (
        folder_of_stopped_recording
        == await cast(Recording, g3.recordings[0]).get_folder()
    )

    await unsubscribe_to_started
    await unsubscribe_to_stopped
