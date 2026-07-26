"""Settings scene."""

import pygame
from core.scene import Scene
from core.ui import Button, Toggle, draw_title, get_font
from core.localization import get_text, set_language
from settings import COLORS, AVAILABLE_RESOLUTIONS, save_settings


class SettingsScene(Scene):
    def __init__(self, engine):
        super().__init__(engine)
        self.buttons = []
        self.toggles = {}
        self.selected_res_idx = 0
        self.res_buttons = []

    def on_enter(self, **kwargs):
        self._build_ui()

    def on_resize(self, w, h):
        self._build_ui()

    def _build_ui(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2

        current_res = tuple(self.engine.settings["resolution"])
        self.selected_res_idx = 0
        for i, res in enumerate(AVAILABLE_RESOLUTIONS):
            if res == current_res:
                self.selected_res_idx = i
                break

        y = 130
        self.buttons = []
        self.toggles = {}

        # Language selector
        lang = self.engine.settings.get("language", "en")
        lang_text = "English" if lang == "en" else "Русский"
        self.buttons.append(
            Button(cx + 50, y, 200, 40, lang_text, font_size=18,
                   on_click=self._toggle_language)
        )
        y += 60

        # Resolution
        res_text = f"{AVAILABLE_RESOLUTIONS[self.selected_res_idx][0]}×{AVAILABLE_RESOLUTIONS[self.selected_res_idx][1]}"
        self.res_buttons = [
            Button(cx + 50, y, 50, 40, "◀", font_size=20,
                   on_click=self._prev_res),
            Button(cx + 250, y, 50, 40, "▶", font_size=20,
                   on_click=self._next_res),
        ]
        y += 60

        # Fullscreen toggle
        self.toggles["fullscreen"] = Toggle(
            cx + 100, y + 7,
            initial=self.engine.settings.get("fullscreen", False),
            on_change=lambda v: self.engine.settings.__setitem__("fullscreen", v),
        )
        y += 60

        # Particles toggle
        has_particles = self.engine.settings.get("particle_density", 1.0) > 0
        self.toggles["particles"] = Toggle(
            cx + 100, y + 7,
            initial=has_particles,
            on_change=self._toggle_particles,
        )
        y += 80

        # Apply & Back
        self.buttons.append(
            Button(cx - 170, h - 80, 160, 50,
                   get_text("apply", self.lang), font_size=20,
                   hover_color=COLORS["primary_dark"],
                   on_click=self._apply)
        )
        self.buttons.append(
            Button(cx + 10, h - 80, 160, 50,
                   get_text("back", self.lang), font_size=20,
                   color=COLORS["bg_light"],
                   hover_color=(80, 30, 30),
                   on_click=lambda: self.engine.pop_scene())
        )

    def _toggle_language(self):
        lang = self.engine.settings.get("language", "en")
        new_lang = "ru" if lang == "en" else "en"
        self.engine.settings["language"] = new_lang
        set_language(new_lang)
        self._build_ui()

    def _prev_res(self):
        self.selected_res_idx = max(0, self.selected_res_idx - 1)
        self._build_ui()

    def _next_res(self):
        self.selected_res_idx = min(
            len(AVAILABLE_RESOLUTIONS) - 1,
            self.selected_res_idx + 1
        )
        self._build_ui()

    def _toggle_particles(self, value):
        self.engine.settings["particle_density"] = 1.0 if value else 0.0

    def _apply(self):
        res = AVAILABLE_RESOLUTIONS[self.selected_res_idx]
        self.engine.settings["resolution"] = list(res)
        save_settings(self.engine.settings)
        self.engine.apply_resolution()
        self._build_ui()

    def handle_events(self, events):
        for event in events:
            for btn in self.buttons:
                btn.handle_event(event)
            for btn in self.res_buttons:
                btn.handle_event(event)
            for toggle in self.toggles.values():
                toggle.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.engine.pop_scene()

    def update(self, dt):
        for btn in self.buttons:
            btn.update(dt)
        for btn in self.res_buttons:
            btn.update(dt)
        for toggle in self.toggles.values():
            toggle.update(dt)

    def draw(self, screen):
        w, h = screen.get_size()
        cx = w // 2

        draw_title(screen, get_text("settings_title", self.lang),
                   y=30, font_size=38)

        font = get_font(22)
        y = 135

        # Language
        label = font.render(get_text("language_label", self.lang),
                            True, COLORS["text_white"])
        screen.blit(label, (cx - 200, y))
        y += 60

        # Resolution
        label = font.render(get_text("resolution_label", self.lang),
                            True, COLORS["text_white"])
        screen.blit(label, (cx - 200, y))

        res = AVAILABLE_RESOLUTIONS[self.selected_res_idx]
        res_font = get_font(20, bold=True)
        res_text = res_font.render(f"{res[0]} × {res[1]}", True, COLORS["primary"])
        screen.blit(res_text, (cx + 115, y + 5))

        for btn in self.res_buttons:
            btn.draw(screen)
        y += 60

        # Fullscreen
        label = font.render(get_text("fullscreen_label", self.lang),
                            True, COLORS["text_white"])
        screen.blit(label, (cx - 200, y))
        if "fullscreen" in self.toggles:
            self.toggles["fullscreen"].draw(screen)
        y += 60

        # Particles
        label = font.render(get_text("particles_label", self.lang),
                            True, COLORS["text_white"])
        screen.blit(label, (cx - 200, y))
        if "particles" in self.toggles:
            self.toggles["particles"].draw(screen)

        for btn in self.buttons:
            btn.draw(screen)