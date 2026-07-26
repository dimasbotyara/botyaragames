"""Tic Tac Toe game scene with full network disconnect support."""

import pygame
import math
from games.base_game import BaseGame
from games.tic_tac_toe.bot import get_bot_move, check_winner, get_winning_line, is_full
from core.ui import Button, draw_title, get_font
from core.localization import get_text
from core.particles import ParticleSystem
from core.network import NetworkMessage
from settings import COLORS


class TicTacToeGame(BaseGame):
    GAME_ID = "tic_tac_toe"

    def __init__(self, engine, mode="local", **kwargs):
        super().__init__(engine, mode, **kwargs)
        self.board = [None] * 9
        self.current_player = "X"
        self.winner = None
        self.winning_line = None
        self.game_over = False
        self.particles = ParticleSystem()
        self.buttons = []

        # Animation
        self.cell_anims = [0.0] * 9
        self.cell_targets = [0.0] * 9
        self.hover_cell = -1
        self.win_anim = 0.0
        self.line_anim = 0.0
        self.status_text = ""
        self.anim_time = 0

        # Bot
        self.bot_delay = 0
        self.bot_thinking = False

        # Network
        if mode == "network":
            self.my_symbol = "X" if self.network_role == "host" else "O"
        else:
            self.my_symbol = None

        # Grid layout
        self.grid_x = 0
        self.grid_y = 0
        self.cell_size = 0

    def on_enter(self, **kwargs):
        self._reset_game()
        self._calc_layout()
        self._build_buttons()

    def on_resize(self, w, h):
        self._calc_layout()
        self._build_buttons()

    def _calc_layout(self):
        w, h = self.engine.screen.get_size()
        available = min(w - 100, h - 250)
        self.cell_size = available // 3
        grid_size = self.cell_size * 3
        self.grid_x = (w - grid_size) // 2
        self.grid_y = 130

    def _build_buttons(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2
        btn_y = h - 75

        self.buttons = []
        if self.game_over:
            self.buttons.append(
                Button(cx - 170, btn_y, 160, 50,
                       get_text("play_again", self.lang), font_size=20,
                       hover_color=COLORS["primary_dark"],
                       on_click=self._play_again)
            )
        self.buttons.append(
            Button(cx + 10 if self.game_over else cx - 80, btn_y, 160, 50,
                   get_text("back", self.lang), font_size=20,
                   color=COLORS["bg_light"],
                   hover_color=(80, 30, 30),
                   on_click=self.exit_game)
        )

    def _reset_game(self):
        self.board = [None] * 9
        self.current_player = "X"
        self.winner = None
        self.winning_line = None
        self.game_over = False
        self.cell_anims = [0.0] * 9
        self.cell_targets = [0.0] * 9
        self.win_anim = 0.0
        self.line_anim = 0.0
        self.bot_thinking = False
        self.bot_delay = 0
        self.hover_cell = -1
        self._update_status()

    def _play_again(self):
        self._reset_game()
        self._build_buttons()
        if self.mode == "network":
            self.send_network_message({"type": "restart"})

    def _update_status(self):
        if self.game_over:
            if self.winner:
                if self.mode == "bot":
                    self.status_text = get_text(
                        "you_win" if self.winner == "X" else "you_lose", self.lang
                    )
                elif self.mode == "network":
                    self.status_text = get_text(
                        "you_win" if self.winner == self.my_symbol else "you_lose",
                        self.lang
                    )
                else:
                    key = "player_x_wins" if self.winner == "X" else "player_o_wins"
                    self.status_text = get_text(key, self.lang)
            else:
                self.status_text = get_text("draw", self.lang)
        elif self.bot_thinking:
            self.status_text = get_text("bot_thinking", self.lang)
        elif self.mode == "network":
            self.status_text = get_text(
                "your_turn" if self.current_player == self.my_symbol
                else "opponent_turn", self.lang
            )
        else:
            key = "player_x_turn" if self.current_player == "X" else "player_o_turn"
            self.status_text = get_text(key, self.lang)

    def _get_cell_at_pos(self, pos):
        mx, my = pos
        if (self.grid_x <= mx < self.grid_x + self.cell_size * 3 and
                self.grid_y <= my < self.grid_y + self.cell_size * 3):
            col = (mx - self.grid_x) // self.cell_size
            row = (my - self.grid_y) // self.cell_size
            return int(row * 3 + col)
        return -1

    def _make_move(self, cell):
        if self.board[cell] is not None or self.game_over:
            return False

        self.board[cell] = self.current_player
        self.cell_targets[cell] = 1.0

        # Particle burst
        cx = self.grid_x + (cell % 3) * self.cell_size + self.cell_size // 2
        cy = self.grid_y + (cell // 3) * self.cell_size + self.cell_size // 2
        color = COLORS["x_color"] if self.current_player == "X" else COLORS["o_color"]
        self.particles.emit(
            x=cx, y=cy, color=color, count=15,
            speed=120, lifetime=0.8, size=3, glow=True, friction=0.92,
        )

        winner = check_winner(self.board)
        if winner:
            self.winner = winner
            self.winning_line = get_winning_line(self.board)
            self.game_over = True
            self._on_game_over()
        elif is_full(self.board):
            self.game_over = True
            self._on_game_over()
        else:
            self.current_player = "O" if self.current_player == "X" else "X"
            if self.mode == "bot" and self.current_player == "O":
                self.bot_thinking = True
                self.bot_delay = 0.5

        self._update_status()
        return True

    def _on_game_over(self):
        w, h = self.engine.screen.get_size()
        cx_pos = w // 2
        cy_pos = self.grid_y + self.cell_size * 3 // 2

        if self.winner:
            for _ in range(3):
                self.particles.emit(
                    x=cx_pos, y=cy_pos, color=COLORS["win_color"],
                    count=40, speed=250, lifetime=2.0, size=5,
                    glow=True, gravity=100, friction=0.96,
                )
            if self.mode == "bot":
                self.record_result("win" if self.winner == "X" else "loss")
            elif self.mode == "network":
                self.record_result(
                    "win" if self.winner == self.my_symbol else "loss"
                )
        else:
            self.record_result("draw")

        self._build_buttons()
        self._update_status()

    # === Event handling with disconnect support ===

    def handle_events(self, events):
        # Disconnect overlay intercepts all events when active
        if self.handle_disconnect_events(events):
            return

        for event in events:
            for btn in self.buttons:
                btn.handle_event(event)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.exit_game()
                return

            if event.type == pygame.MOUSEMOTION:
                self.hover_cell = self._get_cell_at_pos(event.pos)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.game_over:
                    cell = self._get_cell_at_pos(event.pos)
                    if cell >= 0:
                        if self.mode == "local":
                            self._make_move(cell)
                        elif self.mode == "bot":
                            if self.current_player == "X" and not self.bot_thinking:
                                self._make_move(cell)
                        elif self.mode == "network":
                            if (self.current_player == self.my_symbol
                                    and not self.is_disconnected):
                                if self._make_move(cell):
                                    self.send_network_message({
                                        "type": "move",
                                        "data": {"cell": cell},
                                    })

    def update(self, dt):
        self.anim_time += dt

        # Update disconnect overlay
        self.update_disconnect(dt)

        # Cell animations
        for i in range(9):
            self.cell_anims[i] += (
                (self.cell_targets[i] - self.cell_anims[i]) * min(1, dt * 10)
            )

        # Win animation
        if self.game_over:
            self.win_anim = min(1.0, self.win_anim + dt * 2)
            self.line_anim = min(1.0, self.line_anim + dt * 3)

        # Bot logic
        if self.mode == "bot" and self.bot_thinking:
            self.bot_delay -= dt
            if self.bot_delay <= 0:
                move = get_bot_move(self.board[:], "O")
                if move is not None:
                    self.bot_thinking = False
                    self._make_move(move)

        # Network messages (disconnect handling is inside get_network_messages)
        if self.mode == "network" and not self.is_disconnected:
            msgs = self.get_network_messages()
            for msg in msgs:
                if isinstance(msg, NetworkMessage):
                    if msg.msg_type == "move":
                        cell = msg.data.get("cell")
                        if cell is not None:
                            self._make_move(cell)
                    elif msg.msg_type == "restart":
                        self._reset_game()
                        self._build_buttons()

        for btn in self.buttons:
            btn.update(dt)

        self.particles.update(dt)

    def draw(self, screen):
        w, h = screen.get_size()

        # Title
        draw_title(screen, get_text("tic_tac_toe", self.lang),
                   y=15, font_size=32)

        # Ping indicator (network mode)
        if self.mode == "network" and not self.is_disconnected:
            ping = self.get_ping()
            ping_font = get_font(14)
            ping_color = COLORS["accent"] if ping < 100 else (
                COLORS["warning"] if ping < 300 else COLORS["danger"]
            )
            ping_surf = ping_font.render(f"🏓 {ping}ms", True, ping_color)
            screen.blit(ping_surf, (w - ping_surf.get_width() - 15, 15))

        # Status text
        font = get_font(22, bold=True)
        if self.game_over and self.winner:
            color = COLORS["win_color"]
        elif self.game_over:
            color = COLORS["warning"]
        else:
            color = COLORS["text_gray"]
        status = font.render(self.status_text, True, color)
        screen.blit(status, (w // 2 - status.get_width() // 2, 65))

        # Grid
        self._draw_grid(screen)

        # Symbols
        for i in range(9):
            if self.board[i]:
                self._draw_symbol(screen, i, self.board[i])

        # Hover hint
        if (not self.game_over and self.hover_cell >= 0 and
                self.board[self.hover_cell] is None and
                not self.is_disconnected):
            can_move = True
            if self.mode == "bot" and self.current_player != "X":
                can_move = False
            if self.mode == "network" and self.current_player != self.my_symbol:
                can_move = False
            if can_move:
                self._draw_hover(screen, self.hover_cell)

        # Winning line
        if self.winning_line and self.line_anim > 0:
            self._draw_win_line(screen)

        self.particles.draw(screen)

        for btn in self.buttons:
            btn.draw(screen)

        # Disconnect overlay on top of everything
        self.draw_disconnect_overlay(screen)

    def _draw_grid(self, screen):
        size = self.cell_size * 3
        color = COLORS["grid_color"]
        glow_color = (*COLORS["primary"], 30)

        for i in range(1, 3):
            x = self.grid_x + i * self.cell_size
            glow_surf = pygame.Surface((8, size), pygame.SRCALPHA)
            glow_surf.fill(glow_color)
            screen.blit(glow_surf, (x - 4, self.grid_y))
            pygame.draw.line(screen, color,
                             (x, self.grid_y), (x, self.grid_y + size), 3)

            y = self.grid_y + i * self.cell_size
            glow_surf = pygame.Surface((size, 8), pygame.SRCALPHA)
            glow_surf.fill(glow_color)
            screen.blit(glow_surf, (self.grid_x, y - 4))
            pygame.draw.line(screen, color,
                             (self.grid_x, y), (self.grid_x + size, y), 3)

    def _draw_symbol(self, screen, cell, symbol):
        col = cell % 3
        row = cell // 3
        cx = self.grid_x + col * self.cell_size + self.cell_size // 2
        cy = self.grid_y + row * self.cell_size + self.cell_size // 2
        anim = self.cell_anims[cell]
        if anim < 0.01:
            return
        pad = self.cell_size // 4
        is_winner = self.winning_line and cell in self.winning_line
        if symbol == "X":
            color = COLORS["win_color"] if is_winner else COLORS["x_color"]
            self._draw_x(screen, cx, cy, pad, color, anim)
        else:
            color = COLORS["win_color"] if is_winner else COLORS["o_color"]
            self._draw_o(screen, cx, cy, pad, color, anim)

    def _draw_x(self, screen, cx, cy, pad, color, anim):
        length = int((self.cell_size // 2 - pad) * anim)
        glow_surf = pygame.Surface(
            (self.cell_size, self.cell_size), pygame.SRCALPHA
        )
        gc = (self.cell_size // 2, self.cell_size // 2)
        pygame.draw.line(glow_surf, (*color, 40),
                         (gc[0] - length, gc[1] - length),
                         (gc[0] + length, gc[1] + length), 8)
        pygame.draw.line(glow_surf, (*color, 40),
                         (gc[0] + length, gc[1] - length),
                         (gc[0] - length, gc[1] + length), 8)
        screen.blit(glow_surf,
                    (cx - self.cell_size // 2, cy - self.cell_size // 2))
        pygame.draw.line(screen, color,
                         (cx - length, cy - length),
                         (cx + length, cy + length), 4)
        pygame.draw.line(screen, color,
                         (cx + length, cy - length),
                         (cx - length, cy + length), 4)

    def _draw_o(self, screen, cx, cy, pad, color, anim):
        radius = int((self.cell_size // 2 - pad) * anim)
        if radius < 3:
            return
        glow_surf = pygame.Surface(
            (radius * 2 + 20, radius * 2 + 20), pygame.SRCALPHA
        )
        pygame.draw.circle(glow_surf, (*color, 30),
                           (radius + 10, radius + 10), radius + 5, 6)
        screen.blit(glow_surf, (cx - radius - 10, cy - radius - 10))
        pygame.draw.circle(screen, color, (cx, cy), radius, 4)

    def _draw_hover(self, screen, cell):
        col = cell % 3
        row = cell // 3
        x = self.grid_x + col * self.cell_size
        y = self.grid_y + row * self.cell_size
        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 4)
        alpha = int(30 + 20 * pulse)
        surf = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
        color = COLORS["x_color"] if self.current_player == "X" else COLORS["o_color"]
        surf.fill((*color, alpha))
        screen.blit(surf, (x, y))

    def _draw_win_line(self, screen):
        if not self.winning_line:
            return

        def cell_center(c):
            return (
                self.grid_x + (c % 3) * self.cell_size + self.cell_size // 2,
                self.grid_y + (c // 3) * self.cell_size + self.cell_size // 2,
            )

        start = cell_center(self.winning_line[0])
        end = cell_center(self.winning_line[2])
        progress = min(1.0, self.line_anim)
        current_end = (
            int(start[0] + (end[0] - start[0]) * progress),
            int(start[1] + (end[1] - start[1]) * progress),
        )

        glow_surf = pygame.Surface(
            self.engine.screen.get_size(), pygame.SRCALPHA
        )
        pygame.draw.line(glow_surf, (*COLORS["win_color"], 60),
                         start, current_end, 12)
        screen.blit(glow_surf, (0, 0))
        pygame.draw.line(screen, COLORS["win_color"],
                         start, current_end, 5)

        if progress > 0.1:
            self.particles.emit(
                x=current_end[0], y=current_end[1],
                color=COLORS["win_color"], count=1,
                speed=50, lifetime=0.5, size=2,
                glow=True, friction=0.9,
            )