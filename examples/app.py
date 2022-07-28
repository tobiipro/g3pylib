import asyncio
import logging
import os
from typing import Dict, List, Optional, Set, Tuple, cast

import dotenv
from kivy.app import App
from kivy.lang.builder import Builder
from kivy.properties import BooleanProperty
from kivy.uix.label import Label
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.layout import LayoutSelectionBehavior
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen, ScreenManager

from controleventkind import ControlEventKind
from glasses3 import Glasses3, connect_to_glasses
from glasses3.g3typing import Hostname, SignalBody
from glasses3.recordings.recording import Recording
from glasses3.zeroconf import EventKind, G3Service, G3ServiceDiscovery

logging.basicConfig(level=logging.DEBUG)

dotenv.load_dotenv()  # type: ignore
g3_hostname = Hostname(os.environ["G3_HOSTNAME"])

# fmt: off
Builder.load_string("""
#:import NoTransition kivy.uix.screenmanager.NoTransition
#:import ControlEventKind controleventkind.ControlEventKind

<DiscoveryScreen>:
    BoxLayout:
        SelectableList:
            id: services
        Button:
            text: "Connect"
            on_press: app.connect()

<ControlScreen>:
    BoxLayout:
        orientation: 'vertical'
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
                    app.disconnect()
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
        if is_selected:
            print("selection changed to {0}".format(rv.data[index]))
        else:
            print("selection removed for {0}".format(rv.data[index]))


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
        self.ids.sm.screen_by_name = dict()
        self.ids.sm.screen_by_name["recorder"] = RecorderScreen(name="recorder")
        self.ids.sm.screen_by_name["live"] = LiveScreen(name="live")
        self.ids.sm.add_widget(self.ids.sm.screen_by_name["recorder"])
        self.ids.sm.add_widget(self.ids.sm.screen_by_name["live"])

    def clear(self) -> None:  # let every child screen have clear method?
        self.ids.sm.screen_by_name["recorder"].ids.recordings.data = []
        self.ids.sm.screen_by_name["recorder"].ids.recorder_status.text = "Status:"

    def switch_to_screen(self, screen: str) -> None:
        self.ids.sm.switch_to(self.ids.sm.screen_by_name[screen])


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

    def set_recording(self) -> None:
        self.ids.recorder_status.text = "Status: Recording"

    def set_not_recording(self) -> None:
        self.ids.recorder_status.text = "Status: Not recording"


class LiveScreen(Screen):
    pass


class G3App(App, ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tasks: Set[asyncio.Task] = set()
        self.screen_by_name: Dict[str, Screen] = dict()
        self.control_events: asyncio.Queue[ControlEventKind] = asyncio.Queue()

        self.screen_by_name["discovery"] = DiscoveryScreen(name="discovery")
        self.screen_by_name["control"] = ControlScreen(name="control")
        self.add_widget(self.screen_by_name["discovery"])
        self.add_widget(self.screen_by_name["control"])

    def build(self):
        return self

    def on_start(self):
        self.create_task(self.backend_discovery())

    def connect(self) -> None:
        selected = self.screen_by_name[
            "discovery"
        ].ids.services.ids.selectables.selected_nodes
        if len(selected) <= 0:
            print("Please choose a Glasses3 unit to connect.")  # TODO: print in gui
        else:
            hostname = self.screen_by_name["discovery"].ids.services.data[selected[0]][
                "id"
            ]
            self.backend_control_task = self.create_task(self.backend_control(hostname))
            self.switch_to(self.screen_by_name["control"], direction="left")

    def disconnect(self) -> None:
        self.backend_control_task.cancel()
        self.create_task(self.stop_update_recordings())
        self.create_task(self.stop_update_recorder_status())
        self.switch_to(self.screen_by_name["discovery"], direction="right")
        cast(ControlScreen, self.screen_by_name["control"]).clear()

    async def backend_discovery(self) -> None:
        async with G3ServiceDiscovery.listen() as service_listener:
            while True:
                await self.handle_service_event(await service_listener.events.get())

    async def handle_service_event(self, event: Tuple[EventKind, G3Service]) -> None:
        match event:
            case (EventKind.ADDED, service):
                cast(DiscoveryScreen, self.screen_by_name["discovery"]).add_service(
                    service.hostname, service.ipv4_address, service.ipv6_address
                )
            case (EventKind.UPDATED, service):
                cast(DiscoveryScreen, self.screen_by_name["discovery"]).update_service(
                    service.hostname, service.ipv4_address, service.ipv6_address
                )
            case (EventKind.REMOVED, service):
                cast(DiscoveryScreen, self.screen_by_name["discovery"]).remove_service(
                    service.hostname, service.ipv4_address, service.ipv6_address
                )

    def send_control_event(self, event: ControlEventKind) -> None:
        self.control_events.put_nowait(event)

    async def backend_control(
        self, hostname
    ) -> None:  # TODO: type when Hostname removed from API
        async with connect_to_glasses(hostname) as g3:
            async with g3.recordings.keep_updated_in_context():
                await self.start_update_recordings(g3)
                await self.start_update_recorder_status(g3)
                while True:
                    await self.handle_control_event(g3, await self.control_events.get())

    async def handle_control_event(self, g3: Glasses3, event: ControlEventKind) -> None:
        match event:
            case ControlEventKind.START_RECORDING:
                await g3.recorder.start()
            case ControlEventKind.STOP_RECORDING:
                await g3.recorder.stop()
            case ControlEventKind.DELETE_RECORDING:
                await self.delete_selected_recording(g3)

    async def delete_selected_recording(self, g3: Glasses3) -> None:
        selected = (
            self.screen_by_name["control"]
            .ids.sm.screen_by_name["recorder"]
            .ids.recordings.ids.selectables.selected_nodes
        )
        if len(selected) != 1:
            print(
                "Please select one recording before attempting delete."
            )  # TODO: print in gui
        else:
            uuid = (
                self.screen_by_name["control"]
                .ids.sm.screen_by_name["recorder"]
                .ids.recordings.data[selected[0]]["uuid"]
            )
            print(uuid)
            await g3.recordings.delete(uuid)

    async def start_update_recorder_status(self, g3: Glasses3) -> None:
        if await g3.recorder.get_created() != None:
            self.screen_by_name["control"].ids.sm.screen_by_name[
                "recorder"
            ].set_recording()
        else:
            self.screen_by_name["control"].ids.sm.screen_by_name[
                "recorder"
            ].set_not_recording()
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
                self.screen_by_name["control"].ids.sm.screen_by_name[
                    "recorder"
                ].set_recording()

        async def handle_recorder_stopped(
            recorder_stopped_queue: asyncio.Queue[SignalBody],
        ):
            while True:
                await recorder_stopped_queue.get()
                self.screen_by_name["control"].ids.sm.screen_by_name[
                    "recorder"
                ].set_not_recording()

        self.handle_recorder_started_task = self.create_task(
            handle_recorder_started(recorder_started_queue)
        )
        self.handle_recorder_stopped_task = self.create_task(
            handle_recorder_stopped(recorder_stopped_queue)
        )

    async def stop_update_recorder_status(self) -> None:
        await self.unsubscribe_to_recorder_started
        await self.unsubscribe_to_recorder_stopped
        self.handle_recorder_started_task.cancel()
        self.handle_recorder_stopped_task.cancel()

    async def start_update_recordings(self, g3: Glasses3) -> None:
        for child in cast(List[Recording], g3.recordings):
            self.screen_by_name["control"].ids.sm.screen_by_name[
                "recorder"
            ].add_recording(
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
                recording = g3.recordings._children[
                    uuid
                ]  # add get_child(uuid) in recordings
                self.screen_by_name["control"].ids.sm.screen_by_name[
                    "recorder"
                ].add_recording(
                    await recording.get_visible_name(), recording.uuid, recording
                )

        async def handle_removed_recordings(
            child_removed_queue: asyncio.Queue[SignalBody],
        ):
            while True:
                uuid = cast(str, await child_removed_queue.get())[0]
                self.screen_by_name["control"].ids.sm.screen_by_name[
                    "recorder"
                ].remove_recording(uuid)

        self.handle_added_recordings_task = self.create_task(
            handle_added_recordings(child_added_queue)
        )
        self.handle_removed_recordings_task = self.create_task(
            handle_removed_recordings(child_removed_queue)
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
