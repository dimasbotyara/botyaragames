"""Main game engine - manages scenes, display, and global state."""

import pygame
from settings import load_settings, save_settings, COLORS, APP_TITLE
from core.particles import ParticleSystem


class Engine:
    def __init__(self):
        self.settings = load_settings()
        res = self.settings["resolution"]
        if isinstance(res, list):
            res = tuple(res)

        flags = pygame.RESIZABLE
        if self.settings.get("fullscreen"):
            flags = pygame.FULLSCREEN

        self.screen = pygame.display.set_mode(res, flags)
        pygame.display.set_caption(APP_TITLE)

        self.clock = pygame.time.Clock()
        self.running = True
        self.fps = self.settings.get("fps", 60)
        self.dt = 0

        # Global particle system for background effects
        self.bg_particles = ParticleSystem()
        self._spawn_bg_particles()

        # Scene management
        self.scenes = {}
        self.scene_stack = []
        self.current_scene = None

        # Initialize scenes
        self._init_scenes()

    def _spawn_bg_particles(self):
        """Spawn ambient background particles."""
        import random
        w, h = self.screen.get_size()
        for _ in range(30):
            self.bg_particles.emit(
                x=random.randint(0, w),
                y=random.randint(0, h),
                color=random.choice([
                    COLORS["primary"],
                    COLORS["secondary"],
                    COLORS["accent"],
                ]),
                count=1,
                speed=15,
                lifetime=random.uniform(4, 10),
                size=random.uniform(1, 3),
                fade=True,
                glow=True,
                direction="float",
            )

    def _init_scenes(self):
        """Initialize all scenes."""
        from scenes.language_select import LanguageSelectScene
        from scenes.main_menu import MainMenuScene
        from scenes.mode_select import ModeSelectScene
        from scenes.settings_scene import SettingsScene
        from scenes.stats_scene import StatsScene
        from scenes.network_lobby import NetworkLobbyScene

        self.register_scene("language_select", LanguageSelectScene(self))
        self.register_scene("main_menu", MainMenuScene(self))
        self.register_scene("mode_select", ModeSelectScene(self))
        self.register_scene("settings", SettingsScene(self))
        self.register_scene("stats", StatsScene(self))
        self.register_scene("network_lobby", NetworkLobbyScene(self))

        # Determine starting scene
        if self.settings.get("language") is None:
            self.switch_scene("language_select")
        else:
            self.switch_scene("main_menu")

    def register_scene(self, name, scene):
        """Register a scene."""
        self.scenes[name] = scene

    def switch_scene(self, name, **kwargs):
        """Switch to a scene (replaces current)."""
        if self.current_scene:
            self.current_scene.on_exit()
        self.current_scene = self.scenes[name]
        self.current_scene.on_enter(**kwargs)

    def push_scene(self, name, **kwargs):
        """Push a scene on the stack (for overlays/sub-menus)."""
        if self.current_scene:
            self.scene_stack.append(self.current_scene)
            self.current_scene.on_pause()
        self.current_scene = self.scenes[name]
        self.current_scene.on_enter(**kwargs)

    def pop_scene(self):
        """Pop current scene and return to previous."""
        if self.current_scene:
            self.current_scene.on_exit()
        if self.scene_stack:
            self.current_scene = self.scene_stack.pop()
            self.current_scene.on_resume()
        else:
            self.running = False

    def save_current_settings(self):
        """Save settings and apply resolution."""
        save_settings(self.settings)

    def apply_resolution(self):
        """Apply resolution change."""
        res = self.settings["resolution"]
        if isinstance(res, list):
            res = tuple(res)
        flags = pygame.RESIZABLE
        if self.settings.get("fullscreen"):
            flags = pygame.FULLSCREEN
        self.screen = pygame.display.set_mode(res, flags)
        # Re-enter current scene to recalculate layouts
        if self.current_scene:
            self.current_scene.on_enter()

    def run(self):
        """Main game loop."""
        while self.running:
            self.dt = self.clock.tick(self.fps) / 1000.0
            # Cap delta time to avoid physics issues
            if self.dt > 0.1:
                self.dt = 0.1

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                    return
                if event.type == pygame.VIDEORESIZE:
                    if not self.settings.get("fullscreen"):
                        self.settings["resolution"] = [event.w, event.h]
                        self.screen = pygame.display.set_mode(
                            (event.w, event.h), pygame.RESIZABLE
                        )
                        if self.current_scene:
                            self.current_scene.on_resize(event.w, event.h)

            if self.current_scene:
                self.current_scene.handle_events(events)
                self.current_scene.update(self.dt)

            # Render
            self.screen.fill(COLORS["bg_dark"])

            # Background particles
            self.bg_particles.update(self.dt)
            self._maintain_bg_particles()
            self.bg_particles.draw(self.screen)

            if self.current_scene:
                self.current_scene.draw(self.screen)

            pygame.display.flip()

    def _maintain_bg_particles(self):
        """Keep background particles alive."""
        import random
        w, h = self.screen.get_size()
        if len(self.bg_particles.particles) < 25:
            self.bg_particles.emit(
                x=random.randint(0, w),
                y=random.randint(0, h),
                color=random.choice([
                    COLORS["primary"],
                    COLORS["secondary"],
                    COLORS["accent"],
                ]),
                count=1,
                speed=15,
                lifetime=random.uniform(4, 10),
                size=random.uniform(1, 3),
                fade=True,
                glow=True,
                direction="float",
            )