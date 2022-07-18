from __future__ import annotations

import asyncio
import tkinter
from typing import Any, Coroutine, Optional, Set

from glasses3 import Glasses3
from glasses3.zeroconf import G3ServiceDiscovery


class App(tkinter.Tk):
    def __init__(
        self, g3: Glasses3, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        super().__init__()
        if loop is None:
            loop = asyncio.get_running_loop()
        self.loop = loop
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.update_task: Optional[asyncio.Task[None]] = None
        self.tasks: Set[asyncio.Task[Any]] = set()
        self.g3: Glasses3 = g3

        self.latest_recording = tkinter.StringVar(value="Waiting...")

    def start_update_task(self, interval: float = 1 / 120):
        async def update_task():
            while True:
                self.event_generate("<<Update>>")
                self.update()
                await asyncio.sleep(interval)

        self.update_task = self.loop.create_task(update_task())

    @classmethod
    async def open(cls, loop: Optional[asyncio.AbstractEventLoop] = None):
        async with G3ServiceDiscovery.connect() as g3sd:
            hostname = g3sd.services[0].hostname
            print("Hostname:", hostname)
        async with Glasses3.connect(
            "tg03b-080200045321"
        ) as g3:  # TODO: hostname should maybe be type str not Hostname
            app = cls(g3)
            await app.populate()
            app.start_update_task(1 / 30)
            if app.update_task is not None:
                await app.update_task

    def close(self):
        for task in self.tasks:
            task.cancel()
        if self.update_task is not None:
            self.update_task.cancel()
        self.destroy()

    async def populate(self):
        self.title("g3pycontroller")
        tkinter.Button(text="Start", command=self.start_recording).pack()
        tkinter.Button(text="Stop", command=self.stop_recording).pack()
        await self.g3.recordings.start_children_handler_tasks()
        self.latest_recording.set(self.g3.recordings[0].uuid)
        tkinter.Label(
            text="Latest recording", textvariable=self.latest_recording
        ).pack()
        self.bind("<<Update>>", self.update_latest_recording)

    def update_latest_recording(self, *args):
        self.latest_recording.set(self.g3.recordings[0].uuid)

    def execute_async(self, coro: Coroutine[None, None, Any]):
        task = self.loop.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.remove)
        return task

    def start_recording(self, *args):
        self.execute_async(self.g3.recorder.start())

    def stop_recording(self, *args):
        self.execute_async(self.g3.recorder.stop())


async def main():
    await App.open()


if __name__ == "__main__":
    asyncio.run(main())
