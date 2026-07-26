"""Base scene class."""

from abc import ABC, abstractmethod


class Scene(ABC):
    """Base class for all scenes."""

    def __init__(self, engine):
        self.engine = engine

    def on_enter(self, **kwargs):
        """Called when scene becomes active."""
        pass

    def on_exit(self):
        """Called when scene is being left."""
        pass

    def on_pause(self):
        """Called when scene is pushed to background."""
        pass

    def on_resume(self):
        """Called when scene returns from background."""
        pass

    def on_resize(self, w, h):
        """Called when window is resized."""
        pass

    @abstractmethod
    def handle_events(self, events):
        """Handle pygame events."""
        pass

    @abstractmethod
    def update(self, dt):
        """Update logic."""
        pass

    @abstractmethod
    def draw(self, screen):
        """Draw to screen."""
        pass

    @property
    def t(self):
        """Shortcut to localization."""
        from core.localization import get_text
        return get_text

    @property
    def lang(self):
        """Current language."""
        return self.engine.settings.get("language", "en")