"""Base class for all mini-games with network disconnect handling."""

import pygame
from core.scene import Scene
from core.ui import Button, get_font, draw_title
from core.localization import get_text
from core.network import NetworkMessage
from core.particles import ParticleSystem
from settings import load_stats, save_stats, COLORS


class BaseGame(Scene):
    """Base class with common game functionality and disconnect overlay."""

    GAME_ID = "base"

    def __init__(self, engine, mode="local", **kwargs):
        super().__init__(engine)
        self.mode = mode
        self.network_role = kwargs.get("network_role", None)
        self.server = kwargs.get("server", None)
        self.client = kwargs.get("client", None)

        # Disconnect overlay state
        self._disconnect_active = False
        self._disconnect_reason = ""
        self._reconnect_possible = False
        self._reconnect_attempt = 0
        self._reconnect_max = 5
        self._disconnect_buttons = []
        self._disconnect_particles = ParticleSystem()

    def record_result(self, result):
        """Record game result: 'win', 'loss', 'draw'."""
        stats = load_stats()
        if self.GAME_ID not in stats:
            stats[self.GAME_ID] = {"wins": 0, "losses": 0, "draws": 0}
        if result == "win":
            stats[self.GAME_ID]["wins"] += 1
        elif result == "loss":
            stats[self.GAME_ID]["losses"] += 1
        elif result == "draw":
            stats[self.GAME_ID]["draws"] += 1
        save_stats(stats)

    def send_network_message(self, msg):
        """Send a game message over network."""
        net_msg = NetworkMessage(msg["type"], msg.get("data", {}))
        if self.network_role == "host" and self.server:
            self.server.send(net_msg)
        elif self.network_role == "client" and self.client:
            self.client.send(net_msg)

    def get_network_messages(self):
        """Get messages, filtering out disconnect/reconnect notifications."""
        raw = []
        if self.network_role == "host" and self.server:
            raw = self.server.get_messages()
        elif self.network_role == "client" and self.client:
            raw = self.client.get_messages()

        game_messages = []
        for msg in raw:
            if not isinstance(msg, NetworkMessage):
                game_messages.append(msg)
                continue

            if msg.msg_type == "_disconnect":
                self._on_network_disconnect(msg)
            elif msg.msg_type == "_reconnecting":
                self._on_reconnecting(msg)
            elif msg.msg_type == "_reconnect_ack":
                self._on_reconnected()
            else:
                game_messages.append(msg)

        return game_messages

    def _on_network_disconnect(self, msg):
        """Handle disconnect notification."""
        reason = msg.data.get("reason", "unknown")
        reconnect_possible = msg.data.get("reconnect_possible", False)

        self._disconnect_active = True
        self._reconnect_possible = reconnect_possible

        reason_keys = {
            "connection_lost": "connection_lost",
            "timeout": "connection_lost",
            "server_closed": "server_closed",
            "reconnect_timeout": "reconnect_failed",
            "reconnect_failed": "reconnect_failed",
            "client_left": "player_disconnected",
            "peer_left": "player_disconnected",
        }
        self._disconnect_reason = get_text(
            reason_keys.get(reason, "connection_lost"), self.lang
        )

        self._build_disconnect_buttons()

        # Warning particles
        w, h = self.engine.screen.get_size()
        self._disconnect_particles.emit(
            x=w // 2, y=h // 2,
            color=COLORS["danger"], count=20,
            speed=100, lifetime=1.5, size=3,
            glow=True, friction=0.95,
        )

    def _on_reconnecting(self, msg):
        """Handle reconnecting notification."""
        self._reconnect_attempt = msg.data.get("attempt", 0)
        self._reconnect_max = msg.data.get("max_attempts", 5)
        self._disconnect_reason = get_text(
            "reconnecting", self.lang,
            self._reconnect_attempt, self._reconnect_max
        )

    def _on_reconnected(self):
        """Handle successful reconnection."""
        self._disconnect_active = False
        self._reconnect_attempt = 0
        self._disconnect_reason = ""
        self._disconnect_particles.clear()

    def _build_disconnect_buttons(self):
        """Build buttons for disconnect overlay."""
        w, h = self.engine.screen.get_size()
        cx = w // 2

        self._disconnect_buttons = []

        if self._reconnect_possible:
            self._disconnect_buttons.append(
                Button(cx - 170, h // 2 + 40, 160, 50,
                       get_text("wait_reconnect", self.lang),
                       font_size=15,
                       hover_color=COLORS["primary_dark"],
                       on_click=self._wait_reconnect)
            )
            self._disconnect_buttons.append(
                Button(cx + 10, h // 2 + 40, 160, 50,
                       get_text("return_to_menu", self.lang),
                       font_size=15,
                       color=COLORS["bg_light"],
                       hover_color=(80, 30, 30),
                       on_click=self.exit_game)
            )
        else:
            self._disconnect_buttons.append(
                Button(cx - 100, h // 2 + 40, 200, 50,
                       get_text("return_to_menu", self.lang),
                       font_size=16,
                       hover_color=(80, 30, 30),
                       on_click=self.exit_game)
            )

    def _wait_reconnect(self):
        """User chose to wait for reconnection."""
        pass  # Just dismiss, reconnection happens automatically

    def handle_disconnect_events(self, events):
        """Handle events for disconnect overlay. Returns True if overlay is active."""
        if not self._disconnect_active:
            return False

        for event in events:
            for btn in self._disconnect_buttons:
                btn.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.exit_game()

        return True

    def update_disconnect(self, dt):
        """Update disconnect overlay."""
        if not self._disconnect_active:
            return

        for btn in self._disconnect_buttons:
            btn.update(dt)
        self._disconnect_particles.update(dt)

        # Check if reconnection happened (for server)
        if self.network_role == "host" and self.server:
            if self.server.connected and self._disconnect_active:
                self._on_reconnected()
        elif self.network_role == "client" and self.client:
            if self.client.connected and not self.client.is_reconnecting():
                if self._disconnect_active:
                    self._on_reconnected()

    def draw_disconnect_overlay(self, screen):
        """Draw disconnect overlay on top of game."""
        if not self._disconnect_active:
            return

        w, h = screen.get_size()

        # Semi-transparent dark overlay
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 200))
        screen.blit(overlay, (0, 0))

        # Title
        draw_title(screen, get_text("network_error", self.lang),
                   y=h // 2 - 120, font_size=36,
                   color=COLORS["danger"])

        # Reason text
        font = get_font(22)
        reason_surf = font.render(self._disconnect_reason, True, COLORS["warning"])
        screen.blit(reason_surf,
                    (w // 2 - reason_surf.get_width() // 2, h // 2 - 30))

        # Ping info (if was connected)
        ping = 0
        if self.network_role == "host" and self.server:
            ping = self.server.ping_ms
            remaining = self.server.get_reconnect_remaining()
            if remaining > 0:
                timer_font = get_font(16)
                timer_text = timer_font.render(
                    f"⏱ {remaining:.0f}s", True, COLORS["text_gray"]
                )
                screen.blit(timer_text,
                            (w // 2 - timer_text.get_width() // 2, h // 2 + 5))
        elif self.network_role == "client" and self.client:
            ping = self.client.ping_ms

        # Buttons
        for btn in self._disconnect_buttons:
            btn.draw(screen)

        # Particles
        self._disconnect_particles.draw(screen)

    @property
    def is_disconnected(self):
        """Check if currently disconnected."""
        return self._disconnect_active

    def get_ping(self):
        """Get current ping in ms."""
        if self.network_role == "host" and self.server:
            return self.server.ping_ms
        elif self.network_role == "client" and self.client:
            return self.client.ping_ms
        return 0

    def exit_game(self):
        """Clean exit back to mode select."""
        if self.server:
            self.server.stop()
            self.server = None
        if self.client:
            self.client.disconnect()
            self.client = None
        self._disconnect_active = False
        self.engine.pop_scene()