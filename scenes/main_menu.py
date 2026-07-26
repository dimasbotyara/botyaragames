"""Main menu with game list."""

import pygame
from core.scene import Scene
from core.ui import Button, ScrollableList, draw_title, get_font
from core.localization import get_text
from games.registry import get_registered_games
from settings import COLORS


class MainMenuScene(Scene):
    def __init__(self, engine):
        super().__init__(engine)
        self.game_list = None
        self.buttons = []

    def on_enter(self, **kwargs):
        self._build_ui()

    def on_resume(self):
        self._build_ui()

    def on_resize(self, w, h):
        self._build_ui()

    def _build_ui(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2

        # Game list
        list_w = min(700, w - 60)
        list_h = h - 220
        list_x = cx - list_w // 2
        list_y = 110

        self.game_list = ScrollableList(list_x, list_y, list_w, list_h,
                                         item_height=75)

        # Populate with registered games
        games = get_registered_games()
        items = []
        for game_id, game_info in games.items():
            modes = []
            if game_info.get("supports_local"):
                modes.append("🎮")
            if game_info.get("supports_bot"):
                modes.append("🤖")
            if game_info.get("supports_network"):
                modes.append("🌐")

            items.append({
                "text": get_text(game_info["name_key"], self.lang),
                "desc": get_text(game_info["desc_key"], self.lang),
                "modes": modes,
                "on_click": lambda gid=game_id: self._select_game(gid),
            })

        self.game_list.set_items(items)

        # Bottom buttons
        btn_y = h - 70
        btn_w = 160
        btn_h = 45
        gap = 20
        total_w = btn_w * 3 + gap * 2
        start_x = cx - total_w // 2

        self.buttons = [
            Button(start_x, btn_y, btn_w, btn_h,
                   get_text("settings", self.lang), font_size=18,
                   on_click=lambda: self.engine.push_scene("settings")),
            Button(start_x + btn_w + gap, btn_y, btn_w, btn_h,
                   get_text("statistics", self.lang), font_size=18,
                   on_click=lambda: self.engine.push_scene("stats")),
            Button(start_x + (btn_w + gap) * 2, btn_y, btn_w, btn_h,
                   get_text("quit", self.lang), font_size=18,
                   color=COLORS["bg_light"],
                   hover_color=(100, 30, 30),
                   on_click=self._quit),
        ]

    def _select_game(self, game_id):
        self.engine.push_scene("mode_select", game_id=game_id)

    def _quit(self):
        self.engine.running = False

    def handle_events(self, events):
        for event in events:
            if self.game_list:
                self.game_list.handle_event(event)
            for btn in self.buttons:
                btn.handle_event(event)

    def update(self, dt):
        if self.game_list:
            self.game_list.update(dt)
        for btn in self.buttons:
            btn.update(dt)

    def draw(self, screen):
        w = screen.get_width()

        # Title
        draw_title(screen, get_text("main_menu_title", self.lang),
                   y=30, font_size=42)

        if self.game_list:
            self.game_list.draw(screen)

        for btn in self.buttons:
            btn.draw(screen)