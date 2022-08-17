from datetime import datetime, timedelta
from types import NoneType
from typing import List, cast

import pytest

from g3pylib import Glasses3


class TestRecorderRunning:
    @pytest.fixture(scope="class", autouse=True)
    @staticmethod
    async def recording_g3(g3: Glasses3):
        await g3.recorder.start()
        yield
        uuid = cast(str, await g3.recorder.get_uuid())
        await g3.recorder.stop()
        await g3.recordings.delete(uuid)

    @staticmethod
    async def test_get_created(g3: Glasses3):
        created = await g3.recorder.get_created()
        assert type(created) is datetime

    @staticmethod
    async def test_get_current_gaze_frequency(g3: Glasses3):
        current_gaze_frequency = await g3.recorder.get_current_gaze_frequency()
        assert type(current_gaze_frequency) is int
        assert current_gaze_frequency >= 0 and current_gaze_frequency <= 100

    @staticmethod
    async def test_get_duration(g3: Glasses3):
        duration = await g3.recorder.get_duration()
        assert type(duration) is timedelta
        assert duration.total_seconds() >= 0

    @staticmethod
    async def test_get_and_set_folder(g3: Glasses3):
        assert type(await g3.recorder.get_folder()) is str
        unique_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        await g3.recorder.set_folder(f"my-folder-{unique_id}")
        assert await g3.recorder.get_folder() == f"my-folder-{unique_id}"

    @staticmethod
    async def test_get_gaze_overlay(g3: Glasses3):
        gaze_overlay = await g3.recorder.get_gaze_overlay()
        assert type(gaze_overlay) is bool

    @staticmethod
    async def test_get_gaze_samples(g3: Glasses3):
        gaze_samples = await g3.recorder.get_gaze_samples()
        assert type(gaze_samples) is int
        assert gaze_samples >= 0

    @staticmethod
    async def test_get_name(g3: Glasses3):
        name = await g3.recorder.get_name()
        assert name == "recorder"

    @staticmethod
    async def test_get_remaining_time(g3: Glasses3):
        remaining_time = await g3.recorder.get_remaining_time()
        assert type(remaining_time) is timedelta
        assert remaining_time.total_seconds() >= 0

    @staticmethod
    async def test_get_timezone(g3: Glasses3):
        timezone = await g3.recorder.get_timezone()
        assert type(timezone) is str

    @staticmethod
    async def test_get_uuid(g3: Glasses3):
        uuid = await g3.recorder.get_uuid()
        assert type(uuid) is str

    @staticmethod
    async def test_get_valid_gaze_samples(g3: Glasses3):
        valid_gaze_samples = await g3.recorder.get_valid_gaze_samples()
        assert type(valid_gaze_samples) is int
        assert valid_gaze_samples >= 0

    @staticmethod
    async def test_get_and_set_visible_name(g3: Glasses3):
        visible_name = await g3.recorder.get_visible_name()
        assert type(visible_name) is NoneType
        await g3.recorder.set_visible_name("my-name")
        assert await g3.recorder.get_visible_name() == "my-name"

    @staticmethod
    async def test_meta_data(g3: Glasses3):
        insert_successful = await g3.recorder.meta_insert("key1", "val1")
        assert insert_successful
        insert_successful = await g3.recorder.meta_insert("key2", "val2")
        assert insert_successful
        meta_keys = await g3.recorder.meta_keys()
        assert meta_keys == ["key1", "key2"]
        value1 = await g3.recorder.meta_lookup("key1")
        assert value1 == "val1"
        await g3.recorder.meta_insert("key2", None)
        meta_keys = await g3.recorder.meta_keys()
        assert meta_keys == ["key1"]
        non_existing_message = await g3.recorder.meta_lookup("key3")
        assert non_existing_message == None

    @staticmethod
    async def test_send_event(g3: Glasses3):
        assert await g3.recorder.send_event("my-tag-name", {"key": "value"})

    @staticmethod
    async def test_snapshot(g3: Glasses3):
        assert await g3.recorder.snapshot()


class TestRecorderNotRunning:
    @staticmethod
    async def test_get_created(g3: Glasses3):
        assert type(await g3.recorder.get_created()) is NoneType

    @staticmethod
    async def test_get_current_gaze_frequency(g3: Glasses3):
        current_gaze_frequency = await g3.recorder.get_current_gaze_frequency()
        assert type(current_gaze_frequency) is int
        assert current_gaze_frequency == 0

    @staticmethod
    async def test_get_duration(g3: Glasses3):
        duration = await g3.recorder.get_duration()
        assert type(duration) is NoneType
        assert duration == None

    @staticmethod
    async def test_get_and_set_folder(g3: Glasses3):
        assert await g3.recorder.get_folder() is None
        unique_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
        await g3.recorder.set_folder(f"my-folder-{unique_id}")
        assert await g3.recorder.get_folder() is None

    @staticmethod
    async def test_get_gaze_overlay(g3: Glasses3):
        assert not await g3.recorder.get_gaze_overlay()

    @staticmethod
    async def test_get_gaze_samples(g3: Glasses3):
        gaze_samples = await g3.recorder.get_gaze_samples()
        assert type(gaze_samples) is int
        assert gaze_samples == 0

    @staticmethod
    async def test_get_name(g3: Glasses3):
        name = await g3.recorder.get_name()
        assert type(name) is str
        assert name == "recorder"

    @staticmethod
    async def test_get_remaining_time(g3: Glasses3):
        remaining_time = await g3.recorder.get_remaining_time()
        assert type(remaining_time) is timedelta
        assert remaining_time.total_seconds() >= 0

    @staticmethod
    async def test_get_timezone(g3: Glasses3):
        timezone = await g3.recorder.get_timezone()
        assert type(timezone) is NoneType

    @staticmethod
    async def test_get_uuid(g3: Glasses3):
        uuid = await g3.recorder.get_uuid()
        assert type(uuid) is NoneType

    @staticmethod
    async def test_get_valid_gaze_samples(g3: Glasses3):
        valid_gaze_samples = await g3.recorder.get_valid_gaze_samples()
        assert type(valid_gaze_samples) is int
        assert valid_gaze_samples == 0

    @staticmethod
    async def test_get_and_set_visible_name(g3: Glasses3):
        visible_name = await g3.recorder.get_visible_name()
        assert type(visible_name) is NoneType
        await g3.recorder.set_visible_name("my-name")
        assert await g3.recorder.get_visible_name() == None

    @staticmethod
    async def test_meta_data(g3: Glasses3):
        insert_successful = await g3.recorder.meta_insert("key1", "val1")
        assert not insert_successful
        meta_keys = await g3.recorder.meta_keys()
        assert meta_keys == []
        value1 = await g3.recorder.meta_lookup("key1")
        assert value1 == None

    @staticmethod
    async def test_send_event(g3: Glasses3):
        send_event_successful = await g3.recorder.send_event(
            "my-tag-name", {"key": "value"}
        )
        assert not send_event_successful

    @staticmethod
    async def test_snapshot(g3: Glasses3):
        assert not await g3.recorder.snapshot()

    @staticmethod
    async def test_start_stop_and_signals(g3: Glasses3):
        (
            queue_of_started,
            unsubscribe_to_started,
        ) = await g3.recorder.subscribe_to_started()
        (
            queue_of_stopped,
            unsubscribe_to_stopped,
        ) = await g3.recorder.subscribe_to_stopped()

        start_successful = await g3.recorder.start()
        assert start_successful

        uuid_of_started_recording = cast(List[str], await queue_of_started.get())[0]
        assert type(uuid_of_started_recording[0]) is str

        uuid = cast(str, await g3.recorder.get_uuid())
        stop_successful = await g3.recorder.stop()
        assert stop_successful

        folder_of_stopped_recording = cast(List[str], await queue_of_stopped.get())[0]
        assert type(folder_of_stopped_recording) is str

        assert g3.recordings[0].uuid == uuid_of_started_recording
        assert folder_of_stopped_recording == await g3.recordings[0].get_folder()

        await unsubscribe_to_started
        await unsubscribe_to_stopped
        await g3.recordings.delete(uuid)
