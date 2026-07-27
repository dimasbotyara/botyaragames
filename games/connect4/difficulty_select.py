"""Difficulty selection for Connect Four bot mode."""

import pygame
from core.scene import Scene
from core.ui import Button, draw_title
from core.localization import get_text
from settings import COLORS


class Connect4DifficultySelect(Scene):
    """Select bot difficulty before starting Connect Four."""

    def __init__(self, engine, **kwargs):
        super().__init__(engine)
        self.kwargs = kwargs
        self.buttons = []

    def on_enter(self, **kwargs):
        self._build_ui()

    def on_resize(self, w, h):
        self._build_ui()

    def _build_ui(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2
        btn_w = 350
        btn_h = 60

        self.buttons = [
            Button(cx - btn_w // 2, h // 2 - 110, btn_w, btn_h,
                   get_text("connect4_easy", self.lang), font_size=24,
                   hover_color=(30, 120, 50),
                   on_click=lambda: self._start("easy")),
            Button(cx - btn_w // 2, h // 2 - 30, btn_w, btn_h,
                   get_text("connect4_medium", self.lang), font_size=24,
                   hover_color=(140, 120, 20),
                   on_click=lambda: self._start("medium")),
            Button(cx - btn_w // 2, h // 2 + 50, btn_w, btn_h,
                   get_text("connect4_hard", self.lang), font_size=24,
                   hover_color=(140, 30, 30),
                   on_click=lambda: self._start("hard")),
            Button(cx - btn_w // 2, h // 2 + 150, btn_w, btn_h,
                   get_text("back", self.lang), font_size=20,
                   color=COLORS["bg_light"],
                   hover_color=(80, 30, 30),
                   on_click=lambda: self.engine.pop_scene()),
        ]

    def _start(self, difficulty):
        from games.connect4.game import Connect4Game
        scene = Connect4Game(self.engine, mode="bot", difficulty=difficulty,
                             **self.kwargs)
        self.engine.register_scene("game_connect4_bot_play", scene)
        self.engine.switch_scene("game_connect4_bot_play")

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
        draw_title(screen, get_text("connect4", self.lang), y=30, font_size=42)
        draw_title(screen, get_text("connect4_difficulty", self.lang),
                   y=85, font_size=24, color=COLORS["text_gray"])
        for btn in self.buttons:
            btn.draw(screen)
