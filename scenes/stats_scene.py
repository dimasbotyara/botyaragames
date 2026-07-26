"""Statistics scene."""

import pygame
from core.scene import Scene
from core.ui import Button, draw_title, get_font
from core.localization import get_text
from games.registry import get_registered_games
from settings import COLORS, load_stats, save_stats


class StatsScene(Scene):
    def __init__(self, engine):
        super().__init__(engine)
        self.buttons = []
        self.stats = {}

    def on_enter(self, **kwargs):
        self.stats = load_stats()
        self._build_ui()

    def on_resize(self, w, h):
        self._build_ui()

    def _build_ui(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2

        self.buttons = [
            Button(cx - 170, h - 80, 160, 50,
                   get_text("reset_stats", self.lang), font_size=16,
                   color=COLORS["bg_light"],
                   hover_color=(120, 30, 30),
                   on_click=self._reset),
            Button(cx + 10, h - 80, 160, 50,
                   get_text("back", self.lang), font_size=20,
                   color=COLORS["bg_light"],
                   hover_color=(80, 30, 30),
                   on_click=lambda: self.engine.pop_scene()),
        ]

    def _reset(self):
        self.stats = {}
        save_stats(self.stats)

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
        w, h = screen.get_size()
        cx = w // 2

        draw_title(screen, get_text("stats_title", self.lang),
                   y=30, font_size=38)

        games = get_registered_games()
        y = 120
        font_title = get_font(24, bold=True)
        font_stat = get_font(20)

        if not self.stats:
            no_stats = get_font(22).render(
                get_text("no_stats", self.lang), True, COLORS["text_dark"]
            )
            screen.blit(no_stats, (cx - no_stats.get_width() // 2, h // 2 - 20))
        else:
            for game_id, game_info in games.items():
                game_stats = self.stats.get(game_id, {})
                if not game_stats:
                    continue

                name = get_text(game_info["name_key"], self.lang)
                title_surf = font_title.render(name, True, COLORS["primary"])
                screen.blit(title_surf, (cx - 200, y))
                y += 35

                wins = game_stats.get("wins", 0)
                losses = game_stats.get("losses", 0)
                draws = game_stats.get("draws", 0)
                total = wins + losses + draws

                stats_items = [
                    (get_text("wins", self.lang), str(wins), COLORS["accent"]),
                    (get_text("losses", self.lang), str(losses), COLORS["danger"]),
                    (get_text("draws", self.lang), str(draws), COLORS["warning"]),
                    (get_text("total_games", self.lang), str(total), COLORS["text_gray"]),
                ]

                for label, value, color in stats_items:
                    surf = font_stat.render(f"{label}: ", True, COLORS["text_gray"])
                    screen.blit(surf, (cx - 180, y))
                    val_surf = font_stat.render(value, True, color)
                    screen.blit(val_surf, (cx - 180 + surf.get_width(), y))
                    y += 28

                y += 20

        for btn in self.buttons:
            btn.draw(screen)