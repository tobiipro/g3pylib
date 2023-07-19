import json
from datetime import datetime, timedelta
from os import path
from typing import cast

import aiohttp
import pytest

from g3pylib import Glasses3
from g3pylib.recordings.recording import Recording


@pytest.fixture(scope="module")
async def recording(g3: Glasses3):
    await g3.recorder.start()
    uuid = cast(str, await g3.recorder.get_uuid())
    await g3.recorder.stop()
    yield g3.recordings[0]
    await g3.recordings.delete(uuid)


async def test_get_created(recording: Recording):
    created = await recording.get_created()
    assert type(created) is datetime


async def test_get_duration(recording: Recording):
    duration = await recording.get_duration()
    assert type(duration) is timedelta
    assert duration.total_seconds() >= 0


async def test_get_folder_and_move(recording: Recording):
    folder = await recording.get_folder()
    assert type(folder) is str
    unique_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    await recording.move(f"move-folder-{unique_id}")
    folder = await recording.get_folder()
    assert folder == f"move-folder-{unique_id}"


async def test_get_gaze_overlay(recording: Recording):
    assert type(await recording.get_gaze_overlay()) is bool


async def test_get_gaze_samples(recording: Recording):
    gaze_samples = await recording.get_gaze_samples()
    assert type(gaze_samples) is int
    assert gaze_samples >= 0


async def test_get_http_path(recording: Recording):
    http_path = await recording.get_http_path()
    assert type(http_path) is str
    assert http_path == f"/recordings/{recording.uuid}"


async def test_get_name(recording: Recording):
    name = await recording.get_name()
    assert type(name) is str
    assert name == recording.uuid


async def test_get_rtsp_path(recording: Recording):
    rtsp_path = await recording.get_rtsp_path()
    assert type(rtsp_path) is str
    assert rtsp_path == f"/recordings?uuid={recording.uuid}"


async def test_get_timezone(recording: Recording):
    timezone = await recording.get_timezone()
    assert type(timezone) is str


async def test_get_valid_gaze_samples(recording: Recording):
    valid_gaze_samples = await recording.get_valid_gaze_samples()
    assert type(valid_gaze_samples) is int
    assert valid_gaze_samples >= 0


async def test_get_visible_name(recording: Recording):
    visible_name = await recording.get_visible_name()
    assert type(visible_name) is str
    await recording.set_visible_name("my-name")
    assert await recording.get_visible_name() == "my-name"


async def test_meta_data(recording: Recording):
    insert_success = await recording.meta_insert("key1", "val1")
    assert insert_success
    insert_success = await recording.meta_insert("key2", "val2")
    assert insert_success
    meta_keys = await recording.meta_keys()
    assert meta_keys == ["RuVersion", "HuSerial", "RuSerial", "key1", "key2"]
    value1 = await recording.meta_lookup("key1")
    assert value1 == "val1"
    await recording.meta_insert("key2", None)
    meta_keys = await recording.meta_keys()
    assert meta_keys == ["RuVersion", "HuSerial", "RuSerial", "key1"]
    non_existing_message = await recording.meta_lookup("key3")
    assert non_existing_message == None


async def test_get_scenevideo_url(recording: Recording):
    url = await recording.get_scenevideo_url()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            assert response.status == 200


async def test_get_gazedata_url(recording: Recording):
    url = await recording.get_gazedata_url()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            assert response.status == 200


async def test_download_files(recording: Recording):
    download_path = "./downloaded_recordings"
    folder_name = await recording.download_files(download_path)

    # check recording.g3 file and read its content
    assert path.isfile(path.join(download_path, folder_name, "recording.g3"))
    with open(path.join(download_path, folder_name, "recording.g3"), "r") as f:
        data_json = json.loads(f.read())

    # check data files exist
    assert path.isfile(
        path.join(download_path, folder_name, data_json["scenecamera"]["file"])
    )
    assert path.isfile(path.join(download_path, folder_name, data_json["gaze"]["file"]))
    assert path.isfile(
        path.join(download_path, folder_name, data_json["events"]["file"])
    )
    assert path.isfile(path.join(download_path, folder_name, data_json["imu"]["file"]))

    # check meta files exist
    meta_folder = data_json["meta-folder"]
    meta_keys = await recording.meta_keys()
    for key in meta_keys:
        assert path.isfile(path.join(download_path, folder_name, meta_folder, key))
