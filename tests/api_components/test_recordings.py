from typing import List, cast

import pytest

from g3pylib import Glasses3


async def test_get_name(g3: Glasses3):
    assert await g3.recordings.get_name() == "recordings"


async def test_child_added_and_removed_signals(g3: Glasses3):
    (
        child_added_queue,
        unsubscribe_to_child_added,
    ) = await g3.recordings.subscribe_to_child_added()
    (
        child_removed_queue,
        unsubscribe_to_child_removed,
    ) = await g3.recordings.subscribe_to_child_removed()
    deleted_queue, unsubscribe_to_deleted = await g3.recordings.subscribe_to_deleted()

    await g3.recorder.start()
    uuid = cast(str, await g3.recorder.get_uuid())
    await g3.recorder.stop()

    recording_uuid = cast(List[str], await child_added_queue.get())[0]
    assert recording_uuid == g3.recordings[0].uuid

    assert await g3.recordings.delete(recording_uuid)
    removed_child_uuid = cast(List[str], await child_removed_queue.get())[0]
    deleted_recording_uuid = cast(List[str], await deleted_queue.get())[0]
    assert recording_uuid == removed_child_uuid
    assert recording_uuid == deleted_recording_uuid

    await unsubscribe_to_child_added
    await unsubscribe_to_child_removed
    await unsubscribe_to_deleted
    await g3.recordings.delete(uuid)


@pytest.mark.skip(reason="Scan tests need manual interaction.")
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


async def test_context_manager(g3: Glasses3):
    await g3.recorder.start()
    uuid = cast(str, await g3.recorder.get_uuid())
    await g3.recorder.stop()
    async with g3.recordings.keep_updated_in_context():
        assert len(g3.recordings) > 0
    await g3.recordings.delete(uuid)
