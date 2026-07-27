"""Reaction Duel game scene."""

import pygame
import math
import random
import time
from games.base_game import BaseGame
from games.reaction.bot import ReactionBot
from core.ui import Button, draw_title, get_font
from core.localization import get_text
from core.particles import ParticleSystem
from core.network import NetworkMessage
from settings import COLORS


WINNING_SCORE = 5
FAKE_COLORS = {
    "red": (255, 60, 60),
    "blue": (60, 100, 255),
    "yellow": (255, 220, 40),
    "purple": (180, 60, 255),
}
REAL_COLOR = (40, 255, 100)  # green
SIGNAL_SIZE_RATIO = 0.35


class ReactionGame(BaseGame):
    GAME_ID = "reaction"

    def __init__(self, engine, mode="local", **kwargs):
        super().__init__(engine, mode, **kwargs)
        self.difficulty = kwargs.get("difficulty", "medium")

        # Scores
        self.score_p1 = 0
        self.score_p2 = 0
        self.round_num = 0

        # State machine
        # states: intro, waiting, fake_signal, real_signal,
        #         round_result, game_over
        self.state = "intro"
        self.state_timer = 0

        # Round data
        self.wait_duration = 0
        self.signal_time = 0
        self.signal_color = REAL_COLOR
        self.signal_color_name = "green"
        self.is_fake = False
        self.fake_sequence = []
        self.fake_index = 0

        # Player input
        self.p1_pressed = False
        self.p2_pressed = False
        self.p1_time = None
        self.p2_time = None
        self.p1_early = False
        self.p2_early = False

        # Result
        self.round_result_text = ""
        self.round_result_color = COLORS["text_white"]
        self.result_show_timer = 0

        # Stats tracking
        self.p1_times = []
        self.p2_times = []

        # Bot
        self.bot = None
        if mode == "bot":
            self.bot = ReactionBot(self.difficulty)
        self.bot_press_timer = None

        # Visuals
        self.particles = ParticleSystem()
        self.anim_time = 0
        self.screen_flash_alpha = 0
        self.screen_flash_color = (0, 0, 0)
        self.circle_scale = 0
        self.circle_target = 0
        self.pulse_time = 0
        self.shake = 0
        self.shake_intensity = 0

        # Buttons
        self.buttons = []

        # Network
        if mode == "network":
            self.is_p1 = (self.network_role == "host")
        else:
            self.is_p1 = True

    def on_enter(self, **kwargs):
        self._start_intro()

    def on_resize(self, w, h):
        self._build_buttons()

    def _start_intro(self):
        self.state = "intro"
        self.state_timer = 2.5
        self.round_num = 0
        self.score_p1 = 0
        self.score_p2 = 0
        self.p1_times = []
        self.p2_times = []
        if self.bot:
            self.bot = ReactionBot(self.difficulty)
        self._build_buttons()

    def _start_round(self):
        self.round_num += 1
        self.state = "waiting"
        self.wait_duration = random.uniform(1.5, 4.5)
        self.state_timer = 0

        # Decide fake sequence
        self.fake_sequence = []
        num_fakes = random.choices([0, 1, 2, 3], weights=[35, 35, 20, 10])[0]
        current_time = random.uniform(0.3, min(1.5, self.wait_duration * 0.3))

        for _ in range(num_fakes):
            fake_name = random.choice(list(FAKE_COLORS.keys()))
            duration = random.uniform(0.15, 0.4)
            self.fake_sequence.append({
                "time": current_time,
                "color_name": fake_name,
                "color": FAKE_COLORS[fake_name],
                "duration": duration,
                "shown": False,
                "active": False,
            })
            current_time += duration + random.uniform(0.3, 1.0)

        # Make sure fakes don't overlap with real signal time
        self.wait_duration = max(self.wait_duration, current_time + 0.5)

        self.fake_index = 0
        self.is_fake = False
        self.signal_color = REAL_COLOR
        self.signal_color_name = "green"

        # Reset input
        self.p1_pressed = False
        self.p2_pressed = False
        self.p1_time = None
        self.p2_time = None
        self.p1_early = False
        self.p2_early = False

        self.circle_scale = 0
        self.circle_target = 0
        self.bot_press_timer = None

        if self.bot:
            self.bot.new_round()

    def _show_signal(self, color, color_name, is_real):
        """Display a signal (real or fake)."""
        self.signal_color = color
        self.signal_color_name = color_name
        self.is_fake = not is_real
        self.signal_time = time.time()

        if is_real:
            self.state = "real_signal"
        else:
            self.state = "fake_signal"

        self.circle_target = 1.0
        self.circle_scale = 0
        self.screen_flash_alpha = 200
        self.screen_flash_color = color

        # Particle burst
        w, h = self.engine.screen.get_size()
        self.particles.emit(
            x=w // 2, y=h // 2,
            color=color, count=25,
            speed=200, lifetime=0.8, size=4,
            glow=True, friction=0.93,
        )

        # Bot reaction
        if self.bot and not self.bot.pressed:
            press_time = self.bot.on_signal(is_real)
            if press_time is not None:
                self.bot_press_timer = press_time

    def _player_press(self, player):
        """Handle a player pressing their button."""
        if self.state == "waiting":
            # Too early!
            if player == 1 and not self.p1_pressed:
                self.p1_pressed = True
                self.p1_early = True
                self._penalty(player)
            elif player == 2 and not self.p2_pressed:
                self.p2_pressed = True
                self.p2_early = True
                self._penalty(player)
            # Check if both pressed early
            if self.p1_pressed and self.p2_pressed:
                self.round_result_text = get_text("reaction_both_early", self.lang)
                self.round_result_color = COLORS["warning"]
                self._end_round()

        elif self.state == "fake_signal":
            # Fell for fake!
            if player == 1 and not self.p1_pressed:
                self.p1_pressed = True
                self.p1_early = True
                self._penalty(player)
            elif player == 2 and not self.p2_pressed:
                self.p2_pressed = True
                self.p2_early = True
                self._penalty(player)
            if self.p1_pressed and self.p2_pressed:
                self._end_round()

        elif self.state == "real_signal":
            reaction_time = (time.time() - self.signal_time) * 1000  # ms

            if player == 1 and not self.p1_pressed:
                self.p1_pressed = True
                self.p1_time = reaction_time
                self.p1_times.append(reaction_time)
            elif player == 2 and not self.p2_pressed:
                self.p2_pressed = True
                self.p2_time = reaction_time
                self.p2_times.append(reaction_time)

            # Check if round is decided
            if self.mode == "bot":
                if self.p1_pressed:
                    if self.bot_press_timer is not None and not self.p2_pressed:
                        # Bot hasn't pressed yet - player wins
                        self._round_winner(1, self.p1_time)
                    elif self.p2_pressed:
                        # Both pressed - compare times
                        if self.p1_time <= self.p2_time:
                            self._round_winner(1, self.p1_time)
                        else:
                            self._round_winner(2, self.p2_time)
                    else:
                        # Player pressed, bot hasn't decided
                        self._round_winner(1, self.p1_time)
            else:
                if self.p1_pressed and self.p2_pressed:
                    if self.p1_time <= self.p2_time:
                        self._round_winner(1, self.p1_time)
                    else:
                        self._round_winner(2, self.p2_time)
                elif self.p1_pressed and self.mode == "local":
                    self._round_winner(1, self.p1_time)
                elif self.p2_pressed and self.mode == "local":
                    self._round_winner(2, self.p2_time)

    def _penalty(self, player):
        """Apply penalty for early/fake press."""
        if player == 1:
            self.score_p1 = max(0, self.score_p1 - 1)
        else:
            self.score_p2 = max(0, self.score_p2 - 1)

        w, h = self.engine.screen.get_size()
        name = self._get_player_name(player)

        if self.state == "fake_signal":
            color_name = get_text(f"reaction_color_{self.signal_color_name}", self.lang)
            self.round_result_text = get_text("reaction_fake", self.lang, color_name)
        else:
            self.round_result_text = get_text("reaction_too_early", self.lang)

        self.round_result_color = COLORS["danger"]

        # Shake
        self.shake = 0.3
        self.shake_intensity = 10

        self.particles.emit(
            x=w // 2, y=h // 2,
            color=COLORS["danger"], count=20,
            speed=150, lifetime=0.8, size=3,
            glow=True, friction=0.93,
        )

        if self.p1_pressed and self.p2_pressed:
            pass  # Already handled
        elif self.mode == "bot" and player == 1:
            self._end_round()
        elif self.mode == "local":
            if not (self.p1_pressed and self.p2_pressed):
                pass  # Wait for other player or timeout

    def _round_winner(self, player, reaction_ms):
        """Declare round winner."""
        if player == 1:
            self.score_p1 += 1
        else:
            self.score_p2 += 1

        name = self._get_player_name(player)

        if self.mode == "bot":
            if player == 1:
                self.round_result_text = get_text(
                    "reaction_you_wins_round", self.lang, reaction_ms
                )
                self.round_result_color = COLORS["accent"]
            else:
                self.round_result_text = get_text(
                    "reaction_bot_wins_round", self.lang, reaction_ms
                )
                self.round_result_color = COLORS["danger"]
        else:
            key = "reaction_p1_wins_round" if player == 1 else "reaction_p2_wins_round"
            self.round_result_text = get_text(key, self.lang, reaction_ms)
            self.round_result_color = COLORS["x_color"] if player == 1 else COLORS["o_color"]

        w, h = self.engine.screen.get_size()
        color = COLORS["x_color"] if player == 1 else COLORS["o_color"]
        self.particles.emit(
            x=w // 2, y=h // 2,
            color=color, count=30,
            speed=200, lifetime=1.0, size=4,
            glow=True, friction=0.95,
        )

        self._end_round()

    def _end_round(self):
        """End the current round."""
        self.state = "round_result"
        self.result_show_timer = 2.5

        # Check for game over
        if self.score_p1 >= WINNING_SCORE or self.score_p2 >= WINNING_SCORE:
            self.state = "game_over"
            self._on_game_over_reaction()

    def _on_game_over_reaction(self):
        """Handle game over."""
        w, h = self.engine.screen.get_size()

        # Fireworks
        for _ in range(5):
            fx = random.randint(100, w - 100)
            fy = random.randint(100, h - 100)
            color = random.choice([
                COLORS["primary"], COLORS["secondary"],
                COLORS["accent"], COLORS["warning"],
            ])
            self.particles.emit(
                x=fx, y=fy, color=color, count=25,
                speed=200, lifetime=2.0, size=5,
                glow=True, gravity=80, friction=0.96,
            )

        if self.mode == "bot":
            self.record_result("win" if self.score_p1 >= WINNING_SCORE else "loss")
        elif self.mode == "network":
            if self.is_p1:
                self.record_result(
                    "win" if self.score_p1 >= WINNING_SCORE else "loss"
                )
            else:
                self.record_result(
                    "win" if self.score_p2 >= WINNING_SCORE else "loss"
                )

        self._build_buttons()

    def _get_player_name(self, player):
        if player == 1:
            return get_text("pong_player1", self.lang)
        elif self.mode == "bot":
            return get_text("pong_bot", self.lang)
        else:
            return get_text("pong_player2", self.lang)

    def _build_buttons(self):
        w, h = self.engine.screen.get_size()
        cx = w // 2
        btn_y = h - 75

        self.buttons = []
        if self.state == "game_over":
            self.buttons.append(
                Button(cx - 170, btn_y, 160, 50,
                       get_text("play_again", self.lang), font_size=20,
                       hover_color=COLORS["primary_dark"],
                       on_click=self._restart)
            )
        if self.state in ("game_over", "intro"):
            self.buttons.append(
                Button(cx + 10 if self.state == "game_over" else cx - 80,
                       btn_y, 160, 50,
                       get_text("back", self.lang), font_size=20,
                       color=COLORS["bg_light"],
                       hover_color=(80, 30, 30),
                       on_click=self.exit_game)
            )

    def _restart(self):
        self._start_intro()
        if self.mode == "network":
            self.send_network_message({"type": "restart"})

    # === Events ===

    def handle_events(self, events):
        if self.handle_disconnect_events(events):
            return

        for event in events:
            for btn in self.buttons:
                btn.handle_event(event)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.exit_game()
                    return

                if self.state in ("waiting", "fake_signal", "real_signal"):
                    # Player 1: SPACE (or left side keys)
                    if event.key in (pygame.K_SPACE, pygame.K_a, pygame.K_w,
                                     pygame.K_d, pygame.K_s):
                        if self.mode == "local" or self.mode == "bot":
                            self._player_press(1)
                        elif self.mode == "network" and self.is_p1:
                            self._player_press(1)
                            self.send_network_message({
                                "type": "press",
                                "data": {"player": 1,
                                         "time": time.time()},
                            })

                    # Player 2: ENTER, arrows, numpad
                    if event.key in (pygame.K_RETURN, pygame.K_UP,
                                     pygame.K_DOWN, pygame.K_LEFT,
                                     pygame.K_RIGHT, pygame.K_KP_ENTER,
                                     pygame.K_RSHIFT):
                        if self.mode == "local":
                            self._player_press(2)
                        elif self.mode == "network" and not self.is_p1:
                            self._player_press(2)
                            self.send_network_message({
                                "type": "press",
                                "data": {"player": 2,
                                         "time": time.time()},
                            })

    # === Update ===

    def update(self, dt):
        self.anim_time += dt
        self.update_disconnect(dt)
        self.particles.update(dt)

        # Shake decay
        if self.shake > 0:
            self.shake = max(0, self.shake - dt)

        # Flash decay
        if self.screen_flash_alpha > 0:
            self.screen_flash_alpha = max(0, self.screen_flash_alpha - dt * 600)

        # Circle animation
        self.circle_scale += (self.circle_target - self.circle_scale) * min(1, dt * 12)

        # Pulse
        self.pulse_time += dt

        for btn in self.buttons:
            btn.update(dt)

        if self.state == "intro":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self._start_round()

        elif self.state == "waiting":
            self.state_timer += dt

            # Check for fake signals
            for fake in self.fake_sequence:
                if (not fake["shown"] and
                        self.state_timer >= fake["time"]):
                    fake["shown"] = True
                    fake["active"] = True
                    self._show_signal(fake["color"], fake["color_name"], False)
                    return

            # Check fake expiry
            for fake in self.fake_sequence:
                if (fake["active"] and
                        self.state_timer >= fake["time"] + fake["duration"]):
                    fake["active"] = False
                    self.state = "waiting"
                    self.circle_target = 0
                    self.signal_color = REAL_COLOR

            # Time for real signal?
            if self.state_timer >= self.wait_duration:
                self._show_signal(REAL_COLOR, "green", True)

            # Bot early press check
            if self.bot and not self.bot.pressed:
                if self.bot.check_early_press(self.state_timer):
                    self._player_press(2)

        elif self.state == "fake_signal":
            # Check if fake should end
            for fake in self.fake_sequence:
                if (fake["active"] and
                        self.state_timer >= fake["time"] + fake["duration"]):
                    fake["active"] = False
                    self.state = "waiting"
                    self.circle_target = 0

        elif self.state == "real_signal":
            # Bot press
            if self.bot and self.bot_press_timer is not None:
                self.bot_press_timer -= dt
                if self.bot_press_timer <= 0 and not self.p2_pressed:
                    self.bot.mark_pressed()
                    self._player_press(2)

            # Timeout — if nobody pressed in 3 seconds
            elapsed = time.time() - self.signal_time
            if elapsed > 3.0 and not self.p1_pressed and not self.p2_pressed:
                self.round_result_text = get_text("reaction_both_early", self.lang)
                self.round_result_color = COLORS["text_dark"]
                self._end_round()

        elif self.state == "round_result":
            self.result_show_timer -= dt
            if self.result_show_timer <= 0:
                self._start_round()

        elif self.state == "game_over":
            # Fireworks
            self._fw_timer = getattr(self, "_fw_timer", 0) + dt
            if self._fw_timer > 0.5:
                self._fw_timer = 0
                w, h = self.engine.screen.get_size()
                self.particles.emit(
                    x=random.randint(100, w - 100),
                    y=random.randint(100, h - 100),
                    color=random.choice([
                        COLORS["primary"], COLORS["secondary"],
                        COLORS["accent"], COLORS["warning"],
                    ]),
                    count=15, speed=150, lifetime=1.5, size=4,
                    glow=True, gravity=60, friction=0.96,
                )

        # Network
        if self.mode == "network":
            self._update_network()

    def _update_network(self):
        msgs = self.get_network_messages()
        for msg in msgs:
            if isinstance(msg, NetworkMessage):
                if msg.msg_type == "press":
                    player = msg.data.get("player")
                    if player:
                        self._player_press(player)
                elif msg.msg_type == "signal":
                    data = msg.data
                    self._show_signal(
                        tuple(data["color"]),
                        data["color_name"],
                        data["is_real"],
                    )
                elif msg.msg_type == "restart":
                    self._start_intro()

    # === Drawing ===

    def draw(self, screen):
        w, h = screen.get_size()
        cx, cy = w // 2, h // 2

        # Shake offset
        sx = random.randint(-int(self.shake_intensity), int(self.shake_intensity)) \
            if self.shake > 0 else 0
        sy = random.randint(-int(self.shake_intensity), int(self.shake_intensity)) \
            if self.shake > 0 else 0

        # Screen flash
        if self.screen_flash_alpha > 5:
            flash = pygame.Surface((w, h), pygame.SRCALPHA)
            flash.fill((*self.screen_flash_color, int(self.screen_flash_alpha * 0.3)))
            screen.blit(flash, (0, 0))

        # Score
        self._draw_score(screen)

        # Central area
        if self.state == "intro":
            self._draw_intro(screen)
        elif self.state in ("waiting",):
            self._draw_waiting(screen, cx + sx, cy + sy)
        elif self.state in ("fake_signal", "real_signal"):
            self._draw_signal(screen, cx + sx, cy + sy)
        elif self.state == "round_result":
            self._draw_result(screen, cx, cy)
        elif self.state == "game_over":
            self._draw_game_over(screen, cx, cy)

        # Controls hint (always visible at bottom in local/bot)
        if self.mode != "network" and self.state not in ("game_over",):
            self._draw_controls(screen)

        self.particles.draw(screen)

        for btn in self.buttons:
            btn.draw(screen)

        self.draw_disconnect_overlay(screen)

    def _draw_score(self, screen):
        w = screen.get_width()
        font = get_font(42, bold=True)

        # P1 score
        p1_surf = font.render(str(self.score_p1), True, COLORS["x_color"])
        screen.blit(p1_surf, (w // 2 - p1_surf.get_width() - 30, 15))

        # Separator
        sep_font = get_font(30)
        sep = sep_font.render(":", True, COLORS["text_dark"])
        screen.blit(sep, (w // 2 - sep.get_width() // 2, 22))

        # P2 score
        p2_surf = font.render(str(self.score_p2), True, COLORS["o_color"])
        screen.blit(p2_surf, (w // 2 + 30, 15))

        # First to N
        info_font = get_font(14)
        info = info_font.render(
            get_text("reaction_first_to", self.lang, WINNING_SCORE),
            True, COLORS["text_dark"]
        )
        screen.blit(info, (w // 2 - info.get_width() // 2, 65))

    def _draw_intro(self, screen):
        w, h = screen.get_size()
        cx, cy = w // 2, h // 2

        draw_title(screen, get_text("reaction", self.lang),
                   y=cy - 80, font_size=48)

        font = get_font(22)
        text = get_text("reaction_get_ready", self.lang)
        pulse = 0.5 + 0.5 * math.sin(self.anim_time * 3)
        alpha = int(150 + 105 * pulse)
        surf = font.render(text, True, (*COLORS["warning"][:3],))
        screen.blit(surf, (cx - surf.get_width() // 2, cy + 20))

    def _draw_waiting(self, screen, cx, cy):
        # Pulsing circle outline
        radius = int(min(screen.get_width(), screen.get_height()) * SIGNAL_SIZE_RATIO / 2)
        pulse = 0.8 + 0.2 * math.sin(self.pulse_time * 2)
        r = int(radius * pulse)

        # Dark circle
        pygame.draw.circle(screen, COLORS["bg_light"], (cx, cy), r, 4)

        # Text
        font = get_font(24)
        text = get_text("reaction_wait", self.lang)
        dots = "." * (int(self.anim_time * 2) % 4)
        surf = font.render(text, True, COLORS["text_gray"])
        screen.blit(surf, (cx - surf.get_width() // 2, cy + r + 20))

        # Round number
        round_font = get_font(16)
        round_text = get_text("reaction_round", self.lang, self.round_num)
        round_surf = round_font.render(round_text, True, COLORS["text_dark"])
        screen.blit(round_surf, (cx - round_surf.get_width() // 2, cy - r - 35))

    def _draw_signal(self, screen, cx, cy):
        radius = int(min(screen.get_width(), screen.get_height()) * SIGNAL_SIZE_RATIO / 2)
        r = int(radius * self.circle_scale)

        if r < 3:
            return

        # Glow
        glow_r = int(r * 1.5)
        glow_surf = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (*self.signal_color, 40),
                           (glow_r, glow_r), glow_r)
        screen.blit(glow_surf, (cx - glow_r, cy - glow_r))

        # Main circle
        pygame.draw.circle(screen, self.signal_color, (cx, cy), r)

        # Bright center
        inner_r = max(2, r // 2)
        bright = tuple(min(255, c + 80) for c in self.signal_color)
        pygame.draw.circle(screen, bright, (cx, cy), inner_r)

        # Label
        if self.state == "real_signal":
            font = get_font(36, bold=True)
            text = get_text("reaction_now", self.lang)
            surf = font.render(text, True, (255, 255, 255))
            screen.blit(surf, (cx - surf.get_width() // 2,
                               cy + r + 15))

    def _draw_result(self, screen, cx, cy):
        font = get_font(28, bold=True)
        surf = font.render(self.round_result_text, True, self.round_result_color)
        screen.blit(surf, (cx - surf.get_width() // 2, cy - 30))

        # Next round timer
        if self.result_show_timer > 0:
            timer_font = get_font(16)
            timer_text = get_text("reaction_next_round", self.lang,
                                  self.result_show_timer)
            timer_surf = timer_font.render(timer_text, True, COLORS["text_dark"])
            screen.blit(timer_surf,
                        (cx - timer_surf.get_width() // 2, cy + 20))

    def _draw_game_over(self, screen, cx, cy):
        # Overlay
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((*COLORS["bg_dark"], 160))
        screen.blit(overlay, (0, 0))

        # Winner
        if self.score_p1 >= WINNING_SCORE:
            winner_name = self._get_player_name(1)
            color = COLORS["x_color"]
        else:
            winner_name = self._get_player_name(2)
            color = COLORS["o_color"]

        pulse = 1.0 + 0.05 * math.sin(self.anim_time * 3)
        font = get_font(int(44 * pulse), bold=True)
        win_text = get_text("reaction_wins", self.lang, winner_name)
        surf = font.render(win_text, True, color)
        screen.blit(surf, (cx - surf.get_width() // 2, cy - 80))

        # Score
        score_font = get_font(28)
        score_text = f"{self.score_p1}  :  {self.score_p2}"
        score_surf = score_font.render(score_text, True, COLORS["text_gray"])
        screen.blit(score_surf, (cx - score_surf.get_width() // 2, cy - 20))

        # Average times
        stats_font = get_font(18)
        y = cy + 30

        if self.p1_times:
            avg1 = sum(self.p1_times) / len(self.p1_times)
            best1 = min(self.p1_times)
            t1 = stats_font.render(
                f"{self._get_player_name(1)}: avg {avg1:.0f}ms, best {best1:.0f}ms",
                True, COLORS["x_color"]
            )
            screen.blit(t1, (cx - t1.get_width() // 2, y))
            y += 25

        if self.p2_times:
            avg2 = sum(self.p2_times) / len(self.p2_times)
            best2 = min(self.p2_times)
            t2 = stats_font.render(
                f"{self._get_player_name(2)}: avg {avg2:.0f}ms, best {best2:.0f}ms",
                True, COLORS["o_color"]
            )
            screen.blit(t2, (cx - t2.get_width() // 2, y))

    def _draw_controls(self, screen):
        w, h = screen.get_size()
        font = get_font(15)

        # P1
        p1_text = get_text("reaction_p1_controls", self.lang)
        p1_surf = font.render(p1_text, True, COLORS["x_color"])
        screen.blit(p1_surf, (20, h - 30))

        # P2
        if self.mode == "bot":
            p2_text = f"{get_text('pong_bot', self.lang)} ({self.difficulty})"
        else:
            p2_text = get_text("reaction_p2_controls", self.lang)
        p2_surf = font.render(p2_text, True, COLORS["o_color"])
        screen.blit(p2_surf, (w - p2_surf.get_width() - 20, h - 30))
