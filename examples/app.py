import asyncio
import logging
import os
from typing import Dict, Optional, Tuple

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

from glasses3.g3typing import Hostname
from glasses3.zeroconf import EventKind, G3Service, G3ServiceDiscovery

logging.basicConfig(level=logging.DEBUG)

dotenv.load_dotenv()  # type: ignore
g3_hostname = Hostname(os.environ["G3_HOSTNAME"])

Builder.load_string(
    """
<DiscoveryScreen>:
    BoxLayout:
        ServicesList:
            id: services
        Button:
            text: "Press me"
            on_press: app.connect()

<ControlScreen>:
    BoxLayout:
        orientation: 'vertical'
        Button:
            text: "menu"
            on_press: app.switch_control_screen_to("live")
        ScreenManager:
            id: sm

<RecorderScreen>:
    BoxLayout:
        Label:
            text: "Here you can control your glasses."

<LiveScreen>:
    BoxLayout:
        Label:
            text: "Here you can see your glasses in action."

<ServicesList>:
    viewclass: 'SelectableLabel'
    SelectableRecycleBoxLayout:
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


class ServicesList(RecycleView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.data = []


class DiscoveryScreen(Screen):
    pass


class ControlScreen(Screen):
    pass


class RecorderScreen(Screen):
    pass


class LiveScreen(Screen):
    pass


class G3App(App, ScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tasks = set()
        self.screen_by_name: Dict[str, Screen] = dict()

    def connect(self):
        self.switch_to(self.screen_by_name["control"])

    def switch_control_screen_to(self, screen: str):
        self.control_screen.ids.sm.switch_to(
            self.control_screen.ids.sm.screen_by_name[screen]
        )

    def build(self):
        self.screen_by_name["discovery"] = DiscoveryScreen(name="discovery")
        self.screen_by_name["control"] = ControlScreen(name="control")
        self.add_widget(self.screen_by_name["discovery"])
        self.add_widget(self.screen_by_name["control"])

        self.control_screen = self.screen_by_name["control"]
        self.control_screen.ids.sm.screen_by_name = dict()
        control_sm = self.control_screen.ids.sm
        control_sm.screen_by_name["recorder"] = RecorderScreen(name="recorder")
        control_sm.screen_by_name["live"] = LiveScreen(name="live")
        control_sm.add_widget(control_sm.screen_by_name["recorder"])
        control_sm.add_widget(control_sm.screen_by_name["live"])

        return self

    def on_start(self):
        self.create_task(self.backend())

    async def backend(self):
        async with G3ServiceDiscovery.listen() as service_listener:
            while True:
                await self.handle_service_event(await service_listener.events.get())

    async def handle_service_event(
        self, event: Tuple[EventKind, G3Service]
    ):  # TODO: handle remove/update service
        match event:
            case (EventKind.ADDED, service):
                self.add_service(
                    service.hostname, service.ipv4_address, service.ipv6_address
                )
            case _:
                pass

    def add_service(self, hostname: str, ipv4: Optional[str], ipv6: Optional[str]):
        self.screen_by_name["discovery"].ids.services.data.append(
            {"text": f"{hostname}\n{ipv4}\n{ipv6}"}
        )

    def create_task(self, coro, name=None) -> asyncio.Task:
        task = asyncio.create_task(coro, name=name)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.remove)
        return task


if __name__ == "__main__":
    app = G3App()
    asyncio.run(app.async_run())
