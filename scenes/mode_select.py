"""Mode selection scene - local, bot, or network."""

import pygame
from core.scene import Scene
from core.ui import Button, draw_title
from core.localization import get_text
from games.registry import get_registered_games, create_game
from settings import COLORS


class ModeSelectScene(Scene):
    def __init__(self, engine):
        super().__init__(engine)
        self.game_id = None
        self.buttons = []

    def on_enter(self, **kwargs):
        self.game_id = kwargs.get("game_id", None)
        self._build_ui()

    def on_resume(self):
        self._build_ui()

    def on_resize(self, w, h):
        self._build_ui()

    def _build_ui(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2

        games = get_registered_games()
        game_info = games.get(self.game_id, {})

        self.buttons = []
        btn_w = 350
        btn_h = 60
        start_y = h // 2 - 100

        if game_info.get("supports_local", False):
            self.buttons.append(
                Button(cx - btn_w // 2, start_y, btn_w, btn_h,
                       get_text("mode_local", self.lang), font_size=22,
                       hover_color=COLORS["primary_dark"],
                       on_click=lambda: self._start_game("local"))
            )
            start_y += 80

        if game_info.get("supports_bot", False):
            self.buttons.append(
                Button(cx - btn_w // 2, start_y, btn_w, btn_h,
                       get_text("mode_bot", self.lang), font_size=22,
                       hover_color=(100, 60, 150),
                       on_click=lambda: self._start_game("bot"))
            )
            start_y += 80

        if game_info.get("supports_network", False):
            self.buttons.append(
                Button(cx - btn_w // 2, start_y, btn_w, btn_h,
                       get_text("mode_lan", self.lang), font_size=22,
                       hover_color=(30, 100, 80),
                       on_click=lambda: self._start_network())
            )
            start_y += 80

        # Back button
        self.buttons.append(
            Button(cx - btn_w // 2, start_y + 20, btn_w, btn_h,
                   get_text("back", self.lang), font_size=20,
                   color=COLORS["bg_light"],
                   hover_color=(80, 30, 30),
                   on_click=lambda: self.engine.pop_scene())
        )

    def _start_game(self, mode):
        game_scene = create_game(self.game_id, self.engine, mode)
        if game_scene:
            scene_name = f"game_{self.game_id}_{mode}"
            self.engine.register_scene(scene_name, game_scene)
            self.engine.push_scene(scene_name)

    def _start_network(self):
        self.engine.push_scene("network_lobby", game_id=self.game_id)

    def handle_events(self, events):
        for event in events:
            for btn in self.buttons:
                btn.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.engine.pop_scene()

    def update(self, dt):
        for btn in self.buttons:
            btn.update(dt)

    def draw(self, screen):
        games = get_registered_games()
        game_info = games.get(self.game_id, {})
        title = get_text(game_info.get("name_key", ""), self.lang)
        draw_title(screen, title, y=40, font_size=38)

        subtitle = get_text("select_mode", self.lang)
        draw_title(screen, subtitle, y=90, font_size=22,
                   color=COLORS["text_gray"])

        for btn in self.buttons:
            btn.draw(screen)