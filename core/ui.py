"""UI components: buttons, scrollbar, text input, etc."""

import pygame
import math
from settings import COLORS


def get_font(size, bold=False):
    """Get a system font."""
    names = "Arial,Helvetica,Segoe UI,DejaVu Sans,Liberation Sans"
    return pygame.font.SysFont(names, size, bold=bold)


class Button:
    """Animated button with hover/click effects."""

    def __init__(self, x, y, w, h, text, font_size=24,
                 color=None, hover_color=None, text_color=None,
                 border_radius=12, on_click=None, icon=None):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.font = get_font(font_size, bold=True)
        self.color = color or COLORS["bg_light"]
        self.hover_color = hover_color or COLORS["primary_dark"]
        self.text_color = text_color or COLORS["text_white"]
        self.border_radius = border_radius
        self.on_click = on_click
        self.icon = icon

        self.hovered = False
        self.pressed = False
        self.hover_anim = 0.0  # 0 to 1
        self.press_anim = 0.0
        self.enabled = True
        self.visible = True
        self.glow_time = 0

    def set_pos(self, x, y):
        self.rect.x = x
        self.rect.y = y

    def set_center(self, cx, cy):
        self.rect.center = (cx, cy)

    def handle_event(self, event):
        if not self.enabled or not self.visible:
            return False
        if event.type == pygame.MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.pressed = True
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.pressed and self.rect.collidepoint(event.pos):
                self.pressed = False
                if self.on_click:
                    self.on_click()
                return True
            self.pressed = False
        return False

    def update(self, dt):
        if not self.visible:
            return
        self.glow_time += dt
        target = 1.0 if self.hovered else 0.0
        self.hover_anim += (target - self.hover_anim) * min(1, dt * 10)
        target_p = 1.0 if self.pressed else 0.0
        self.press_anim += (target_p - self.press_anim) * min(1, dt * 15)

    def draw(self, screen):
        if not self.visible:
            return

        rect = self.rect.copy()

        # Press shrink effect
        if self.press_anim > 0.01:
            shrink = int(3 * self.press_anim)
            rect = rect.inflate(-shrink * 2, -shrink * 2)

        # Interpolate color
        r = int(self.color[0] + (self.hover_color[0] - self.color[0]) * self.hover_anim)
        g = int(self.color[1] + (self.hover_color[1] - self.color[1]) * self.hover_anim)
        b = int(self.color[2] + (self.hover_color[2] - self.color[2]) * self.hover_anim)
        bg_color = (r, g, b)

        # Shadow
        shadow_rect = rect.copy()
        shadow_rect.y += 3
        shadow_surf = pygame.Surface(shadow_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (*COLORS["shadow"], 80),
                         (0, 0, *shadow_rect.size), border_radius=self.border_radius)
        screen.blit(shadow_surf, shadow_rect.topleft)

        # Glow on hover
        if self.hover_anim > 0.1:
            glow_rect = rect.inflate(8, 8)
            glow_surf = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            alpha = int(40 * self.hover_anim)
            pygame.draw.rect(glow_surf, (*COLORS["primary"], alpha),
                             (0, 0, *glow_rect.size), border_radius=self.border_radius + 4)
            screen.blit(glow_surf, glow_rect.topleft)

        # Main body
        pygame.draw.rect(screen, bg_color, rect, border_radius=self.border_radius)

        # Border
        border_alpha = int(80 + 100 * self.hover_anim)
        border_color = COLORS["border_light"] if self.hover_anim > 0.5 else COLORS["border"]
        pygame.draw.rect(screen, border_color, rect, 2,
                         border_radius=self.border_radius)

        # Text
        if not self.enabled:
            tc = COLORS["text_dark"]
        else:
            tc = self.text_color
        text_surf = self.font.render(self.text, True, tc)
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)


class ScrollableList:
    """Scrollable list of items with smooth scrolling."""

    def __init__(self, x, y, w, h, item_height=70, padding=8):
        self.rect = pygame.Rect(x, y, w, h)
        self.item_height = item_height
        self.padding = padding
        self.items = []  # List of dicts: {text, desc, on_click, icon, ...}
        self.scroll_y = 0
        self.scroll_target = 0
        self.max_scroll = 0
        self.scrollbar_dragging = False
        self.drag_offset = 0
        self.hover_index = -1
        self.hover_anim = {}

    def set_items(self, items):
        """Set items. Each item: {text, desc, on_click}"""
        self.items = items
        total = len(items) * (self.item_height + self.padding)
        self.max_scroll = max(0, total - self.rect.height + self.padding)
        self.scroll_y = 0
        self.scroll_target = 0
        self.hover_anim = {}

    def handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll_target -= event.y * 40
                self.scroll_target = max(0, min(self.max_scroll, self.scroll_target))
                return True

        if event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                local_y = event.pos[1] - self.rect.y + self.scroll_y
                idx = int(local_y / (self.item_height + self.padding))
                if 0 <= idx < len(self.items):
                    self.hover_index = idx
                else:
                    self.hover_index = -1
            else:
                self.hover_index = -1

            if self.scrollbar_dragging:
                self._drag_scrollbar(event.pos[1])

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                # Check scrollbar
                sb = self._scrollbar_rect()
                if sb and sb.collidepoint(event.pos):
                    self.scrollbar_dragging = True
                    self.drag_offset = event.pos[1] - sb.y
                    return True
                # Check item click
                if self.hover_index >= 0 and self.hover_index < len(self.items):
                    item = self.items[self.hover_index]
                    if item.get("on_click"):
                        item["on_click"]()
                        return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.scrollbar_dragging = False

        return False

    def _drag_scrollbar(self, mouse_y):
        if self.max_scroll <= 0:
            return
        track_h = self.rect.height - 20
        bar_h = max(30, track_h * (self.rect.height / (self.max_scroll + self.rect.height)))
        track_start = self.rect.y + 10
        drag_range = track_h - bar_h
        if drag_range <= 0:
            return
        relative = (mouse_y - self.drag_offset - track_start) / drag_range
        relative = max(0, min(1, relative))
        self.scroll_target = relative * self.max_scroll
        self.scroll_y = self.scroll_target

    def _scrollbar_rect(self):
        if self.max_scroll <= 0:
            return None
        track_h = self.rect.height - 20
        bar_h = max(30, track_h * (self.rect.height / (self.max_scroll + self.rect.height)))
        if self.max_scroll > 0:
            bar_y = (self.scroll_y / self.max_scroll) * (track_h - bar_h)
        else:
            bar_y = 0
        return pygame.Rect(
            self.rect.right - 12,
            self.rect.y + 10 + bar_y,
            8,
            bar_h,
        )

    def update(self, dt):
        # Smooth scroll
        self.scroll_y += (self.scroll_target - self.scroll_y) * min(1, dt * 12)

        # Hover animations
        for i in range(len(self.items)):
            target = 1.0 if i == self.hover_index else 0.0
            current = self.hover_anim.get(i, 0.0)
            self.hover_anim[i] = current + (target - current) * min(1, dt * 10)

    def draw(self, screen):
        # Clip area
        clip = screen.get_clip()
        screen.set_clip(self.rect)

        for i, item in enumerate(self.items):
            iy = self.rect.y + i * (self.item_height + self.padding) - self.scroll_y
            if iy + self.item_height < self.rect.y or iy > self.rect.bottom:
                continue

            item_rect = pygame.Rect(self.rect.x + 5, iy,
                                     self.rect.width - 25, self.item_height)

            anim = self.hover_anim.get(i, 0)

            # Background
            r = int(COLORS["bg_medium"][0] + (COLORS["bg_light"][0] - COLORS["bg_medium"][0]) * anim)
            g = int(COLORS["bg_medium"][1] + (COLORS["bg_light"][1] - COLORS["bg_medium"][1]) * anim)
            b = int(COLORS["bg_medium"][2] + (COLORS["bg_light"][2] - COLORS["bg_medium"][2]) * anim)
            pygame.draw.rect(screen, (r, g, b), item_rect, border_radius=10)

            # Glow on hover
            if anim > 0.1:
                glow = item_rect.inflate(4, 4)
                glow_surf = pygame.Surface(glow.size, pygame.SRCALPHA)
                pygame.draw.rect(glow_surf, (*COLORS["primary"], int(30 * anim)),
                                 (0, 0, *glow.size), border_radius=12)
                screen.blit(glow_surf, glow.topleft)

            # Border
            border_color = (
                int(COLORS["border"][0] + (COLORS["primary"][0] - COLORS["border"][0]) * anim),
                int(COLORS["border"][1] + (COLORS["primary"][1] - COLORS["border"][1]) * anim),
                int(COLORS["border"][2] + (COLORS["primary"][2] - COLORS["border"][2]) * anim),
            )
            pygame.draw.rect(screen, border_color, item_rect, 2, border_radius=10)

            # Text
            font = get_font(22, bold=True)
            text_surf = font.render(item.get("text", ""), True, COLORS["text_white"])
            screen.blit(text_surf, (item_rect.x + 15, item_rect.y + 10))

            # Description
            if item.get("desc"):
                desc_font = get_font(16)
                desc_surf = desc_font.render(item["desc"], True, COLORS["text_gray"])
                screen.blit(desc_surf, (item_rect.x + 15, item_rect.y + 38))

            # Modes indicator
            if item.get("modes"):
                mode_font = get_font(13)
                modes_text = " | ".join(item["modes"])
                mode_surf = mode_font.render(modes_text, True, COLORS["primary"])
                screen.blit(mode_surf, (item_rect.right - mode_surf.get_width() - 15,
                                         item_rect.y + item_rect.height // 2 - mode_surf.get_height() // 2))

        screen.set_clip(clip)

        # Scrollbar
        sb = self._scrollbar_rect()
        if sb:
            # Track
            track_rect = pygame.Rect(self.rect.right - 14, self.rect.y + 8,
                                     12, self.rect.height - 16)
            pygame.draw.rect(screen, COLORS["bg_dark"], track_rect, border_radius=6)
            # Bar
            pygame.draw.rect(screen, COLORS["border_light"], sb, border_radius=4)


class TextInput:
    """Text input field."""

    def __init__(self, x, y, w, h=40, placeholder="", font_size=20,
                 max_length=50, text=""):
        self.rect = pygame.Rect(x, y, w, h)
        self.font = get_font(font_size)
        self.placeholder = placeholder
        self.text = text
        self.max_length = max_length
        self.active = False
        self.cursor_visible = True
        self.cursor_timer = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.active = self.rect.collidepoint(event.pos)
            self.cursor_visible = True
            self.cursor_timer = 0

        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key == pygame.K_RETURN:
                return "enter"
            elif event.key == pygame.K_TAB:
                return "tab"
            elif event.unicode and len(self.text) < self.max_length:
                if event.unicode.isprintable():
                    self.text += event.unicode
            return "input"
        return None

    def update(self, dt):
        self.cursor_timer += dt
        if self.cursor_timer >= 0.5:
            self.cursor_timer = 0
            self.cursor_visible = not self.cursor_visible

    def draw(self, screen):
        # Background
        bg = COLORS["bg_dark"] if self.active else COLORS["bg_medium"]
        pygame.draw.rect(screen, bg, self.rect, border_radius=8)

        # Border
        bc = COLORS["primary"] if self.active else COLORS["border"]
        pygame.draw.rect(screen, bc, self.rect, 2, border_radius=8)

        # Text or placeholder
        if self.text:
            text_surf = self.font.render(self.text, True, COLORS["text_white"])
        else:
            text_surf = self.font.render(self.placeholder, True, COLORS["text_dark"])

        # Clip text
        text_x = self.rect.x + 10
        text_y = self.rect.y + (self.rect.height - text_surf.get_height()) // 2
        screen.blit(text_surf, (text_x, text_y))

        # Cursor
        if self.active and self.cursor_visible:
            cursor_x = text_x + self.font.size(self.text)[0] + 2
            pygame.draw.line(screen, COLORS["primary"],
                             (cursor_x, self.rect.y + 8),
                             (cursor_x, self.rect.bottom - 8), 2)


class Toggle:
    """Toggle switch."""

    def __init__(self, x, y, initial=False, on_change=None):
        self.x = x
        self.y = y
        self.w = 50
        self.h = 26
        self.value = initial
        self.on_change = on_change
        self.anim = 1.0 if initial else 0.0
        self.rect = pygame.Rect(x, y, self.w, self.h)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.value = not self.value
                if self.on_change:
                    self.on_change(self.value)
                return True
        return False

    def update(self, dt):
        target = 1.0 if self.value else 0.0
        self.anim += (target - self.anim) * min(1, dt * 12)

    def draw(self, screen):
        # Track
        r = int(COLORS["bg_dark"][0] + (COLORS["primary_dark"][0] - COLORS["bg_dark"][0]) * self.anim)
        g = int(COLORS["bg_dark"][1] + (COLORS["primary_dark"][1] - COLORS["bg_dark"][1]) * self.anim)
        b = int(COLORS["bg_dark"][2] + (COLORS["primary_dark"][2] - COLORS["bg_dark"][2]) * self.anim)
        pygame.draw.rect(screen, (r, g, b), self.rect, border_radius=13)
        pygame.draw.rect(screen, COLORS["border"], self.rect, 2, border_radius=13)

        # Knob
        knob_x = self.x + 4 + int((self.w - self.h + 2) * self.anim)
        knob_rect = pygame.Rect(knob_x, self.y + 3, self.h - 6, self.h - 6)
        knob_color = COLORS["primary"] if self.value else COLORS["text_gray"]
        pygame.draw.circle(screen, knob_color,
                           knob_rect.center, knob_rect.width // 2)


def draw_title(screen, text, y=None, font_size=48, color=None):
    """Draw a title with glow effect."""
    font = get_font(font_size, bold=True)
    color = color or COLORS["primary"]
    w = screen.get_width()
    if y is None:
        y = 40

    # Glow
    glow_surf = font.render(text, True, color)
    glow = pygame.Surface(
        (glow_surf.get_width() + 20, glow_surf.get_height() + 20),
        pygame.SRCALPHA
    )
    glow_color = (*color, 40)
    glow.blit(font.render(text, True, glow_color),
              (10, 10))
    screen.blit(glow, (w // 2 - glow.get_width() // 2, y - 10))

    # Main text
    text_surf = font.render(text, True, color)
    screen.blit(text_surf, (w // 2 - text_surf.get_width() // 2, y))

    return y + text_surf.get_height() + 20