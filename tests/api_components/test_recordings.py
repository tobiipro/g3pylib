import asyncio
from typing import List, cast

import pytest

from glasses3 import Glasses3
from glasses3.recordings.recording import Recording


@pytest.mark.asyncio
async def test_get_name(g3: Glasses3):
    assert await g3.recordings.get_name() == "recordings"


@pytest.mark.asyncio
async def test_child_added_and_removed_signals(g3: Glasses3):
    (
        added_children_queue,
        unsubscribe_to_child_added,
    ) = await g3.recordings.subscribe_to_child_added()
    (
        removed_children_queue,
        unsubscribe_to_child_removed,
    ) = await g3.recordings.subscribe_to_child_removed()
    deleted_queue, unsubscribe_to_deleted = await g3.recordings.subscribe_to_deleted()

    await g3.recorder.start()
    await g3.recorder.stop()
    recording_uuid = cast(List[str], await added_children_queue.get())[0]
    assert recording_uuid == cast(Recording, g3.recordings[0]).uuid

    assert await g3.recordings.delete(recording_uuid)
    removed_child_uuid = cast(List[str], await removed_children_queue.get())[0]
    deleted_recording_uuid = cast(List[str], await deleted_queue.get())[0]
    assert recording_uuid == removed_child_uuid
    assert recording_uuid == deleted_recording_uuid

    await unsubscribe_to_child_added
    await unsubscribe_to_child_removed
    await unsubscribe_to_deleted


@pytest.mark.skip(reason="Scan tests need manual interaction.")
@pytest.mark.asyncio
async def test_scan_done_and_start_signals(g3: Glasses3):
    (
        scan_start_queue,
        unsubscribe_to_scan_start,
    ) = await g3.recordings.subscribe_to_scan_start()
    (
        scan_done_queue,
        unsubscribe_to_scan_done,
    ) = await g3.recordings.subscribe_to_scan_done()
    assert await scan_start_queue.get() == []
    assert await scan_done_queue.get() == []
    await unsubscribe_to_scan_start
    await unsubscribe_to_scan_done


@pytest.mark.skip
@pytest.mark.asyncio
async def iterate(g3: Glasses3):
    raise NotImplementedError
