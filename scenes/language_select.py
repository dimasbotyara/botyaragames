"""Language selection scene - shown on first launch."""

import pygame
from core.scene import Scene
from core.ui import Button, draw_title, get_font
from core.localization import set_language
from core.particles import ParticleSystem
from settings import COLORS, save_settings


class LanguageSelectScene(Scene):
    def __init__(self, engine):
        super().__init__(engine)
        self.buttons = []
        self.particles = ParticleSystem()
        self.anim_time = 0

    def on_enter(self, **kwargs):
        w, h = self.engine.screen.get_size()
        cx = w // 2

        self.buttons = [
            Button(cx - 150, h // 2 - 40, 300, 60,
                   "English", font_size=28,
                   color=COLORS["bg_light"],
                   hover_color=COLORS["primary_dark"],
                   on_click=lambda: self._select("en")),
            Button(cx - 150, h // 2 + 40, 300, 60,
                   "Русский", font_size=28,
                   color=COLORS["bg_light"],
                   hover_color=COLORS["secondary"],
                   text_color=COLORS["text_white"],
                   on_click=lambda: self._select("ru")),
        ]

    def _select(self, lang):
        set_language(lang)
        self.engine.settings["language"] = lang
        save_settings(self.engine.settings)

        # Celebration particles
        w, h = self.engine.screen.get_size()
        for color in [COLORS["primary"], COLORS["secondary"], COLORS["accent"]]:
            self.particles.emit(
                x=w // 2, y=h // 2,
                color=color, count=30,
                speed=200, lifetime=1.5,
                size=4, glow=True,
            )

        self.engine.switch_scene("main_menu")

    def handle_events(self, events):
        for event in events:
            for btn in self.buttons:
                btn.handle_event(event)

    def update(self, dt):
        self.anim_time += dt
        for btn in self.buttons:
            btn.update(dt)
        self.particles.update(dt)

    def draw(self, screen):
        w, h = screen.get_size()

        # Title
        font = get_font(52, bold=True)
        title = font.render("botyaragames", True, COLORS["primary"])
        screen.blit(title, (w // 2 - title.get_width() // 2, h // 4 - 40))

        # Subtitle
        sub_font = get_font(22)
        sub = sub_font.render("Choose your language / Выберите язык",
                              True, COLORS["text_gray"])
        screen.blit(sub, (w // 2 - sub.get_width() // 2, h // 4 + 30))

        for btn in self.buttons:
            btn.draw(screen)

        self.particles.draw(screen)