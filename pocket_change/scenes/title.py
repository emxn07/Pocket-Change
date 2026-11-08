"""Title screen: a coin drops into place as the O in POCKET, then the logo appears."""
import math
import random

import pygame

from ..config import SCREEN_W, SCREEN_H
from ..core.game_state import GameState
from ..game import Scene
from ..ui import sprites
from ..ui.widgets import Menu, MenuItem, action_of, is_click, draw_text, draw_hints

GOLD = (250, 204, 70)
GOLD_DARK = (176, 120, 30)
ANIM_END = 2.6


def _bounce(t):
    """Ease-out bounce, t in 0..1."""
    n, d = 7.5625, 2.75
    if t < 1 / d:
        return n * t * t
    if t < 2 / d:
        t -= 1.5 / d
        return n * t * t + 0.75
    if t < 2.5 / d:
        t -= 2.25 / d
        return n * t * t + 0.9375
    t -= 2.625 / d
    return n * t * t + 0.984375


class TitleScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.t = 0.0 if game.motion else ANIM_END     # Reduce motion: show the finished logo straight away
        has_save = GameState.save_exists()
        self.menu = Menu(game, [
            MenuItem("New Game", "new"),
            MenuItem("Continue", "continue", enabled=has_save, note=None if has_save else "No save yet"),
            MenuItem("Judge Demo", "demo", note="Prepared 3-minute demo"),
            MenuItem("PocketBank practice", "practice", note="Account tasks only"),
            MenuItem("Options", "options", note="Text size, contrast, read aloud"),
            MenuItem("Quit", "quit"),
        ], cancel=False)
        rng = random.Random(4)
        self.bg_coins = [(rng.randrange(SCREEN_W), rng.randrange(SCREEN_H), rng.uniform(10, 30), rng.randint(5, 12))
                         for _ in range(18)]

    @property
    def ready(self):
        return self.t >= ANIM_END

    def speech_text(self):
        return "Pocket Change. " + ". ".join(Menu.item_speech(i) for i in self.menu.items)

    def on_resume(self):
        has_save = GameState.save_exists()
        item = self.menu.items[1]
        item.enabled, item.note = has_save, None if has_save else "No save yet"

    def handle(self, event):
        if not self.ready:
            if action_of(event) or is_click(event):
                self.t = ANIM_END
                self.game.announce(self.speech_text())
            return
        res = self.menu.handle(event)
        if not res or res[0] != "select":
            return
        choice = res[1]
        if choice == "new":
            if GameState.save_exists():
                self.game.ask("Start a new adventure? Your saved adventure will be replaced the next time you save.",
                              [("Start new adventure", True), ("Go back", False)],
                              lambda yes: yes and self.game.start_new_game())
            else:
                self.game.start_new_game()
        elif choice == "continue":
            self.game.continue_game()
        elif choice == "demo":
            self.game.start_demo()
        elif choice == "practice":
            self.game.start_practice()
        elif choice == "options":
            from .menus import OptionsScene
            self.game.push(OptionsScene(self.game, from_title=True))
        elif choice == "quit":
            self.game.running = False

    def update(self, dt):
        was_ready = self.ready
        self.t += dt
        if self.ready and not was_ready:
            self.game.announce(self.speech_text())

    # ------------------------------------------------------------------ drawing
    def _draw_euro_e(self, surf, rect, colour, alpha):
        """A euro-style E: an open C with two bars. Still reads clearly as an E."""
        s = pygame.Surface(rect.size, pygame.SRCALPHA)
        w, h = rect.size
        stroke = max(6, h // 7)
        pygame.draw.arc(s, colour, (0, 0, w + w // 3, h), math.radians(70), math.radians(290), stroke)
        for fy in (0.38, 0.6):
            pygame.draw.rect(s, colour, (0, int(h * fy) - stroke // 2, int(w * 0.85), stroke))
        s.set_alpha(alpha)
        surf.blit(s, rect)

    def draw(self, surf):
        hc = self.game.settings.high_contrast
        surf.fill((0, 0, 0) if hc else (14, 18, 34))
        t = self.t
        if not hc and t > 1.0 and self.game.motion:
            a = min(1.0, (t - 1.0) / 1.2)
            for x, y, speed, r in self.bg_coins:
                yy = (y + self.game.anim_time * speed) % (SCREEN_H + 40) - 20
                img = sprites.coin(r).copy()
                img.set_alpha(int(50 * a))
                surf.blit(img, (x, yy))
        big = self.game.fonts.get("big", scaled=False)
        p_img = big.render("P", True, GOLD)
        rest_img = big.render("CKET", True, GOLD)
        cap_h = int(big.get_ascent() * 0.72)
        radius = cap_h // 2 + 2
        coin_w = radius * 2 + 10
        total_w = p_img.get_width() + coin_w + rest_img.get_width()
        x0 = (SCREEN_W - total_w) // 2
        base_y = 100
        coin_cx = x0 + p_img.get_width() + coin_w // 2
        letter_top = base_y
        coin_cy_target = letter_top + big.get_ascent() - cap_h // 2 - 6
        # coin drop
        drop = min(1.0, t / 1.1)
        cy = -60 + (coin_cy_target + 60) * _bounce(drop)
        spin = abs(math.cos(min(t, 1.1) * 7)) if t < 1.1 else 1.0
        coin_img = sprites.coin(radius)
        cw = max(4, int(coin_img.get_width() * (0.35 + 0.65 * spin)))
        coin_img = pygame.transform.smoothscale(coin_img, (cw, coin_img.get_height()))
        surf.blit(coin_img, coin_img.get_rect(center=(coin_cx, int(cy))))
        # letters fade in
        a = max(0.0, min(1.0, (t - 1.0) / 0.5))
        if a > 0:
            for img, x in ((p_img, x0), (rest_img, x0 + p_img.get_width() + coin_w)):
                shadow = big.render("P" if img is p_img else "CKET", True, GOLD_DARK)
                shadow.set_alpha(int(255 * a))
                surf.blit(shadow, (x + 4, letter_top + 5))
                img.set_alpha(int(255 * a))
                surf.blit(img, (x, letter_top))
        # CHANGE with a euro-style E
        b = max(0.0, min(1.0, (t - 1.6) / 0.6))
        if b > 0:
            col = (255, 255, 255)
            chang = big.render("CHANG", True, col)
            e_w = int(chang.get_width() / 5 * 0.95)
            tw = chang.get_width() + e_w + 8
            cx = (SCREEN_W - tw) // 2
            y = base_y + big.get_linesize() - 6 + int((1 - b) * 30)
            chang.set_alpha(int(255 * b))
            surf.blit(chang, (cx, y))
            asc = big.get_ascent()
            e_rect = pygame.Rect(cx + chang.get_width() + 6, y + asc - cap_h - 5, e_w, cap_h + 2)
            self._draw_euro_e(surf, e_rect, col, int(255 * b))
            # sparkle on the coin
            if t < 2.4:
                s = int(10 + 8 * math.sin(t * 12))
                pygame.draw.line(surf, (255, 255, 255), (coin_cx + radius - 4, int(cy) - radius - s),
                                 (coin_cx + radius - 4, int(cy) - radius + s), 3)
                pygame.draw.line(surf, (255, 255, 255), (coin_cx + radius - 4 - s, int(cy) - radius),
                                 (coin_cx + radius - 4 + s, int(cy) - radius), 3)
        small = self.game.fonts.get("small")
        if self.ready:
            draw_text(surf, "An accessible adventure for practising money and credit",
                      small, (220, 225, 240), (SCREEN_W // 2, 284), "center")
            mw = 470
            h = self.menu.needed_height()
            self.menu.draw(surf, ((SCREEN_W - mw) // 2, 306, mw, min(h, SCREEN_H - 306 - 44)))
            draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Select")])
        elif t > 0.3:
            draw_text(surf, "Press any key", small, (160, 170, 190), (SCREEN_W // 2, SCREEN_H - 40), "center")
