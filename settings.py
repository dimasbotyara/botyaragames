"""Global settings and constants."""

import json
import os
import pygame

SETTINGS_FILE = "botyaragames_settings.json"
STATS_FILE = "botyaragames_stats.json"

# Defaults
DEFAULT_SETTINGS = {
    "language": None,  # None = not chosen yet
    "resolution": None,  # None = auto-detect
    "fullscreen": False,
    "fps": 60,
    "particle_density": 1.0,  # 0.0 - 2.0
    "sound_volume": 0.7,
    "music_volume": 0.5,
}

# Colors - Dark neon theme
COLORS = {
    "bg_dark": (15, 15, 25),
    "bg_medium": (25, 25, 45),
    "bg_light": (35, 35, 60),
    "bg_panel": (30, 30, 55),
    "primary": (0, 200, 255),
    "primary_dark": (0, 120, 180),
    "secondary": (255, 100, 200),
    "accent": (100, 255, 150),
    "warning": (255, 200, 50),
    "danger": (255, 80, 80),
    "text_white": (240, 240, 255),
    "text_gray": (150, 150, 180),
    "text_dark": (80, 80, 110),
    "border": (60, 60, 100),
    "border_light": (80, 80, 130),
    "shadow": (5, 5, 15),
    "transparent_dark": (10, 10, 20, 180),
    "glow_blue": (0, 150, 255, 60),
    "glow_pink": (255, 80, 180, 60),
    "glow_green": (80, 255, 150, 60),
    "x_color": (80, 200, 255),
    "o_color": (255, 100, 180),
    "win_color": (100, 255, 150),
    "grid_color": (60, 60, 120),
}

# Available resolutions
AVAILABLE_RESOLUTIONS = [
    (800, 600),
    (1024, 768),
    (1280, 720),
    (1280, 960),
    (1366, 768),
    (1600, 900),
    (1920, 1080),
]

APP_TITLE = "botyaragames"
APP_VERSION = "0.1.0"


def get_recommended_resolution():
    """Get recommended resolution based on display size."""
    try:
        pygame.display.init()
        info = pygame.display.Info()
        screen_w, screen_h = info.current_w, info.current_h
        # Pick resolution that's ~75% of screen
        target_w = int(screen_w * 0.75)
        target_h = int(screen_h * 0.75)
        best = (800, 600)
        for res in AVAILABLE_RESOLUTIONS:
            if res[0] <= target_w and res[1] <= target_h:
                best = res
        return best
    except Exception:
        return (1024, 768)


def load_settings():
    """Load settings from file."""
    settings = DEFAULT_SETTINGS.copy()
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                settings.update(saved)
        except (json.JSONDecodeError, IOError):
            pass
    if settings["resolution"] is None:
        settings["resolution"] = list(get_recommended_resolution())
    elif isinstance(settings["resolution"], list):
        settings["resolution"] = settings["resolution"]
    return settings


def save_settings(settings):
    """Save settings to file."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except IOError:
        pass


def load_stats():
    """Load statistics from file."""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_stats(stats):
    """Save statistics to file."""
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
    except IOError:
        pass