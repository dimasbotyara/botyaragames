"""Network lobby - create or join a game."""

import pygame
from core.scene import Scene
from core.ui import Button, TextInput, draw_title, get_font
from core.localization import get_text
from core.network import TCPServer, TCPClient, NetworkMessage, get_local_ip
from games.registry import create_game
from settings import COLORS


class NetworkLobbyScene(Scene):
    def __init__(self, engine):
        super().__init__(engine)
        self.game_id = None
        self.buttons = []
        self.ip_input = None
        self.port_input = None
        self.state = "menu"  # menu, hosting, joining, connected
        self.server = None
        self.client = None
        self.status_text = ""
        self.local_ip = get_local_ip()

    def on_enter(self, **kwargs):
        self.game_id = kwargs.get("game_id")
        self.state = "menu"
        self.status_text = ""
        self._cleanup_network()
        self._build_ui()

    def on_exit(self):
        self._cleanup_network()

    def _cleanup_network(self):
        if self.server:
            self.server.stop()
            self.server = None
        if self.client:
            self.client.disconnect()
            self.client = None

    def _build_ui(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2
        btn_w = 300
        btn_h = 55

        if self.state == "menu":
            self.buttons = [
                Button(cx - btn_w // 2, h // 2 - 60, btn_w, btn_h,
                       get_text("create_server", self.lang), font_size=22,
                       hover_color=COLORS["primary_dark"],
                       on_click=self._host_game),
                Button(cx - btn_w // 2, h // 2 + 20, btn_w, btn_h,
                       get_text("join_server", self.lang), font_size=22,
                       hover_color=(30, 100, 80),
                       on_click=self._show_join),
                Button(cx - btn_w // 2, h // 2 + 120, btn_w, btn_h,
                       get_text("back", self.lang), font_size=20,
                       color=COLORS["bg_light"],
                       hover_color=(80, 30, 30),
                       on_click=lambda: self.engine.pop_scene()),
            ]
            self.ip_input = None
            self.port_input = None

        elif self.state == "joining":
            self.ip_input = TextInput(cx - 150, h // 2 - 20, 300, 40,
                                       placeholder="192.168.1.100",
                                       text=self.local_ip.rsplit(".", 1)[0] + ".")
            self.port_input = TextInput(cx - 75, h // 2 + 40, 150, 40,
                                         placeholder="5555", text="5555")
            self.buttons = [
                Button(cx - 150, h // 2 + 100, 140, 50,
                       get_text("start", self.lang), font_size=20,
                       hover_color=COLORS["primary_dark"],
                       on_click=self._join_game),
                Button(cx + 10, h // 2 + 100, 140, 50,
                       get_text("cancel", self.lang), font_size=20,
                       color=COLORS["bg_light"],
                       hover_color=(80, 30, 30),
                       on_click=self._back_to_menu),
            ]

        elif self.state in ("hosting", "connecting"):
            self.buttons = [
                Button(cx - 150, h // 2 + 100, 300, 50,
                       get_text("cancel", self.lang), font_size=20,
                       color=COLORS["bg_light"],
                       hover_color=(80, 30, 30),
                       on_click=self._back_to_menu),
            ]

    def _host_game(self):
        self.state = "hosting"
        self.server = TCPServer(port=5555)
        self.server.on_connect = lambda addr: None
        self.server.start()
        self.status_text = get_text("waiting_for_player", self.lang)
        self._build_ui()

    def _show_join(self):
        self.state = "joining"
        self._build_ui()

    def _join_game(self):
        ip = self.ip_input.text.strip()
        try:
            port = int(self.port_input.text.strip())
        except ValueError:
            port = 5555

        self.state = "connecting"
        self.status_text = get_text("connecting", self.lang)
        self.client = TCPClient()
        self.client.connect(ip, port)
        self._build_ui()

    def _back_to_menu(self):
        self._cleanup_network()
        self.state = "menu"
        self._build_ui()

    def _start_network_game(self, is_host):
        game_scene = create_game(self.game_id, self.engine, "network",
                                  network_role="host" if is_host else "client",
                                  server=self.server if is_host else None,
                                  client=self.client if not is_host else None)
        if game_scene:
            scene_name = f"game_{self.game_id}_net"
            self.engine.register_scene(scene_name, game_scene)
            self.engine.push_scene(scene_name)

    def handle_events(self, events):
        for event in events:
            for btn in self.buttons:
                btn.handle_event(event)
            if self.ip_input:
                result = self.ip_input.handle_event(event)
                if result == "tab" and self.port_input:
                    self.port_input.active = True
                    self.ip_input.active = False
                elif result == "enter":
                    self._join_game()
            if self.port_input:
                result = self.port_input.handle_event(event)
                if result == "enter":
                    self._join_game()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.state == "menu":
                    self.engine.pop_scene()
                else:
                    self._back_to_menu()

    def update(self, dt):
        for btn in self.buttons:
            btn.update(dt)
        if self.ip_input:
            self.ip_input.update(dt)
        if self.port_input:
            self.port_input.update(dt)

        # Check server connection
        if self.state == "hosting" and self.server:
            if self.server.error:
                self.status_text = f"{get_text('error', self.lang)}: {self.server.error}"
            elif self.server.connected:
                self.server.send(NetworkMessage("game_start", {"game_id": self.game_id}))
                self._start_network_game(is_host=True)

        # Check client connection
        if self.state == "connecting" and self.client:
            if self.client.error:
                self.status_text = f"{get_text('connection_failed', self.lang)}"
                self.state = "joining"
                self._build_ui()
            elif self.client.connected:
                msgs = self.client.get_messages()
                for msg in msgs:
                    if isinstance(msg, NetworkMessage) and msg.msg_type == "game_start":
                        self._start_network_game(is_host=False)
                        return
                self.status_text = get_text("connected", self.lang)

    def draw(self, screen):
        w, h = screen.get_size()

        draw_title(screen, get_text("network_title", self.lang),
                   y=40, font_size=36)

        if self.state == "menu":
            # Show local IP
            font = get_font(18)
            ip_text = get_text("your_ip", self.lang, self.local_ip)
            surf = font.render(ip_text, True, COLORS["text_gray"])
            screen.blit(surf, (w // 2 - surf.get_width() // 2, h // 2 - 120))

        elif self.state == "joining":
            font = get_font(20)
            label1 = font.render(get_text("enter_ip", self.lang),
                                  True, COLORS["text_gray"])
            screen.blit(label1, (w // 2 - 150, h // 2 - 50))
            if self.ip_input:
                self.ip_input.draw(screen)
            label2 = font.render(get_text("enter_port", self.lang),
                                  True, COLORS["text_gray"])
            screen.blit(label2, (w // 2 - 150, h // 2 + 45))
            if self.port_input:
                self.port_input.draw(screen)

        elif self.state in ("hosting", "connecting"):
            font = get_font(22)
            surf = font.render(self.status_text, True, COLORS["warning"])
            screen.blit(surf, (w // 2 - surf.get_width() // 2, h // 2 - 30))

            if self.state == "hosting":
                info_font = get_font(16)
                info = info_font.render(
                    f"IP: {self.local_ip}  |  Port: 5555",
                    True, COLORS["text_gray"]
                )
                screen.blit(info, (w // 2 - info.get_width() // 2, h // 2 + 10))

        for btn in self.buttons:
            btn.draw(screen)