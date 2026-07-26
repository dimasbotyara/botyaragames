"""Particle system with glow effects."""

import pygame
import random
import math


class Particle:
    """Single particle."""

    __slots__ = [
        "x", "y", "vx", "vy", "color", "size", "original_size",
        "lifetime", "max_lifetime", "fade", "glow", "alpha",
        "gravity", "friction",
    ]

    def __init__(self, x, y, vx, vy, color, size, lifetime,
                 fade=True, glow=False, gravity=0, friction=0.98):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.size = size
        self.original_size = size
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.fade = fade
        self.glow = glow
        self.alpha = 255
        self.gravity = gravity
        self.friction = friction


class ParticleSystem:
    """Manages and renders particles with effects."""

    def __init__(self):
        self.particles = []
        self._glow_cache = {}

    def emit(self, x, y, color=(255, 255, 255), count=10,
             speed=100, lifetime=1.0, size=3, fade=True,
             glow=False, direction="radial", gravity=0,
             friction=0.98, spread=360, angle=0, size_range=None):
        """Emit particles."""
        for _ in range(count):
            if direction == "radial":
                a = random.uniform(0, 2 * math.pi)
                spd = random.uniform(speed * 0.3, speed)
                vx = math.cos(a) * spd
                vy = math.sin(a) * spd
            elif direction == "up":
                a = random.uniform(-math.pi - 0.5, -math.pi + 0.5)
                spd = random.uniform(speed * 0.5, speed)
                vx = math.cos(a) * spd
                vy = -spd
            elif direction == "float":
                vx = random.uniform(-speed * 0.3, speed * 0.3)
                vy = random.uniform(-speed * 0.2, speed * 0.2)
            elif direction == "directional":
                a = math.radians(angle) + random.uniform(
                    -math.radians(spread / 2),
                    math.radians(spread / 2)
                )
                spd = random.uniform(speed * 0.5, speed)
                vx = math.cos(a) * spd
                vy = math.sin(a) * spd
            else:
                vx = random.uniform(-speed, speed)
                vy = random.uniform(-speed, speed)

            if size_range:
                s = random.uniform(size_range[0], size_range[1])
            else:
                s = size * random.uniform(0.5, 1.5)

            lt = lifetime * random.uniform(0.7, 1.3)

            # Slight color variation
            r = max(0, min(255, color[0] + random.randint(-15, 15)))
            g = max(0, min(255, color[1] + random.randint(-15, 15)))
            b = max(0, min(255, color[2] + random.randint(-15, 15)))

            p = Particle(
                x=x + random.uniform(-3, 3),
                y=y + random.uniform(-3, 3),
                vx=vx, vy=vy,
                color=(r, g, b),
                size=s,
                lifetime=lt,
                fade=fade,
                glow=glow,
                gravity=gravity,
                friction=friction,
            )
            self.particles.append(p)

    def update(self, dt):
        """Update all particles."""
        alive = []
        for p in self.particles:
            p.lifetime -= dt
            if p.lifetime <= 0:
                continue

            p.vx *= p.friction
            p.vy *= p.friction
            p.vy += p.gravity * dt

            p.x += p.vx * dt
            p.y += p.vy * dt

            if p.fade:
                ratio = p.lifetime / p.max_lifetime
                p.alpha = int(255 * ratio)
                p.size = p.original_size * (0.3 + 0.7 * ratio)

            alive.append(p)
        self.particles = alive

    def draw(self, screen):
        """Draw all particles."""
        for p in self.particles:
            if p.alpha <= 0 or p.size < 0.5:
                continue

            if p.glow and p.size > 1:
                self._draw_glow(screen, p)
            else:
                self._draw_simple(screen, p)

    def _draw_simple(self, screen, p):
        """Draw a simple circle particle."""
        color = (*p.color, min(255, p.alpha))
        size = max(1, int(p.size))
        surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (size, size), size)
        screen.blit(surf, (int(p.x - size), int(p.y - size)))

    def _draw_glow(self, screen, p):
        """Draw particle with glow effect."""
        size = max(2, int(p.size))
        glow_size = size * 4

        surf = pygame.Surface((glow_size * 2, glow_size * 2), pygame.SRCALPHA)

        # Outer glow
        alpha_outer = max(0, min(255, int(p.alpha * 0.15)))
        color_outer = (*p.color, alpha_outer)
        pygame.draw.circle(surf, color_outer, (glow_size, glow_size), glow_size)

        # Middle glow
        alpha_mid = max(0, min(255, int(p.alpha * 0.3)))
        color_mid = (*p.color, alpha_mid)
        pygame.draw.circle(surf, color_mid, (glow_size, glow_size), glow_size // 2)

        # Core
        alpha_core = max(0, min(255, p.alpha))
        color_core = (
            min(255, p.color[0] + 60),
            min(255, p.color[1] + 60),
            min(255, p.color[2] + 60),
            alpha_core,
        )
        pygame.draw.circle(surf, color_core, (glow_size, glow_size), size)

        screen.blit(surf, (int(p.x - glow_size), int(p.y - glow_size)),
                     special_flags=pygame.BLEND_ALPHA_SDL2)

    def clear(self):
        """Remove all particles."""
        self.particles.clear()

    def __len__(self):
        return len(self.particles)