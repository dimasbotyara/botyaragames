"""Reaction Game AI — simulates human-like reaction times with variance."""

import random
import math


class ReactionBot:
    """Bot that simulates human reaction with personality."""

    PRESETS = {
        "easy": {
            "base_reaction_ms": 450,
            "variance_ms": 120,
            "fake_fall_chance": 0.35,
            "early_press_chance": 0.08,
            "fatigue_per_round": 8,
            "focus_recovery": 0.3,
            "min_reaction_ms": 280,
        },
        "medium": {
            "base_reaction_ms": 320,
            "variance_ms": 80,
            "fake_fall_chance": 0.12,
            "early_press_chance": 0.03,
            "fatigue_per_round": 5,
            "focus_recovery": 0.2,
            "min_reaction_ms": 200,
        },
        "hard": {
            "base_reaction_ms": 230,
            "variance_ms": 50,
            "fake_fall_chance": 0.04,
            "early_press_chance": 0.01,
            "fatigue_per_round": 3,
            "focus_recovery": 0.15,
            "min_reaction_ms": 160,
        },
    }

    def __init__(self, difficulty="medium"):
        preset = self.PRESETS.get(difficulty, self.PRESETS["medium"])
        self.base_reaction = preset["base_reaction_ms"]
        self.variance = preset["variance_ms"]
        self.fake_fall_chance = preset["fake_fall_chance"]
        self.early_press_chance = preset["early_press_chance"]
        self.fatigue_per_round = preset["fatigue_per_round"]
        self.focus_recovery = preset["focus_recovery"]
        self.min_reaction = preset["min_reaction_ms"]

        self.rounds_played = 0
        self.fatigue = 0
        self.decided = False
        self.will_press_at = None
        self.will_fall_for_fake = False
        self.pressed = False

    def new_round(self):
        """Prepare for a new round."""
        self.rounds_played += 1
        self.fatigue = min(80, self.fatigue + self.fatigue_per_round)

        # Random recovery
        if random.random() < self.focus_recovery:
            self.fatigue = max(0, self.fatigue - 20)

        self.decided = False
        self.will_press_at = None
        self.will_fall_for_fake = False
        self.pressed = False

    def on_signal(self, is_real):
        """Called when a signal (real or fake) appears.

        Returns the time (in seconds) when bot will press, or None.
        """
        if self.pressed:
            return None

        self.decided = True

        if is_real:
            # Calculate reaction time
            fatigue_penalty = self.fatigue * 0.8
            reaction_ms = self.base_reaction + fatigue_penalty
            reaction_ms += random.gauss(0, self.variance)
            reaction_ms = max(self.min_reaction, reaction_ms)

            # Sometimes bot is just cracked
            if random.random() < 0.05:
                reaction_ms *= 0.75

            self.will_press_at = reaction_ms / 1000.0
            return self.will_press_at

        else:
            # Fake signal — might fall for it
            if random.random() < self.fake_fall_chance + self.fatigue * 0.002:
                self.will_fall_for_fake = True
                reaction_ms = self.base_reaction * 0.8 + random.gauss(0, self.variance * 0.5)
                self.will_press_at = max(0.1, reaction_ms / 1000.0)
                return self.will_press_at

            return None

    def check_early_press(self, wait_elapsed):
        """Check if bot presses too early during wait phase."""
        if self.pressed:
            return False

        # Chance increases the longer we wait
        time_factor = min(1, wait_elapsed / 5.0)
        chance = self.early_press_chance * time_factor * (1 + self.fatigue * 0.01)

        if random.random() < chance * 0.016:
            self.pressed = True
            return True
        return False

    def mark_pressed(self):
        self.pressed = True
