from typing import List, cast

from g3pylib import Glasses3


async def test_get_gaze_frequency(g3: Glasses3):
    assert type(await g3.settings.get_gaze_frequency()) is int


async def test_set_gaze_frequency(g3: Glasses3):
    assert type(await g3.settings.set_gaze_frequency(50)) is bool


async def test_gaze_overlay(g3: Glasses3):
    gaze_overlay = await g3.settings.get_gaze_overlay()
    assert await g3.settings.set_gaze_overlay(not gaze_overlay)
    assert await g3.settings.set_gaze_overlay(gaze_overlay)


async def test_get_name(g3: Glasses3):
    assert await g3.settings.get_name() == "settings"


async def test_subscribe_to_changed(g3: Glasses3):
    changed_queue, unsubscribe_to_changed = await g3.settings.subscribe_to_changed()
    await g3.settings.set_gaze_overlay(not await g3.settings.get_gaze_overlay())
    assert cast(List[str], await changed_queue.get())[0] == "gaze-overlay"
    await unsubscribe_to_changed
