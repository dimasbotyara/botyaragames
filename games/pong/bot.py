"""Pong AI with fatigue/dopamine system.

Bot starts focused and sharp, then gradually loses concentration.
Reaction time increases, prediction accuracy decreases.
Like a real human losing focus over time.
"""

import random
import math


class PongBot:
    """AI paddle controller with realistic fatigue."""

    # Difficulty presets: (base_speed, reaction_time, prediction_accuracy,
    #                      fatigue_rate, recovery_on_score, jitter)
    PRESETS = {
        "easy": {
            "base_speed": 0.55,        # % of max paddle speed
            "base_reaction": 0.35,     # seconds delay before reacting
            "base_accuracy": 0.50,     # how well it predicts ball landing
            "fatigue_rate": 0.03,      # concentration lost per second
            "recovery_on_score": 0.4,  # concentration recovered on point scored
            "jitter": 25,              # random offset in pixels
            "initial_focus": 0.8,      # starting concentration (0-1)
            "min_focus": 0.15,         # lowest concentration
            "focus_drop_time": 15,     # seconds before serious drop
        },
        "medium": {
            "base_speed": 0.72,
            "base_reaction": 0.20,
            "base_accuracy": 0.70,
            "fatigue_rate": 0.018,
            "recovery_on_score": 0.3,
            "jitter": 15,
            "initial_focus": 0.9,
            "min_focus": 0.30,
            "focus_drop_time": 25,
        },
        "hard": {
            "base_speed": 0.88,
            "base_reaction": 0.10,
            "base_accuracy": 0.88,
            "fatigue_rate": 0.012,
            "recovery_on_score": 0.2,
            "jitter": 8,
            "initial_focus": 0.95,
            "min_focus": 0.45,
            "focus_drop_time": 35,
        },
    }

    def __init__(self, difficulty="medium"):
        preset = self.PRESETS.get(difficulty, self.PRESETS["medium"])

        self.base_speed = preset["base_speed"]
        self.base_reaction = preset["base_reaction"]
        self.base_accuracy = preset["base_accuracy"]
        self.fatigue_rate = preset["fatigue_rate"]
        self.recovery_on_score = preset["recovery_on_score"]
        self.jitter = preset["jitter"]
        self.initial_focus = preset["initial_focus"]
        self.min_focus = preset["min_focus"]
        self.focus_drop_time = preset["focus_drop_time"]

        # Current state
        self.focus = self.initial_focus  # 0 = exhausted, 1 = laser focused
        self.round_time = 0.0           # time since round started
        self.reaction_timer = 0.0       # current reaction delay
        self.target_y = 0.0            # where bot wants to go
        self.last_target_update = 0.0
        self.is_reacting = False       # waiting to react to ball direction change

        # Micro-hesitations (random pauses)
        self.hesitation_timer = 0.0
        self.next_hesitation = random.uniform(3, 8)

        # "Dopamine" burst — after scoring, bot gets briefly sharper
        self.dopamine_timer = 0.0
        self.dopamine_boost = 0.0

    def reset_round(self):
        """Reset for new round (ball respawn)."""
        self.round_time = 0.0
        self.reaction_timer = 0.0
        self.is_reacting = False
        self.hesitation_timer = 0.0
        self.next_hesitation = random.uniform(3, 8)
        # Small focus recovery at round start (like a breather)
        self.focus = min(1.0, self.focus + 0.05)

    def on_score(self, bot_scored):
        """Called when someone scores."""
        if bot_scored:
            # Dopamine hit! Bot gets focused briefly
            self.dopamine_timer = 3.0
            self.dopamine_boost = 0.2
            self.focus = min(1.0, self.focus + self.recovery_on_score)
        else:
            # Got scored on — slight tilt/frustration, OR refocus
            if random.random() < 0.4:
                # Tilt
                self.focus = max(self.min_focus, self.focus - 0.1)
            else:
                # Refocus
                self.focus = min(1.0, self.focus + self.recovery_on_score * 0.5)

    def get_effective_stats(self):
        """Get current effective stats with fatigue applied."""
        # Fatigue curve — starts flat, then drops
        if self.round_time < self.focus_drop_time * 0.3:
            # "In the zone" — minimal fatigue
            time_factor = 1.0
        elif self.round_time < self.focus_drop_time:
            # Gradual decline
            t = (self.round_time - self.focus_drop_time * 0.3) / (self.focus_drop_time * 0.7)
            time_factor = 1.0 - t * 0.4
        else:
            # Deep fatigue — getting sloppy
            overtime = self.round_time - self.focus_drop_time
            time_factor = 0.6 - min(0.35, overtime * 0.01)

        effective_focus = self.focus * time_factor

        # Dopamine boost
        if self.dopamine_timer > 0:
            effective_focus = min(1.0, effective_focus + self.dopamine_boost)

        effective_focus = max(self.min_focus, min(1.0, effective_focus))

        speed = self.base_speed * (0.5 + 0.5 * effective_focus)
        reaction = self.base_reaction * (2.0 - effective_focus)
        accuracy = self.base_accuracy * effective_focus
        jitter = self.jitter * (2.0 - effective_focus)

        return speed, reaction, accuracy, jitter, effective_focus

    def update(self, dt, ball_x, ball_y, ball_vx, ball_vy,
               paddle_y, paddle_h, field_h, field_w, paddle_x):
        """Update bot logic. Returns desired paddle movement (-1, 0, or 1 with strength)."""
        self.round_time += dt

        # Update fatigue
        self.focus = max(self.min_focus,
                         self.focus - self.fatigue_rate * dt)

        # Update dopamine
        if self.dopamine_timer > 0:
            self.dopamine_timer -= dt
            if self.dopamine_timer <= 0:
                self.dopamine_boost = 0

        speed, reaction, accuracy, jitter, effective_focus = self.get_effective_stats()

        # Hesitation system — sometimes bot just... spaces out
        self.hesitation_timer += dt
        if self.hesitation_timer >= self.next_hesitation:
            self.hesitation_timer = 0
            self.next_hesitation = random.uniform(
                3 / max(0.1, effective_focus),
                8 / max(0.1, effective_focus)
            )
            # Brief pause
            if random.random() < (1.0 - effective_focus) * 0.5:
                return 0  # Space out for this frame

        # Determine target Y
        if ball_vx > 0:
            # Ball coming towards bot (right side)
            self._update_target(ball_x, ball_y, ball_vx, ball_vy,
                                field_h, field_w, paddle_x, accuracy, jitter)
        else:
            # Ball going away — drift towards center
            center = field_h / 2
            self.target_y = center + random.uniform(-jitter * 2, jitter * 2)

        # Reaction delay
        if self.is_reacting:
            self.reaction_timer -= dt
            if self.reaction_timer > 0:
                return 0  # Still reacting, don't move
            self.is_reacting = False

        # Move towards target
        paddle_center = paddle_y + paddle_h / 2
        diff = self.target_y - paddle_center
        dead_zone = paddle_h * 0.15 * (2.0 - effective_focus)

        if abs(diff) < dead_zone:
            return 0

        # Speed factor — how fast paddle moves (0 to 1)
        move_strength = min(1.0, abs(diff) / (paddle_h * 0.8)) * speed

        if diff > 0:
            return move_strength
        else:
            return -move_strength

    def _update_target(self, ball_x, ball_y, ball_vx, ball_vy,
                       field_h, field_w, paddle_x, accuracy, jitter):
        """Predict where ball will arrive and set target."""
        if ball_vx <= 0:
            return

        # Time to reach paddle
        dist = paddle_x - ball_x
        if dist <= 0:
            self.target_y = ball_y
            return

        time_to_arrive = dist / ball_vx

        # Predict Y with bounces
        predicted_y = ball_y + ball_vy * time_to_arrive

        # Simulate bounces
        bounces = 0
        while predicted_y < 0 or predicted_y > field_h:
            if predicted_y < 0:
                predicted_y = -predicted_y
            elif predicted_y > field_h:
                predicted_y = 2 * field_h - predicted_y
            bounces += 1
            if bounces > 10:
                break

        # Apply accuracy — less accurate = more random offset
        error = (1.0 - accuracy) * field_h * 0.3
        predicted_y += random.uniform(-error, error)

        # Apply jitter
        predicted_y += random.uniform(-jitter, jitter)

        self.target_y = max(0, min(field_h, predicted_y))

    def on_ball_direction_change(self):
        """Called when ball changes horizontal direction."""
        _, reaction, _, _, _ = self.get_effective_stats()
        self.is_reacting = True
        self.reaction_timer = reaction * random.uniform(0.7, 1.3)