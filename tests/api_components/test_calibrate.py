from typing import Any, List, cast

from g3pylib import Glasses3


async def test_get_name(g3: Glasses3):
    assert await g3.calibrate.get_name() == "calibrate"


async def test_emit_markers(g3: Glasses3):
    marker_queue, unsubscribe_to_marker = await g3.calibrate.subscribe_to_marker()
    await g3.calibrate.emit_markers()
    marker = cast(List[Any], await marker_queue.get())
    assert type(marker) is list
    assert type(marker[0]) is float
    assert type(marker[1]) is list
    assert type(marker[2]) is list
    await unsubscribe_to_marker


async def test_run(g3: Glasses3):
    assert type(await g3.calibrate.run()) is bool
