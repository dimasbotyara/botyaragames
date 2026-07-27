"""Connect Four game scene with falling disc animations."""

import pygame
import math
import random
from games.base_game import BaseGame
from games.connect4.bot import (
    get_bot_move, check_winner, get_winning_cells,
    is_full, get_valid_columns, ROWS, COLS
)
from core.ui import Button, draw_title, get_font
from core.localization import get_text
from core.particles import ParticleSystem
from core.network import NetworkMessage
from settings import COLORS


# Colors for players
P1_COLOR = (240, 60, 60)      # Red
P1_COLOR_LIGHT = (255, 120, 120)
P2_COLOR = (240, 220, 40)     # Yellow
P2_COLOR_LIGHT = (255, 245, 130)
BOARD_COLOR = (30, 50, 160)
BOARD_DARK = (20, 35, 120)
EMPTY_COLOR = (15, 15, 30)
GHOST_ALPHA = 80


class FallingDisc:
    """Animated disc falling into place."""

    def __init__(self, col, target_row, player, cell_size, grid_x, grid_y):
        self.col = col
        self.target_row = target_row
        self.player = player
        self.cell_size = cell_size

        # Physics
        self.x = grid_x + col * cell_size + cell_size // 2
        self.y = grid_y - cell_size  # Start above board
        self.target_y = grid_y + target_row * cell_size + cell_size // 2
        self.vy = 0
        self.gravity = 2500
        self.bounce_damping = 0.35
        self.settled = False
        self.bounce_count = 0
        self.max_bounces = 3

    def update(self, dt):
        if self.settled:
            return

        self.vy += self.gravity * dt
        self.y += self.vy * dt

        # Hit target row
        if self.y >= self.target_y:
            self.y = self.target_y
            self.bounce_count += 1

            if self.bounce_count >= self.max_bounces or abs(self.vy) < 50:
                self.settled = True
                self.y = self.target_y
            else:
                self.vy = -abs(self.vy) * self.bounce_damping

    def get_pos(self):
        return (int(self.x), int(self.y))


class Connect4Game(BaseGame):
    GAME_ID = "connect4"

    def __init__(self, engine, mode="local", **kwargs):
        super().__init__(engine, mode, **kwargs)
        self.difficulty = kwargs.get("difficulty", "medium")

        # Board: 0=empty, 1=player1(red), 2=player2(yellow)
        self.board = [[0] * COLS for _ in range(ROWS)]
        self.current_player = 1
        self.winner = None
        self.winning_cells = None
        self.game_over = False

        # Layout
        self.grid_x = 0
        self.grid_y = 0
        self.cell_size = 0

        # Animations
        self.falling_discs = []
        self.hover_col = -1
        self.anim_time = 0
        self.win_anim = 0
        self.line_anim = 0

        # Status
        self.status_text = ""

        # Bot
        self.bot_delay = 0
        self.bot_thinking = False

        # Network
        if mode == "network":
            self.my_player = 1 if self.network_role == "host" else 2
        else:
            self.my_player = None

        # Particles & UI
        self.particles = ParticleSystem()
        self.buttons = []

    def on_enter(self, **kwargs):
        self._reset_game()
        self._calc_layout()
        self._build_buttons()

    def on_resize(self, w, h):
        self._calc_layout()
        self._build_buttons()

    def _calc_layout(self):
        w, h = self.engine.screen.get_size()
        top_margin = 110
        bottom_margin = 90
        side_margin = 40

        available_h = h - top_margin - bottom_margin
        available_w = w - side_margin * 2

        self.cell_size = min(available_w // COLS, available_h // ROWS)
        grid_w = self.cell_size * COLS
        grid_h = self.cell_size * ROWS

        self.grid_x = (w - grid_w) // 2
        self.grid_y = top_margin + (available_h - grid_h) // 2

    def _build_buttons(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2
        btn_y = h - 70

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
        self.board = [[0] * COLS for _ in range(ROWS)]
        self.current_player = 1
        self.winner = None
        self.winning_cells = None
        self.game_over = False
        self.falling_discs = []
        self.hover_col = -1
        self.win_anim = 0
        self.line_anim = 0
        self.bot_thinking = False
        self.bot_delay = 0
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
                    if self.winner == 1:
                        self.status_text = get_text("you_win", self.lang)
                    else:
                        self.status_text = get_text("you_lose", self.lang)
                elif self.mode == "network":
                    if self.winner == self.my_player:
                        self.status_text = get_text("you_win", self.lang)
                    else:
                        self.status_text = get_text("you_lose", self.lang)
                else:
                    key = "connect4_p1_wins" if self.winner == 1 else "connect4_p2_wins"
                    self.status_text = get_text(key, self.lang)
            else:
                self.status_text = get_text("connect4_draw", self.lang)
        elif self.bot_thinking:
            self.status_text = get_text("bot_thinking", self.lang)
        elif self.mode == "network":
            if self.current_player == self.my_player:
                self.status_text = get_text("your_turn", self.lang)
            else:
                self.status_text = get_text("opponent_turn", self.lang)
        else:
            key = "connect4_p1_turn" if self.current_player == 1 else "connect4_p2_turn"
            self.status_text = get_text(key, self.lang)

    def _get_col_at_pos(self, pos):
        mx, my = pos
        if self.grid_x <= mx < self.grid_x + self.cell_size * COLS:
            col = (mx - self.grid_x) // self.cell_size
            return int(col)
        return -1

    def _get_drop_row(self, col):
        """Get the lowest empty row in a column."""
        for row in range(ROWS - 1, -1, -1):
            if self.board[row][col] == 0:
                return row
        return -1

    def _make_move(self, col):
        """Drop a disc into the column."""
        if self.game_over:
            return False

        row = self._get_drop_row(col)
        if row < 0:
            return False

        # Place on board
        self.board[row][col] = self.current_player

        # Create falling animation
        disc = FallingDisc(
            col, row, self.current_player,
            self.cell_size, self.grid_x, self.grid_y
        )
        self.falling_discs.append(disc)

        # Check win
        winner = check_winner(self.board)
        if winner:
            self.winner = winner
            self.winning_cells = get_winning_cells(self.board)
            self.game_over = True
            self._on_game_over()
        elif is_full(self.board):
            self.game_over = True
            self._on_game_over()
        else:
            self.current_player = 3 - self.current_player
            if self.mode == "bot" and self.current_player == 2:
                self.bot_thinking = True
                self.bot_delay = 0.6

        self._update_status()
        return True

    def _on_game_over(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2
        cy = self.grid_y + (ROWS * self.cell_size) // 2

        if self.winner:
            color = P1_COLOR if self.winner == 1 else P2_COLOR
            for _ in range(4):
                self.particles.emit(
                    x=cx, y=cy, color=color, count=35,
                    speed=250, lifetime=2.0, size=5,
                    glow=True, gravity=100, friction=0.96,
                )

            if self.winning_cells:
                for r, c in self.winning_cells:
                    px = self.grid_x + c * self.cell_size + self.cell_size // 2
                    py = self.grid_y + r * self.cell_size + self.cell_size // 2
                    self.particles.emit(
                        x=px, y=py, color=COLORS["win_color"], count=10,
                        speed=100, lifetime=1.5, size=3,
                        glow=True, friction=0.94,
                    )

            if self.mode == "bot":
                self.record_result("win" if self.winner == 1 else "loss")
            elif self.mode == "network":
                self.record_result(
                    "win" if self.winner == self.my_player else "loss"
                )
        else:
            self.record_result("draw")

        self._build_buttons()
        self._update_status()

    # === Events ===

    def handle_events(self, events):
        if self.handle_disconnect_events(events):
            return

        for event in events:
            for btn in self.buttons:
                btn.handle_event(event)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.exit_game()
                return

            if event.type == pygame.MOUSEMOTION:
                self.hover_col = self._get_col_at_pos(event.pos)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if not self.game_over:
                    col = self._get_col_at_pos(event.pos)
                    if col >= 0:
                        can_move = True
                        if self.mode == "bot" and self.bot_thinking:
                            can_move = False
                        if self.mode == "bot" and self.current_player != 1:
                            can_move = False
                        if (self.mode == "network" and
                                self.current_player != self.my_player):
                            can_move = False
                        if self.is_disconnected:
                            can_move = False

                        if can_move and self._make_move(col):
                            if self.mode == "network":
                                self.send_network_message({
                                    "type": "move",
                                    "data": {"col": col},
                                })

    # === Update ===

    def update(self, dt):
        self.anim_time += dt
        self.update_disconnect(dt)

        # Falling discs
        still_falling = []
        for disc in self.falling_discs:
            disc.update(dt)
            if disc.settled:
                # Landing particles
                px = self.grid_x + disc.col * self.cell_size + self.cell_size // 2
                py = self.grid_y + disc.target_row * self.cell_size + self.cell_size // 2
                color = P1_COLOR if disc.player == 1 else P2_COLOR
                self.particles.emit(
                    x=px, y=py + self.cell_size // 3,
                    color=color, count=8,
                    speed=80, lifetime=0.5, size=2,
                    glow=True,
                    direction="directional", angle=270, spread=150,
                    friction=0.9,
                )
            else:
                still_falling.append(disc)
        self.falling_discs = still_falling

        # Win animation
        if self.game_over and self.winner:
            self.win_anim = min(1.0, self.win_anim + dt * 2)
            self.line_anim = min(1.0, self.line_anim + dt * 3)

        # Bot
        if self.mode == "bot" and self.bot_thinking:
            self.bot_delay -= dt
            if self.bot_delay <= 0:
                board_copy = [row[:] for row in self.board]
                col = get_bot_move(board_copy, 2, self.difficulty)
                if col is not None:
                    self.bot_thinking = False
                    self._make_move(col)

        # Network
        if self.mode == "network" and not self.is_disconnected:
            msgs = self.get_network_messages()
            for msg in msgs:
                if isinstance(msg, NetworkMessage):
                    if msg.msg_type == "move":
                        col = msg.data.get("col")
                        if col is not None:
                            self._make_move(col)
                    elif msg.msg_type == "restart":
                        self._reset_game()
                        self._build_buttons()

        for btn in self.buttons:
            btn.update(dt)
        self.particles.update(dt)

    # === Drawing ===

    def draw(self, screen):
        w, h = screen.get_size()

        # Title
        draw_title(screen, get_text("connect4", self.lang), y=12, font_size=32)

        # Status
        font = get_font(22, bold=True)
        if self.game_over and self.winner:
            color = COLORS["win_color"]
        elif self.game_over:
            color = COLORS["warning"]
        elif self.current_player == 1:
            color = P1_COLOR_LIGHT
        else:
            color = P2_COLOR_LIGHT
        status = font.render(self.status_text, True, color)
        screen.blit(status, (w // 2 - status.get_width() // 2, 55))

        # Ping
        if self.mode == "network" and not self.is_disconnected:
            ping = self.get_ping()
            ping_font = get_font(14)
            ping_color = COLORS["accent"] if ping < 100 else (
                COLORS["warning"] if ping < 300 else COLORS["danger"]
            )
            surf = ping_font.render(f"🏓 {ping}ms", True, ping_color)
            screen.blit(surf, (w - surf.get_width() - 15, 15))

        # Draw hover indicator (arrow above column)
        self._draw_hover_indicator(screen)

        # Draw board
        self._draw_board(screen)

        # Draw falling discs
        for disc in self.falling_discs:
            pos = disc.get_pos()
            color = P1_COLOR if disc.player == 1 else P2_COLOR
            radius = self.cell_size // 2 - 4
            self._draw_disc(screen, pos[0], pos[1], radius, color, disc.player)

        # Draw winning highlight
        if self.winning_cells and self.win_anim > 0:
            self._draw_win_highlight(screen)

        self.particles.draw(screen)

        for btn in self.buttons:
            btn.draw(screen)

        self.draw_disconnect_overlay(screen)

    def _draw_hover_indicator(self, screen):
        """Draw ghost disc and arrow above hovered column."""
        if self.game_over or self.hover_col < 0:
            return

        can_hover = True
        if self.mode == "bot" and (self.current_player != 1 or self.bot_thinking):
            can_hover = False
        if self.mode == "network" and self.current_player != self.my_player:
            can_hover = False
        if self.is_disconnected:
            can_hover = False
        if self._get_drop_row(self.hover_col) < 0:
            can_hover = False

        if not can_hover:
            return

        col = self.hover_col
        row = self._get_drop_row(col)
        if row < 0:
            return

        cx = self.grid_x + col * self.cell_size + self.cell_size // 2
        radius = self.cell_size // 2 - 4

        # Arrow above board
        arrow_y = self.grid_y - 20
        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 4)
        color = P1_COLOR if self.current_player == 1 else P2_COLOR
        alpha_color = (*color, int(150 + 105 * pulse))

        arrow_surf = pygame.Surface((30, 20), pygame.SRCALPHA)
        pygame.draw.polygon(arrow_surf, alpha_color,
                            [(15, 18), (0, 0), (30, 0)])
        screen.blit(arrow_surf, (cx - 15, arrow_y))

        # Ghost disc at landing position
        gy = self.grid_y + row * self.cell_size + self.cell_size // 2
        ghost_surf = pygame.Surface(
            (radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA
        )
        ghost_color = (*color, int(GHOST_ALPHA * pulse))
        pygame.draw.circle(ghost_surf, ghost_color,
                           (radius + 2, radius + 2), radius)
        screen.blit(ghost_surf, (cx - radius - 2, gy - radius - 2))

    def _draw_board(self, screen):
        """Draw the Connect Four board frame and discs."""
        grid_w = self.cell_size * COLS
        grid_h = self.cell_size * ROWS
        board_rect = pygame.Rect(
            self.grid_x - 6, self.grid_y - 6,
            grid_w + 12, grid_h + 12
        )

        # Board background with rounded corners
        pygame.draw.rect(screen, BOARD_COLOR, board_rect, border_radius=12)
        pygame.draw.rect(screen, BOARD_DARK, board_rect, 3, border_radius=12)

        # Cells
        for row in range(ROWS):
            for col in range(COLS):
                cx = self.grid_x + col * self.cell_size + self.cell_size // 2
                cy = self.grid_y + row * self.cell_size + self.cell_size // 2
                radius = self.cell_size // 2 - 4

                # Check if there's a falling disc for this cell
                has_falling = any(
                    d.col == col and d.target_row == row and not d.settled
                    for d in self.falling_discs
                )

                cell_val = self.board[row][col]
                if cell_val == 0 or has_falling:
                    # Empty hole
                    pygame.draw.circle(screen, EMPTY_COLOR, (cx, cy), radius)
                    # Inner shadow for depth
                    shadow_surf = pygame.Surface(
                        (radius * 2, radius * 2), pygame.SRCALPHA
                    )
                    pygame.draw.circle(shadow_surf, (0, 0, 0, 30),
                                       (radius, radius), radius)
                    pygame.draw.circle(shadow_surf, (0, 0, 0, 0),
                                       (radius - 2, radius - 2), radius - 3)
                    screen.blit(shadow_surf, (cx - radius, cy - radius))
                else:
                    # Placed disc
                    color = P1_COLOR if cell_val == 1 else P2_COLOR
                    is_winner = (self.winning_cells and
                                 (row, col) in self.winning_cells)
                    if is_winner:
                        pulse = 0.7 + 0.3 * math.sin(self.anim_time * 5)
                        color = tuple(
                            int(c * pulse + COLORS["win_color"][i] * (1 - pulse))
                            for i, c in enumerate(color)
                        )
                    self._draw_disc(screen, cx, cy, radius, color, cell_val)

    def _draw_disc(self, screen, cx, cy, radius, color, player):
        """Draw a disc with 3D-like shading."""
        # Glow
        glow_surf = pygame.Surface((radius * 3, radius * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*color, 30),
                           (radius * 3 // 2, radius * 3 // 2),
                           radius + 4)
        screen.blit(glow_surf,
                    (cx - radius * 3 // 2, cy - radius * 3 // 2))

        # Main disc
        pygame.draw.circle(screen, color, (cx, cy), radius)

        # Highlight (top-left)
        highlight_color = (
            min(255, color[0] + 70),
            min(255, color[1] + 70),
            min(255, color[2] + 70),
        )
        highlight_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(highlight_surf, (*highlight_color, 100),
                           (radius - radius // 4, radius - radius // 4),
                           radius // 3)
        screen.blit(highlight_surf, (cx - radius, cy - radius))

        # Dark edge (bottom-right)
        dark_color = (
            max(0, color[0] - 50),
            max(0, color[1] - 50),
            max(0, color[2] - 50),
        )
        pygame.draw.circle(screen, dark_color, (cx, cy), radius, 2)

    def _draw_win_highlight(self, screen):
        """Draw highlight on winning cells."""
        if not self.winning_cells:
            return

        # Connecting line
        cells_px = []
        for r, c in self.winning_cells:
            px = self.grid_x + c * self.cell_size + self.cell_size // 2
            py = self.grid_y + r * self.cell_size + self.cell_size // 2
            cells_px.append((px, py))

        if len(cells_px) >= 2:
            start = cells_px[0]
            end = cells_px[-1]
            progress = min(1.0, self.line_anim)
            current_end = (
                int(start[0] + (end[0] - start[0]) * progress),
                int(start[1] + (end[1] - start[1]) * progress),
            )

            # Glow line
            glow_surf = pygame.Surface(
                self.engine.screen.get_size(), pygame.SRCALPHA
            )
            pygame.draw.line(glow_surf, (*COLORS["win_color"], 80),
                             start, current_end, 14)
            screen.blit(glow_surf, (0, 0))

            pygame.draw.line(screen, COLORS["win_color"],
                             start, current_end, 4)

            # Sparkles
            if progress > 0.1:
                self.particles.emit(
                    x=current_end[0], y=current_end[1],
                    color=COLORS["win_color"], count=1,
                    speed=40, lifetime=0.4, size=2,
                    glow=True, friction=0.9,
                )
