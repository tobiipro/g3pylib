import asyncio
import logging
import os
from typing import Dict, List, Optional, Set, Tuple, cast

import dotenv
from kivy.app import App
from kivy.core.window import Window
from kivy.lang.builder import Builder
from kivy.properties import BooleanProperty
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen, ScreenManager

from eventkinds import AppEventKind, ControlEventKind
from glasses3 import Glasses3, connect_to_glasses
from glasses3.g3typing import SignalBody
from glasses3.recordings import RecordingsEventKind
from glasses3.recordings.recording import Recording
from glasses3.zeroconf import EventKind, G3Service, G3ServiceDiscovery

logging.basicConfig(level=logging.DEBUG)

dotenv.load_dotenv()  # type: ignore
g3_hostname = os.environ["G3_HOSTNAME"]

# fmt: off
Builder.load_string("""
#:import NoTransition kivy.uix.screenmanager.NoTransition
#:import ControlEventKind eventkinds.ControlEventKind
#:import AppEventKind eventkinds.AppEventKind

<DiscoveryScreen>:
    BoxLayout:
        SelectableList:
            id: services
        Button:
            text: "Connect"
            on_press: app.send_app_event(AppEventKind.CONNECT)

<ControlScreen>:
    BoxLayout:
        orientation: 'vertical'
        BoxLayout:
            size_hint: 1, None
            height: dp(50)
            Label:
                id: hostname
                text: "Hostname placeholder"
                halign: "left"
            Label:
                id: task_indicator
                text: "No tasks running."
        BoxLayout:
            size_hint: 1, None
            height: dp(50)
            Button:
                text: "Recorder"
                on_press: root.switch_to_screen("recorder")
            Button:
                text: "Live"
                on_press: root.switch_to_screen("live")
            Button:
                background_color: (0.6, 0.6, 1, 1)
                text: "Disconnect"
                on_press:
                    app.send_app_event(AppEventKind.DISCONNECT)
        ScreenManager:
            id: sm
            transition: NoTransition()

<RecorderScreen>:
    BoxLayout:
        BoxLayout:
            orientation: 'vertical'
            Label:
                id: recorder_status
                text: "Status:"
            Button:
                text: "Start"
                on_press: app.send_control_event(ControlEventKind.START_RECORDING)
            Button:
                text: "Stop"
                on_press: app.send_control_event(ControlEventKind.STOP_RECORDING)
            Button:
                text: "Delete"
                on_press: app.send_control_event(ControlEventKind.DELETE_RECORDING)
        SelectableList:
            id: recordings

<LiveScreen>:
    BoxLayout:
        Label:
            text: "Here you can see your glasses in action."

<SelectableList>:
    viewclass: 'SelectableLabel'
    SelectableRecycleBoxLayout:
        id: selectables
        default_size: None, dp(70)
        default_size_hint: 1, None
        size_hint_y: None
        height: self.minimum_height
        orientation: 'vertical'

<SelectableLabel>:
    canvas.before:
        Color:
            rgba: (.0, 0.9, .1, .3) if self.selected else (0, 0, 0, 1)
        Rectangle:
            pos: self.pos
            size: self.size
"""
)
# fmt: on


class SelectableRecycleBoxLayout(LayoutSelectionBehavior, RecycleBoxLayout):
    pass


class SelectableLabel(RecycleDataViewBehavior, Label):
    index = None
    selected = BooleanProperty(False)
    selectable = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        """Catch and handle the view changes"""
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        """Add selection on touch down"""
        if super().on_touch_down(touch):
            return True
        if self.collide_point(*touch.pos) and self.selectable:
            return self.parent.select_with_touch(self.index, touch)

    def apply_selection(self, rv, index, is_selected):
        """Respond to the selection of items in the view."""
        self.selected = is_selected


class SelectableList(RecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []


class DiscoveryScreen(Screen):
    def add_service(
        self, hostname: str, ipv4: Optional[str], ipv6: Optional[str]
    ) -> None:
        self.ids.services.data.append(
            {"id": hostname, "text": f"{hostname}\n{ipv4}\n{ipv6}"}
        )

    def update_service(
        self, hostname: str, ipv4: Optional[str], ipv6: Optional[str]
    ) -> None:
        services = self.ids.services
        for service in services.data:
            if service["id"] == hostname:
                service["text"] = f"{hostname}\n{ipv4}\n{ipv6}"

    def remove_service(
        self, hostname: str, ipv4: Optional[str], ipv6: Optional[str]
    ) -> None:
        services = self.ids.services
        services.data = [
            service for service in services.data if service["id"] != hostname
        ]


class ControlScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.ids.sm.add_widget(RecorderScreen(name="recorder"))
        self.ids.sm.add_widget(LiveScreen(name="live"))

    def clear(self) -> None:
        self.ids.sm.get_screen("recorder").ids.recordings.data = []
        self.ids.sm.get_screen("recorder").ids.recorder_status.text = "Status:"

    def switch_to_screen(self, screen: str) -> None:
        self.ids.sm.current = screen

    def set_task_running_status(self, is_running: bool) -> None:
        if is_running:
            self.ids.task_indicator.text = "Task running..."
        else:
            self.ids.task_indicator.text = "No task is running."

    def set_hostname(self, hostname: str) -> None:
        self.ids.hostname.text = hostname


class RecorderScreen(Screen):
    def add_recording(
        self, visible_name: str, uuid: str, recording: Recording, atEnd: bool = False
    ) -> None:
        recordings = self.ids.recordings
        recording_data = {"text": visible_name, "uuid": uuid, "recording": recording}
        if atEnd == True:
            recordings.data.append(recording_data)
        else:
            recordings.data.insert(0, recording_data)

    def remove_recording(self, uuid: str) -> None:
        recordings = self.ids.recordings
        recordings.data = [rec for rec in recordings.data if rec["uuid"] != uuid]

    def set_recording_status(self, is_recording: bool) -> None:
        if is_recording:
            self.ids.recorder_status.text = "Status: Recording"
        else:
            self.ids.recorder_status.text = "Status: Not recording"


class LiveScreen(Screen):
    pass


class G3App(App, ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_request_close=self.close)
        self.tasks: Set[asyncio.Task] = set()
        self.app_events: asyncio.Queue[AppEventKind] = asyncio.Queue()
        self.control_events: asyncio.Queue[ControlEventKind] = asyncio.Queue()
        self.add_widget(DiscoveryScreen(name="discovery"))
        self.add_widget(ControlScreen(name="control"))

    def build(self):
        return self

    def on_start(self):
        self.create_task(self.backend_app(), name="backend_app")
        self.send_app_event(AppEventKind.START_DISCOVERY)

    def close(self, *args) -> bool:
        match self.current:
            case "discovery":
                self.send_app_event(AppEventKind.STOP_DISCOVERY)
            case "control":
                self.send_app_event(AppEventKind.DISCONNECT)
        self.send_app_event(AppEventKind.STOP)
        return True

    def switch_to_screen(self, screen: str):
        if screen == "discovery":
            self.transition.direction = "right"
        else:
            self.transition.direction = "left"
        self.current = screen

    def connect(self) -> None:
        selected = self.get_screen(
            "discovery"
        ).ids.services.ids.selectables.selected_nodes
        if len(selected) <= 0:
            print("Please choose a Glasses3 unit to connect.")  # TODO: print in gui
        else:
            hostname = self.get_screen("discovery").ids.services.data[selected[0]]["id"]
            self.backend_control_task = self.create_task(
                self.backend_control(hostname), name="backend_control"
            )
            self.get_screen("control").set_hostname(hostname)
            self.switch_to_screen("control")
            self.send_app_event(AppEventKind.STOP_DISCOVERY)

    async def disconnect(self) -> None:
        self.send_app_event(AppEventKind.START_DISCOVERY)
        await self.stop_update_recordings()
        await self.stop_update_recorder_status()
        self.backend_control_task.cancel()
        try:
            await self.backend_control_task
        except asyncio.CancelledError:
            print("backend_control_task cancelled")
        self.switch_to_screen("discovery")
        self.get_screen("control").clear()

    async def stop_discovery(self):
        self.discovery_task.cancel()
        try:
            await self.discovery_task
        except asyncio.CancelledError:
            print("discovery_task cancelled")
        self.get_screen("discovery").ids.services.data = []

    def send_app_event(self, event: AppEventKind) -> None:
        self.app_events.put_nowait(event)

    async def backend_app(self) -> None:
        while True:
            await self.handle_app_event(await self.app_events.get())

    async def handle_app_event(self, event: AppEventKind):
        match event:
            case AppEventKind.START_DISCOVERY:
                self.discovery_task = self.create_task(
                    self.backend_discovery(), name="backend_discovery"
                )
            case AppEventKind.STOP_DISCOVERY:
                await self.stop_discovery()
            case AppEventKind.CONNECT:
                self.connect()
            case AppEventKind.DISCONNECT:
                await self.disconnect()
            case AppEventKind.STOP:
                self.stop()

    async def backend_discovery(self) -> None:
        async with G3ServiceDiscovery.listen() as service_listener:
            while True:
                await self.handle_service_event(await service_listener.events.get())

    async def handle_service_event(self, event: Tuple[EventKind, G3Service]) -> None:
        match event:
            case (EventKind.ADDED, service):
                self.get_screen("discovery").add_service(
                    service.hostname, service.ipv4_address, service.ipv6_address
                )
            case (EventKind.UPDATED, service):
                self.get_screen("discovery").update_service(
                    service.hostname, service.ipv4_address, service.ipv6_address
                )
            case (EventKind.REMOVED, service):
                self.get_screen("discovery").remove_service(
                    service.hostname, service.ipv4_address, service.ipv6_address
                )

    def send_control_event(self, event: ControlEventKind) -> None:
        self.control_events.put_nowait(event)

    async def backend_control(self, hostname: str) -> None:
        async with connect_to_glasses(hostname) as g3:
            async with g3.recordings.keep_updated_in_context():
                await self.start_update_recordings(g3)
                await self.start_update_recorder_status(g3)
                while True:
                    await self.handle_control_event(g3, await self.control_events.get())

    async def handle_control_event(self, g3: Glasses3, event: ControlEventKind) -> None:
        self.get_screen("control").set_task_running_status(True)
        match event:
            case ControlEventKind.START_RECORDING:
                await g3.recorder.start()
            case ControlEventKind.STOP_RECORDING:
                await g3.recorder.stop()
            case ControlEventKind.DELETE_RECORDING:
                await self.delete_selected_recording(g3)
        self.get_screen("control").set_task_running_status(False)

    async def delete_selected_recording(self, g3: Glasses3) -> None:
        selected = (
            self.get_screen("control")
            .ids.sm.get_screen("recorder")
            .ids.recordings.ids.selectables.selected_nodes
        )
        if len(selected) != 1:
            print(
                "Please select a recording before attempting delete."
            )  # TODO: print in gui
        else:
            uuid = (
                self.get_screen("control")
                .ids.sm.get_screen("recorder")
                .ids.recordings.data[selected[0]]["uuid"]
            )
            print(uuid)
            await g3.recordings.delete(uuid)

    async def start_update_recorder_status(self, g3: Glasses3) -> None:
        recorder_screen = self.get_screen("control").ids.sm.get_screen("recorder")
        if await g3.recorder.get_created() != None:
            recorder_screen.set_recording_status(True)
        else:
            recorder_screen.set_recording_status(False)
        (
            recorder_started_queue,
            self.unsubscribe_to_recorder_started,
        ) = await g3.recorder.subscribe_to_started()
        (
            recorder_stopped_queue,
            self.unsubscribe_to_recorder_stopped,
        ) = await g3.recorder.subscribe_to_stopped()

        async def handle_recorder_started(
            recorder_started_queue: asyncio.Queue[SignalBody],
        ):
            while True:
                await recorder_started_queue.get()
                recorder_screen.set_recording_status(True)

        async def handle_recorder_stopped(
            recorder_stopped_queue: asyncio.Queue[SignalBody],
        ):
            while True:
                await recorder_stopped_queue.get()
                recorder_screen.set_recording_status(False)

        self.handle_recorder_started_task = self.create_task(
            handle_recorder_started(recorder_started_queue),
            name="handle_recorder_started",
        )
        self.handle_recorder_stopped_task = self.create_task(
            handle_recorder_stopped(recorder_stopped_queue),
            name="handle_recorder_stopped",
        )

    async def stop_update_recorder_status(self) -> None:
        await self.unsubscribe_to_recorder_started
        await self.unsubscribe_to_recorder_stopped
        self.handle_recorder_started_task.cancel()
        self.handle_recorder_stopped_task.cancel()

    async def start_update_recordings(self, g3: Glasses3) -> None:
        recorder_screen = self.get_screen("control").ids.sm.get_screen("recorder")
        for child in cast(List[Recording], g3.recordings):
            recorder_screen.add_recording(
                await child.get_visible_name(), child.uuid, child, atEnd=True
            )
        (
            child_added_queue,
            self.unsubscribe_to_child_added,
        ) = await g3.recordings.subscribe_to_child_added()
        (
            child_removed_queue,
            self.unsubscribe_to_child_removed,
        ) = await g3.recordings.subscribe_to_child_removed()

        async def handle_added_recordings(child_added_queue: asyncio.Queue[SignalBody]):
            while True:
                uuid = cast(str, await child_added_queue.get())[0]
                recording = g3.recordings.get_recording(uuid)
                recorder_screen.add_recording(
                    await recording.get_visible_name(), recording.uuid, recording
                )

        async def handle_removed_recordings(
            child_removed_queue: asyncio.Queue[SignalBody],
        ):
            while True:
                uuid = cast(str, await child_removed_queue.get())[0]
                recorder_screen.remove_recording(uuid)

        self.handle_added_recordings_task = self.create_task(
            handle_added_recordings(child_added_queue), name="handle_added_recordings"
        )
        self.handle_removed_recordings_task = self.create_task(
            handle_removed_recordings(child_removed_queue),
            name="handle_removed_recordings",
        )

    async def stop_update_recordings(self) -> None:
        await self.unsubscribe_to_child_added
        await self.unsubscribe_to_child_removed
        self.handle_added_recordings_task.cancel()
        self.handle_removed_recordings_task.cancel()

    def create_task(self, coro, name=None) -> asyncio.Task:
        task = asyncio.create_task(coro, name=name)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.remove)
        return task


if __name__ == "__main__":
    app = G3App()
    asyncio.run(app.async_run())
