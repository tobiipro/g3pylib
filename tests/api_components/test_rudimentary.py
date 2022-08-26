import asyncio
from typing import Any, List, cast

import pytest

from g3pylib import Glasses3


class TestStreamNotRunning:
    @staticmethod
    async def test_get_event_sample(g3: Glasses3):
        assert not await g3.rudimentary.send_event("my-tag", {"my-key": "my-value"})
        event_sample = await g3.rudimentary.get_event_sample()
        assert type(event_sample) is dict
        assert "timestamp" not in event_sample

    @staticmethod
    async def test_get_gaze_sample(g3: Glasses3):
        gaze_sample = await g3.rudimentary.get_gaze_sample()
        assert type(gaze_sample) is dict
        assert "timestamp" not in gaze_sample

    @staticmethod
    async def test_get_imu_sample(g3: Glasses3):
        imu_sample = await g3.rudimentary.get_imu_sample()
        assert type(imu_sample) is dict
        assert "timestamp" not in imu_sample

    @staticmethod
    @pytest.mark.skip(
        reason="Requires communication through the recording unit's sync port."
    )
    async def test_get_sync_port_sample(g3: Glasses3) -> None:
        raise NotImplementedError

    @staticmethod
    async def calibrate(g3: Glasses3):
        assert not await g3.rudimentary.calibrate()

    @staticmethod
    async def test_context_manager(g3: Glasses3):
        async with g3.rudimentary.keep_alive_in_context():
            await asyncio.sleep(0.1)
            assert (
                "timestamp"
                in cast(dict[str, Any], await g3.rudimentary.get_gaze_sample()).keys()
            )


@pytest.mark.skip(
    reason="Slow test that needs only be run when other tests aren't working as expected."
)
async def test_keepalive(g3: Glasses3):
    assert g3.rudimentary.keepalive()
    await g3.rudimentary._keepalive_task  # type: ignore


class TestStreamRunning:
    @pytest.fixture(scope="class", autouse=True)
    @staticmethod
    async def g3_running(g3: Glasses3):
        await g3.rudimentary.start_streams()
        yield
        await g3.rudimentary.stop_streams()

    @staticmethod
    async def test_get_event_sample(g3: Glasses3):
        assert await g3.rudimentary.send_event("my-tag", {"my-key": "my-value"})

        async def retry_get_event_sample():
            event_sample = await g3.rudimentary.get_event_sample()
            while event_sample == {}:
                event_sample = await asyncio.shield(g3.rudimentary.get_event_sample())
            return event_sample

        event_sample = await asyncio.wait_for(retry_get_event_sample(), timeout=5)
        assert type(event_sample) is dict
        assert "timestamp" in event_sample

    @staticmethod
    async def test_get_gaze_sample(g3: Glasses3):
        gaze_sample = await g3.rudimentary.get_gaze_sample()
        assert type(gaze_sample) is dict
        assert "timestamp" in gaze_sample

    @staticmethod
    async def test_get_imu_sample(g3: Glasses3):
        imu_sample = await g3.rudimentary.get_imu_sample()
        assert type(imu_sample) is dict
        assert "timestamp" in imu_sample

    @staticmethod
    async def test_get_and_set_scene_quality(g3: Glasses3):
        scene_quality = await g3.rudimentary.get_scene_quality()
        assert type(scene_quality) is int
        assert scene_quality >= 15 and scene_quality <= 100
        new_scene_quality = (
            scene_quality - 14
        ) % 86 + 15  # a new integer in the range [15,100]
        await g3.rudimentary.set_scene_quality(new_scene_quality)
        assert await g3.rudimentary.get_scene_quality() == new_scene_quality

    @staticmethod
    async def test_get_and_set_scene_scale(g3: Glasses3):
        scene_scale = await g3.rudimentary.get_scene_scale()
        assert type(scene_scale) is int
        assert scene_scale >= 1 and scene_scale <= 32
        new_scene_scale = scene_scale % 2 + 1
        await g3.rudimentary.set_scene_scale(new_scene_scale)
        assert await g3.rudimentary.get_scene_scale() == new_scene_scale

    @staticmethod
    @pytest.mark.skip(
        reason="Requires communication through the recording unit's sync port."
    )
    async def test_get_sync_port_sample(g3: Glasses3) -> None:
        raise NotImplementedError

    @pytest.mark.skip(reason="Requires a person performing a calibration.")
    @staticmethod
    async def calibrate(g3: Glasses3):
        assert await g3.rudimentary.calibrate()

    @staticmethod
    async def test_event_signal(g3: Glasses3):
        event_queue, unsubscribe_to_event = await g3.rudimentary.subscribe_to_event()
        assert await g3.rudimentary.send_event("my-tag", {"my-key": "my-value"})
        event = cast(List[Any], await event_queue.get())
        assert cast(dict[str, str], event[1])["tag"] == "my-tag"
        await unsubscribe_to_event

    @staticmethod
    async def test_gaze_signal(g3: Glasses3):
        gaze_queue, unsubscribe_to_gaze = await g3.rudimentary.subscribe_to_gaze()
        gaze_sample = cast(List[Any], await gaze_queue.get())
        assert type(gaze_sample[0]) is float
        await unsubscribe_to_gaze

    @staticmethod
    async def test_imu_signal(g3: Glasses3):
        imu_queue, unsubscribe_to_imu = await g3.rudimentary.subscribe_to_imu()
        imu_sample = cast(List[Any], await imu_queue.get())
        assert type(imu_sample[0]) is float
        await unsubscribe_to_imu

    @staticmethod
    async def test_scene_signal(g3: Glasses3):
        scene_queue, unsubscribe_to_scene = await g3.rudimentary.subscribe_to_scene()
        scene_sample = cast(List[Any], await scene_queue.get())
        assert type(scene_sample[0]) is float
        await unsubscribe_to_scene

    @staticmethod
    @pytest.mark.skip(
        reason="Requires communication through the recording unit's sync port."
    )
    async def test_sync_port_signal(g3: Glasses3) -> None:
        raise NotImplementedError
