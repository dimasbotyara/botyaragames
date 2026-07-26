"""Pong game scene — the full experience."""

import pygame
import math
import random
from games.base_game import BaseGame
from games.pong.bot import PongBot
from core.ui import Button, draw_title, get_font
from core.localization import get_text
from core.particles import ParticleSystem
from core.network import NetworkMessage
from settings import COLORS


# === Constants ===
WINNING_SCORE = 11
BALL_BASE_SPEED = 400
BALL_SPEED_INCREMENT = 0.003   # % increase per second
BALL_MAX_SPEED_MULT = 1.8
PADDLE_SPEED = 500
PADDLE_WIDTH = 14
PADDLE_HEIGHT_RATIO = 0.15    # % of field height
PADDLE_MARGIN = 30
BALL_SIZE = 10
COUNTDOWN_TIME = 2.0


class Ball:
    """The pong ball with trail effect."""

    def __init__(self):
        self.x = 0
        self.y = 0
        self.vx = 0
        self.vy = 0
        self.speed_mult = 1.0
        self.rally_time = 0.0
        self.trail = []  # List of (x, y, age)
        self.size = BALL_SIZE
        self.active = False

    def reset(self, field_w, field_h, direction=1):
        """Reset ball to center."""
        self.x = field_w / 2
        self.y = field_h / 2

        angle = random.uniform(-math.pi / 5, math.pi / 5)
        self.vx = math.cos(angle) * BALL_BASE_SPEED * direction
        self.vy = math.sin(angle) * BALL_BASE_SPEED

        self.speed_mult = 1.0
        self.rally_time = 0.0
        self.trail.clear()
        self.active = False

    def update(self, dt):
        if not self.active:
            return

        self.rally_time += dt

        # Gradual speed increase
        self.speed_mult = min(
            BALL_MAX_SPEED_MULT,
            1.0 + self.rally_time * BALL_SPEED_INCREMENT
        )

        self.x += self.vx * self.speed_mult * dt
        self.y += self.vy * self.speed_mult * dt

        # Trail
        self.trail.append((self.x, self.y, 0))
        # Age trail
        new_trail = []
        for tx, ty, age in self.trail:
            age += dt
            if age < 0.3:
                new_trail.append((tx, ty, age))
        self.trail = new_trail


class Paddle:
    """A paddle."""

    def __init__(self, x, field_h):
        self.x = x
        self.w = PADDLE_WIDTH
        self.h = int(field_h * PADDLE_HEIGHT_RATIO)
        self.y = field_h / 2 - self.h / 2
        self.field_h = field_h
        self.vy = 0  # For spin calculation
        self.hit_anim = 0.0
        self.glow = 0.0

    def move(self, direction, dt, speed_mult=1.0):
        """Move paddle. direction: -1 (up) to 1 (down), can be fractional."""
        speed = PADDLE_SPEED * speed_mult
        old_y = self.y
        self.y += direction * speed * dt
        self.y = max(0, min(self.field_h - self.h, self.y))
        self.vy = (self.y - old_y) / max(0.001, dt)

    def get_rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, self.h)

    def get_center_y(self):
        return self.y + self.h / 2


class PongGame(BaseGame):
    GAME_ID = "pong"

    def __init__(self, engine, mode="local", **kwargs):
        super().__init__(engine, mode, **kwargs)

        self.difficulty = kwargs.get("difficulty", "medium")

        # Field dimensions (set in on_enter based on screen)
        self.field_x = 0
        self.field_y = 0
        self.field_w = 0
        self.field_h = 0

        # Game objects
        self.ball = Ball()
        self.paddle_left = None
        self.paddle_right = None
        self.bot_ai = None

        # Score
        self.score_left = 0
        self.score_right = 0
        self.round_num = 0

        # State
        self.state = "countdown"  # countdown, playing, scored, game_over, paused
        self.countdown_timer = COUNTDOWN_TIME
        self.scored_timer = 0
        self.winner = None
        self.last_scorer = None  # "left" or "right"

        # Particles
        self.particles = ParticleSystem()

        # UI
        self.buttons = []

        # Network
        if mode == "network":
            self.is_left = (self.network_role == "host")
        else:
            self.is_left = True

        # Input state
        self.keys_held = set()

        # Visual
        self.anim_time = 0
        self.screen_shake = 0
        self.shake_intensity = 0

        # Midline particles timer
        self._midline_timer = 0

    def on_enter(self, **kwargs):
        self._calc_layout()
        self._init_game()

    def on_resize(self, w, h):
        self._calc_layout()
        self._build_buttons()

    def _calc_layout(self):
        w, h = self.engine.screen.get_size()
        margin = 40
        top_margin = 90
        bottom_margin = 80

        self.field_x = margin
        self.field_y = top_margin
        self.field_w = w - margin * 2
        self.field_h = h - top_margin - bottom_margin

    def _init_game(self):
        self.score_left = 0
        self.score_right = 0
        self.round_num = 0
        self.winner = None

        # Create paddles
        self.paddle_left = Paddle(
            self.field_x + PADDLE_MARGIN,
            self.field_h
        )
        self.paddle_right = Paddle(
            self.field_x + self.field_w - PADDLE_MARGIN - PADDLE_WIDTH,
            self.field_h
        )

        # Bot
        if self.mode == "bot":
            self.bot_ai = PongBot(self.difficulty)

        self._start_round()

    def _start_round(self):
        self.round_num += 1
        direction = 1 if self.last_scorer == "right" else -1
        if self.round_num == 1:
            direction = random.choice([-1, 1])

        self.ball.reset(self.field_w, self.field_h, direction)
        self.state = "countdown"
        self.countdown_timer = COUNTDOWN_TIME
        self.screen_shake = 0

        if self.paddle_left:
            self.paddle_left.y = self.field_h / 2 - self.paddle_left.h / 2
        if self.paddle_right:
            self.paddle_right.y = self.field_h / 2 - self.paddle_right.h / 2

        if self.bot_ai:
            self.bot_ai.reset_round()

        self._build_buttons()

    def _build_buttons(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2
        btn_y = h - 65

        self.buttons = []

        if self.state == "game_over":
            self.buttons.append(
                Button(cx - 170, btn_y, 160, 50,
                       get_text("play_again", self.lang), font_size=20,
                       hover_color=COLORS["primary_dark"],
                       on_click=self._restart_game)
            )
        if self.state in ("game_over", "paused"):
            self.buttons.append(
                Button(cx + 10 if self.state == "game_over" else cx - 80,
                       btn_y, 160, 50,
                       get_text("back", self.lang), font_size=20,
                       color=COLORS["bg_light"],
                       hover_color=(80, 30, 30),
                       on_click=self.exit_game)
            )

    def _restart_game(self):
        self._init_game()
        if self.mode == "network":
            self.send_network_message({"type": "restart"})

    def _score(self, side):
        """Handle scoring."""
        self.last_scorer = side
        self.scored_timer = 1.5
        self.state = "scored"

        if side == "left":
            self.score_left += 1
        else:
            self.score_right += 1

        # Screen shake
        self.screen_shake = 0.3
        self.shake_intensity = 8

        # Particles explosion at ball position
        ball_screen_x = self.field_x + self.ball.x
        ball_screen_y = self.field_y + self.ball.y
        color = COLORS["x_color"] if side == "left" else COLORS["o_color"]
        self.particles.emit(
            x=ball_screen_x, y=ball_screen_y,
            color=color, count=40,
            speed=300, lifetime=1.2, size=4,
            glow=True, gravity=150, friction=0.95,
        )

        # Bot scoring callback
        if self.bot_ai:
            self.bot_ai.on_score(side == "right")

        # Record stats for network/bot
        if self.score_left >= WINNING_SCORE or self.score_right >= WINNING_SCORE:
            self.state = "game_over"
            if self.score_left >= WINNING_SCORE:
                self.winner = "left"
            else:
                self.winner = "right"
            self._on_game_over_pong()

    def _on_game_over_pong(self):
        """Handle game over."""
        w, h = self.engine.screen.get_size()

        # Fireworks!
        for _ in range(5):
            fx = random.randint(self.field_x + 50, self.field_x + self.field_w - 50)
            fy = random.randint(self.field_y + 50, self.field_y + self.field_h - 50)
            color = random.choice([
                COLORS["primary"], COLORS["secondary"],
                COLORS["accent"], COLORS["warning"],
            ])
            self.particles.emit(
                x=fx, y=fy, color=color, count=30,
                speed=200, lifetime=2.0, size=5,
                glow=True, gravity=80, friction=0.96,
            )

        # Record stats
        if self.mode == "bot":
            self.record_result("win" if self.winner == "left" else "loss")
        elif self.mode == "network":
            if (self.winner == "left" and self.is_left) or \
               (self.winner == "right" and not self.is_left):
                self.record_result("win")
            else:
                self.record_result("loss")

        self._build_buttons()

    def _ball_paddle_collision(self, ball, paddle, is_left):
        """Check and handle ball-paddle collision."""
        ball_rect = pygame.Rect(
            ball.x - ball.size / 2,
            ball.y - ball.size / 2,
            ball.size,
            ball.size
        )
        paddle_rect = pygame.Rect(
            paddle.x - self.field_x,
            paddle.y,
            paddle.w,
            paddle.h
        )

        if not ball_rect.colliderect(paddle_rect):
            return False

        # Where on paddle did it hit? (-1 = top edge, 0 = center, 1 = bottom edge)
        relative_y = (ball.y - (paddle.y + paddle.h / 2)) / (paddle.h / 2)
        relative_y = max(-1, min(1, relative_y))

        # Reflect X
        ball.vx = -ball.vx

        # Adjust angle based on where it hit
        speed = math.sqrt(ball.vx ** 2 + ball.vy ** 2)
        max_angle = math.pi / 3.5  # ~51 degrees max
        angle = relative_y * max_angle

        direction = 1 if is_left else -1
        ball.vx = abs(speed * math.cos(angle)) * direction
        ball.vy = speed * math.sin(angle)

        # Add paddle momentum (spin)
        ball.vy += paddle.vy * 0.15

        # Push ball out of paddle
        if is_left:
            ball.x = paddle_rect.right + ball.size / 2 + 1
        else:
            ball.x = paddle_rect.left - ball.size / 2 - 1

        # Hit animation
        paddle.hit_anim = 1.0
        paddle.glow = 1.0

        # Particles on hit
        hit_x = self.field_x + (paddle_rect.right if is_left else paddle_rect.left)
        hit_y = self.field_y + ball.y
        color = COLORS["x_color"] if is_left else COLORS["o_color"]
        count = 8 + int(ball.speed_mult * 8)
        self.particles.emit(
            x=hit_x, y=hit_y, color=color,
            count=count, speed=150 * ball.speed_mult,
            lifetime=0.6, size=3, glow=True,
            direction="directional",
            angle=0 if is_left else 180,
            spread=90, friction=0.92,
        )

        # Screen shake proportional to speed
        self.screen_shake = 0.1
        self.shake_intensity = 2 + ball.speed_mult * 2

        # Notify bot of direction change
        if self.bot_ai:
            self.bot_ai.on_ball_direction_change()

        return True

    # === Input / Events ===

    def handle_events(self, events):
        if self.handle_disconnect_events(events):
            return

        for event in events:
            for btn in self.buttons:
                btn.handle_event(event)

            if event.type == pygame.KEYDOWN:
                self.keys_held.add(event.key)

                if event.key == pygame.K_ESCAPE:
                    if self.state == "playing":
                        self.state = "paused"
                        self._build_buttons()
                    elif self.state == "paused":
                        self.state = "playing"
                        self._build_buttons()
                    elif self.state == "game_over":
                        self.exit_game()
                        return

                if event.key == pygame.K_SPACE:
                    if self.state == "paused":
                        self.state = "playing"
                        self._build_buttons()

            if event.type == pygame.KEYUP:
                self.keys_held.discard(event.key)

    # === Update ===

    def update(self, dt):
        self.anim_time += dt
        self.update_disconnect(dt)

        # Screen shake decay
        if self.screen_shake > 0:
            self.screen_shake -= dt
            if self.screen_shake < 0:
                self.screen_shake = 0

        # Paddle hit animation decay
        if self.paddle_left:
            self.paddle_left.hit_anim *= max(0, 1 - dt * 8)
            self.paddle_left.glow *= max(0, 1 - dt * 4)
        if self.paddle_right:
            self.paddle_right.hit_anim *= max(0, 1 - dt * 8)
            self.paddle_right.glow *= max(0, 1 - dt * 4)

        self.particles.update(dt)

        if self.state == "countdown":
            self._update_countdown(dt)
        elif self.state == "playing":
            self._update_playing(dt)
        elif self.state == "scored":
            self.scored_timer -= dt
            if self.scored_timer <= 0:
                self._start_round()
        elif self.state == "game_over":
            self._spawn_fireworks(dt)

        # Network
        if self.mode == "network":
            self._update_network(dt)

        for btn in self.buttons:
            btn.update(dt)

    def _update_countdown(self, dt):
        self.countdown_timer -= dt
        if self.countdown_timer <= 0:
            self.state = "playing"
            self.ball.active = True
            self._build_buttons()

    def _update_playing(self, dt):
        # === Input: Left paddle ===
        if self.mode in ("local", "bot"):
            direction = 0
            if pygame.K_w in self.keys_held:
                direction -= 1
            if pygame.K_s in self.keys_held:
                direction += 1
            if direction != 0:
                self.paddle_left.move(direction, dt)
        elif self.mode == "network":
            if self.is_left:
                direction = 0
                if pygame.K_w in self.keys_held or pygame.K_UP in self.keys_held:
                    direction -= 1
                if pygame.K_s in self.keys_held or pygame.K_DOWN in self.keys_held:
                    direction += 1
                if direction != 0:
                    self.paddle_left.move(direction, dt)

        # === Input: Right paddle ===
        if self.mode == "local":
            direction = 0
            if pygame.K_UP in self.keys_held:
                direction -= 1
            if pygame.K_DOWN in self.keys_held:
                direction += 1
            if direction != 0:
                self.paddle_right.move(direction, dt)
        elif self.mode == "bot":
            self._update_bot(dt)
        elif self.mode == "network":
            if not self.is_left:
                direction = 0
                if pygame.K_w in self.keys_held or pygame.K_UP in self.keys_held:
                    direction -= 1
                if pygame.K_s in self.keys_held or pygame.K_DOWN in self.keys_held:
                    direction += 1
                if direction != 0:
                    self.paddle_right.move(direction, dt)

        # === Ball physics ===
        self.ball.update(dt)

        # Wall bounces (top/bottom)
        if self.ball.y - self.ball.size / 2 <= 0:
            self.ball.y = self.ball.size / 2
            self.ball.vy = abs(self.ball.vy)
            self._wall_bounce_effect("top")
        elif self.ball.y + self.ball.size / 2 >= self.field_h:
            self.ball.y = self.field_h - self.ball.size / 2
            self.ball.vy = -abs(self.ball.vy)
            self._wall_bounce_effect("bottom")

        # Paddle collisions
        if self.ball.vx < 0:
            self._ball_paddle_collision(self.ball, self.paddle_left, True)
        if self.ball.vx > 0:
            self._ball_paddle_collision(self.ball, self.paddle_right, False)

        # Scoring
        if self.ball.x < -self.ball.size:
            self._score("right")
        elif self.ball.x > self.field_w + self.ball.size:
            self._score("left")

    def _update_bot(self, dt):
        """Update bot AI."""
        if not self.bot_ai:
            return

        move = self.bot_ai.update(
            dt=dt,
            ball_x=self.ball.x,
            ball_y=self.ball.y,
            ball_vx=self.ball.vx,
            ball_vy=self.ball.vy,
            paddle_y=self.paddle_right.y,
            paddle_h=self.paddle_right.h,
            field_h=self.field_h,
            field_w=self.field_w,
            paddle_x=self.paddle_right.x - self.field_x,
        )

        if move != 0:
            self.paddle_right.move(move, dt, abs(move))

    def _wall_bounce_effect(self, side):
        """Visual effect when ball bounces off wall."""
        bx = self.field_x + self.ball.x
        if side == "top":
            by = self.field_y
        else:
            by = self.field_y + self.field_h

        self.particles.emit(
            x=bx, y=by,
            color=COLORS["primary"], count=5,
            speed=80, lifetime=0.4, size=2,
            glow=True,
            direction="directional",
            angle=90 if side == "top" else 270,
            spread=120, friction=0.9,
        )

    def _update_network(self, dt):
        """Send/receive network state."""
        msgs = self.get_network_messages()
        for msg in msgs:
            if isinstance(msg, NetworkMessage):
                if msg.msg_type == "state":
                    self._apply_network_state(msg.data)
                elif msg.msg_type == "restart":
                    self._init_game()

        # Send state (host sends ball + left paddle, client sends right paddle)
        if self.is_left:
            self.send_network_message({
                "type": "state",
                "data": {
                    "ball_x": self.ball.x,
                    "ball_y": self.ball.y,
                    "ball_vx": self.ball.vx,
                    "ball_vy": self.ball.vy,
                    "paddle_y": self.paddle_left.y,
                    "score_left": self.score_left,
                    "score_right": self.score_right,
                    "state": self.state,
                },
            })
        else:
            self.send_network_message({
                "type": "state",
                "data": {
                    "paddle_y": self.paddle_right.y,
                },
            })

    def _apply_network_state(self, data):
        """Apply received network state."""
        if self.is_left:
            # Host receives client's paddle position
            if "paddle_y" in data:
                self.paddle_right.y = data["paddle_y"]
        else:
            # Client receives full state from host
            if "ball_x" in data:
                self.ball.x = data["ball_x"]
                self.ball.y = data["ball_y"]
                self.ball.vx = data["ball_vx"]
                self.ball.vy = data["ball_vy"]
            if "paddle_y" in data:
                self.paddle_left.y = data["paddle_y"]
            if "score_left" in data:
                self.score_left = data["score_left"]
                self.score_right = data["score_right"]

    def _spawn_fireworks(self, dt):
        """Spawn fireworks during game over."""
        self._midline_timer += dt
        if self._midline_timer > 0.4:
            self._midline_timer = 0
            fx = random.randint(self.field_x + 50,
                                self.field_x + self.field_w - 50)
            fy = random.randint(self.field_y + 50,
                                self.field_y + self.field_h - 50)
            color = random.choice([
                COLORS["primary"], COLORS["secondary"],
                COLORS["accent"], COLORS["warning"],
            ])
            self.particles.emit(
                x=fx, y=fy, color=color, count=15,
                speed=150, lifetime=1.5, size=4,
                glow=True, gravity=60, friction=0.96,
            )

    # === Drawing ===

    def draw(self, screen):
        w, h = screen.get_size()

        # Screen shake offset
        shake_x, shake_y = 0, 0
        if self.screen_shake > 0:
            shake_x = random.randint(
                -int(self.shake_intensity), int(self.shake_intensity)
            )
            shake_y = random.randint(
                -int(self.shake_intensity), int(self.shake_intensity)
            )

        # Draw field
        self._draw_field(screen, shake_x, shake_y)

        # Draw paddles
        self._draw_paddle(screen, self.paddle_left, COLORS["x_color"],
                          shake_x, shake_y)
        self._draw_paddle(screen, self.paddle_right, COLORS["o_color"],
                          shake_x, shake_y)

        # Draw ball
        if self.state not in ("countdown",):
            self._draw_ball(screen, shake_x, shake_y)
        elif self.state == "countdown" and self.countdown_timer < COUNTDOWN_TIME * 0.5:
            self._draw_ball(screen, shake_x, shake_y)

        # Score
        self._draw_score(screen)

        # Speed indicator
        if self.state == "playing" and self.ball.speed_mult > 1.05:
            self._draw_speed(screen)

        # Countdown / state overlays
        if self.state == "countdown":
            self._draw_countdown(screen)
        elif self.state == "scored":
            self._draw_scored(screen)
        elif self.state == "game_over":
            self._draw_game_over(screen)
        elif self.state == "paused":
            self._draw_paused(screen)

        # Controls hint
        if self.state == "countdown" and self.round_num == 1:
            self._draw_controls_hint(screen)

        # Ping
        if self.mode == "network" and not self.is_disconnected:
            ping = self.get_ping()
            ping_font = get_font(14)
            ping_color = COLORS["accent"] if ping < 50 else (
                COLORS["warning"] if ping < 150 else COLORS["danger"]
            )
            surf = ping_font.render(f"🏓 {ping}ms", True, ping_color)
            screen.blit(surf, (w - surf.get_width() - 15, 10))

        # Bot focus indicator
        if self.mode == "bot" and self.bot_ai and self.state == "playing":
            self._draw_bot_focus(screen)

        # Particles
        self.particles.draw(screen)

        # Buttons
        for btn in self.buttons:
            btn.draw(screen)

        # Disconnect overlay
        self.draw_disconnect_overlay(screen)

    def _draw_field(self, screen, sx, sy):
        """Draw the playing field."""
        field_rect = pygame.Rect(
            self.field_x + sx, self.field_y + sy,
            self.field_w, self.field_h
        )

        # Background
        field_surf = pygame.Surface((self.field_w, self.field_h), pygame.SRCALPHA)
        field_surf.fill((*COLORS["bg_medium"], 150))
        screen.blit(field_surf, field_rect.topleft)

        # Border
        pygame.draw.rect(screen, COLORS["border"], field_rect, 2,
                         border_radius=4)

        # Center line (dashed)
        cx = self.field_x + self.field_w // 2 + sx
        dash_len = 15
        gap = 10
        y = self.field_y + sy
        while y < self.field_y + self.field_h + sy:
            end_y = min(y + dash_len, self.field_y + self.field_h + sy)
            pygame.draw.line(screen, (*COLORS["border"], 100),
                             (cx, y), (cx, end_y), 2)
            y += dash_len + gap

        # Center circle
        pygame.draw.circle(screen, COLORS["border"],
                           (cx, self.field_y + self.field_h // 2 + sy),
                           40, 1)

    def _draw_paddle(self, screen, paddle, color, sx, sy):
        """Draw paddle with glow effect."""
        rect = pygame.Rect(
            int(paddle.x + sx),
            int(self.field_y + paddle.y + sy),
            paddle.w,
            paddle.h
        )

        # Glow
        glow_amount = paddle.glow
        if glow_amount > 0.05:
            glow_rect = rect.inflate(
                int(12 * glow_amount), int(8 * glow_amount)
            )
            glow_surf = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            glow_alpha = int(60 * glow_amount)
            pygame.draw.rect(glow_surf, (*color, glow_alpha),
                             (0, 0, *glow_rect.size), border_radius=8)
            screen.blit(glow_surf, glow_rect.topleft)

        # Hit stretch effect
        draw_rect = rect.copy()
        if paddle.hit_anim > 0.05:
            stretch = int(4 * paddle.hit_anim)
            draw_rect = draw_rect.inflate(stretch * 2, -stretch)

        # Main paddle
        pygame.draw.rect(screen, color, draw_rect, border_radius=6)

        # Highlight
        highlight = pygame.Rect(draw_rect.x + 2, draw_rect.y + 2,
                                draw_rect.w - 4, draw_rect.h // 3)
        highlight_surf = pygame.Surface(highlight.size, pygame.SRCALPHA)
        pygame.draw.rect(highlight_surf, (255, 255, 255, 30),
                         (0, 0, *highlight.size), border_radius=4)
        screen.blit(highlight_surf, highlight.topleft)

    def _draw_ball(self, screen, sx, sy):
        """Draw ball with trail and glow."""
        # Trail
        for tx, ty, age in self.ball.trail:
            alpha = int(120 * (1 - age / 0.3))
            size = max(1, int(self.ball.size * (1 - age / 0.3) * 0.7))
            trail_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)

            speed_ratio = min(1, (self.ball.speed_mult - 1) / (BALL_MAX_SPEED_MULT - 1))
            tr = int(255 * speed_ratio)
            tg = int(200 * (1 - speed_ratio))
            tb = int(255 * (1 - speed_ratio))

            pygame.draw.circle(trail_surf, (tr, tg, tb, alpha),
                               (size, size), size)
            screen.blit(trail_surf,
                        (int(self.field_x + tx - size + sx),
                         int(self.field_y + ty - size + sy)))

        # Ball glow
        bx = int(self.field_x + self.ball.x + sx)
        by = int(self.field_y + self.ball.y + sy)
        glow_size = self.ball.size * 3

        glow_surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)

        speed_ratio = min(1, (self.ball.speed_mult - 1) / (BALL_MAX_SPEED_MULT - 1))
        br = int(200 + 55 * speed_ratio)
        bg = int(220 * (1 - speed_ratio * 0.5))
        bb = int(255 * (1 - speed_ratio))

        pygame.draw.circle(glow_surf, (br, bg, bb, 40),
                           (glow_size, glow_size), glow_size)
        pygame.draw.circle(glow_surf, (br, bg, bb, 80),
                           (glow_size, glow_size), glow_size // 2)
        screen.blit(glow_surf, (bx - glow_size, by - glow_size))

        # Ball core
        pygame.draw.circle(screen, (br, bg, bb),
                           (bx, by), self.ball.size)
        # White center
        pygame.draw.circle(screen, (255, 255, 255),
                           (bx, by), self.ball.size // 2)

    def _draw_score(self, screen):
        """Draw score display."""
        w = screen.get_width()
        font = get_font(48, bold=True)

        # Left score
        left_surf = font.render(str(self.score_left), True, COLORS["x_color"])
        screen.blit(left_surf, (w // 2 - left_surf.get_width() - 30, 20))

        # Separator
        sep_font = get_font(36)
        sep = sep_font.render(":", True, COLORS["text_dark"])
        screen.blit(sep, (w // 2 - sep.get_width() // 2, 28))

        # Right score
        right_surf = font.render(str(self.score_right), True, COLORS["o_color"])
        screen.blit(right_surf, (w // 2 + 30, 20))

    def _draw_speed(self, screen):
        """Draw speed indicator."""
        speed_pct = self.ball.speed_mult * 100
        font = get_font(14)

        ratio = min(1, (self.ball.speed_mult - 1) / (BALL_MAX_SPEED_MULT - 1))
        color = (
            int(100 + 155 * ratio),
            int(255 * (1 - ratio * 0.7)),
            int(100 * (1 - ratio)),
        )
        text = get_text("pong_speed", self.lang, speed_pct)
        surf = font.render(text, True, color)
        screen.blit(surf, (self.field_x + 5, self.field_y + self.field_h + 5))

    def _draw_countdown(self, screen):
        """Draw countdown overlay."""
        w, h = screen.get_size()
        cx = w // 2
        cy = self.field_y + self.field_h // 2

        if self.countdown_timer > 1.0:
            text = get_text("pong_get_ready", self.lang)
            color = COLORS["warning"]
            scale = 1.0 + 0.05 * math.sin(self.anim_time * 6)
        elif self.countdown_timer > 0:
            text = get_text("pong_go", self.lang)
            color = COLORS["accent"]
            scale = 1.0 + (1.0 - self.countdown_timer) * 0.3
        else:
            return

        font_size = int(48 * scale)
        font = get_font(font_size, bold=True)
        surf = font.render(text, True, color)

        # Glow behind text
        glow = pygame.Surface(
            (surf.get_width() + 40, surf.get_height() + 20), pygame.SRCALPHA
        )
        glow.fill((*COLORS["bg_dark"], 180))
        screen.blit(glow, (cx - glow.get_width() // 2, cy - glow.get_height() // 2))

        screen.blit(surf, (cx - surf.get_width() // 2,
                           cy - surf.get_height() // 2))

    def _draw_scored(self, screen):
        """Draw scored flash."""
        w, h = screen.get_size()
        cx = w // 2
        cy = self.field_y + self.field_h // 2

        scorer = get_text("pong_player1", self.lang) if self.last_scorer == "left" \
            else (get_text("pong_bot", self.lang) if self.mode == "bot"
                  else get_text("pong_player2", self.lang))
        color = COLORS["x_color"] if self.last_scorer == "left" else COLORS["o_color"]

        font = get_font(36, bold=True)
        text = font.render(f"⚡ {scorer}!", True, color)

        bg = pygame.Surface((text.get_width() + 40, text.get_height() + 20),
                            pygame.SRCALPHA)
        bg.fill((*COLORS["bg_dark"], 200))
        screen.blit(bg, (cx - bg.get_width() // 2, cy - bg.get_height() // 2))
        screen.blit(text, (cx - text.get_width() // 2,
                           cy - text.get_height() // 2))

    def _draw_game_over(self, screen):
        """Draw game over screen."""
        w, h = screen.get_size()
        cx = w // 2
        cy = self.field_y + self.field_h // 2

        # Determine winner name
        if self.winner == "left":
            if self.mode == "network" and not self.is_left:
                name = get_text("opponent_turn", self.lang)
            else:
                name = get_text("pong_player1", self.lang)
        else:
            if self.mode == "bot":
                name = get_text("pong_bot", self.lang)
            else:
                name = get_text("pong_player2", self.lang)

        # Background overlay
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((*COLORS["bg_dark"], 160))
        screen.blit(overlay, (0, 0))

        color = COLORS["win_color"]
        win_text = get_text("pong_wins", self.lang, name)

        pulse = 1.0 + 0.05 * math.sin(self.anim_time * 3)
        font = get_font(int(44 * pulse), bold=True)
        surf = font.render(win_text, True, color)
        screen.blit(surf, (cx - surf.get_width() // 2, cy - 60))

        # Final score
        score_font = get_font(28)
        score_text = f"{self.score_left}  :  {self.score_right}"
        score_surf = score_font.render(score_text, True, COLORS["text_gray"])
        screen.blit(score_surf, (cx - score_surf.get_width() // 2, cy))

    def _draw_paused(self, screen):
        """Draw pause overlay."""
        w, h = screen.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((*COLORS["bg_dark"], 180))
        screen.blit(overlay, (0, 0))

        cx = w // 2
        cy = h // 2

        font = get_font(48, bold=True)
        text = font.render(get_text("pong_paused", self.lang),
                           True, COLORS["warning"])
        screen.blit(text, (cx - text.get_width() // 2, cy - 60))

        hint_font = get_font(20)
        hint = hint_font.render(get_text("pong_press_space", self.lang),
                                True, COLORS["text_gray"])
        screen.blit(hint, (cx - hint.get_width() // 2, cy + 10))

    def _draw_controls_hint(self, screen):
        """Draw control hints on first round."""
        font = get_font(16)

        # Left player
        left_text = get_text("pong_controls_left", self.lang)
        left_label = get_text("pong_player1", self.lang)

        surf1 = font.render(left_label, True, COLORS["x_color"])
        screen.blit(surf1, (self.field_x + 10,
                            self.field_y + self.field_h + 8))
        surf2 = font.render(left_text, True, COLORS["text_dark"])
        screen.blit(surf2, (self.field_x + 10,
                            self.field_y + self.field_h + 28))

        # Right player
        if self.mode == "bot":
            right_label = get_text("pong_bot", self.lang)
            right_text = self.difficulty.upper()
        else:
            right_label = get_text("pong_player2", self.lang)
            right_text = get_text("pong_controls_right", self.lang)

        surf3 = font.render(right_label, True, COLORS["o_color"])
        screen.blit(surf3, (self.field_x + self.field_w - surf3.get_width() - 10,
                            self.field_y + self.field_h + 8))
        surf4 = font.render(right_text, True, COLORS["text_dark"])
        screen.blit(surf4, (self.field_x + self.field_w - surf4.get_width() - 10,
                            self.field_y + self.field_h + 28))

    def _draw_bot_focus(self, screen):
        """Draw bot focus/concentration indicator."""
        if not self.bot_ai:
            return

        _, _, _, _, focus = self.bot_ai.get_effective_stats()

        w = screen.get_width()
        bar_w = 80
        bar_h = 6
        bar_x = w - bar_w - 15
        bar_y = 55

        font = get_font(12)

        # Label
        label_text = "🧠"
        label = font.render(label_text, True, COLORS["text_dark"])
        screen.blit(label, (bar_x - 20, bar_y - 3))

        # Background
        pygame.draw.rect(screen, COLORS["bg_dark"],
                         (bar_x, bar_y, bar_w, bar_h), border_radius=3)

        # Fill
        fill_w = int(bar_w * focus)
        if focus > 0.6:
            color = COLORS["accent"]
        elif focus > 0.3:
            color = COLORS["warning"]
        else:
            color = COLORS["danger"]

        if fill_w > 0:
            pygame.draw.rect(screen, color,
                             (bar_x, bar_y, fill_w, bar_h), border_radius=3)