"""After the gym: a payment reminder, a chance to repay, then the ending screen.
The tutorial never charges late fees or blocks the ending."""
import math

import pygame

from ..config import SCREEN_W, SCREEN_H
from ..game import Scene
from ..ui import sprites
from ..core.report import build_report, topic_scores
from ..ui.widgets import MenuItem, WrapList, draw_panel, draw_text, draw_hints
from .common import ConfirmScene, HINT_SPACE

PENNY = "Professor Penny"


def finale(game):
    st = game.state
    a = st.account
    if a.owed == 0:
        msg = ("You don't owe anything. Your account is in great shape!" if a.total_borrowed else
               "You never needed to borrow. Your account is in great shape!")
        game.say([("PocketBank reminder", msg)], then=lambda: show_ending(game))
        return
    rows = [("Amount you owe", f"£{a.owed}"), ("Your money", f"£{a.money}"),
            ("Payment due", "Now (after the Copperleaf Gym challenge)"), ("Late fees", "None in this tutorial")]
    if a.money >= a.owed:
        notes = ["Your repayment is due. You have enough money to repay everything you owe."]
        options = [MenuItem("Open PocketBank to repay", "bank"), MenuItem("Finish without repaying", "finish")]
    else:
        short = a.owed - a.money
        notes = [f"You have £{a.money} but owe £{a.owed}, so you're £{short} short. That's okay.",
                 "You can repay part now, then earn the rest at the Task Board in town or by battling trainers.",
                 "With real credit, contact your lender early if you can't pay. They may be able to help."]
        options = []
        if a.money > 0:
            options.append(MenuItem(f"Repay what I can now (£{a.money})", "bank"))
        options += [MenuItem("Earn money first, then come back", "earn"), MenuItem("Finish anyway", "finish")]

    def choose(c):
        if c == "bank":
            from .bank import BankScene
            game.push(BankScene(game, start="repay", on_close=lambda: finale(game)))
        elif c == "earn":
            st.flags.add("repay_pending")
            game.say(["Take your time. The Task Board in town has paid jobs.",
                      "Come back and talk to me here at the gym whenever you're ready."], speaker=PENNY)
        elif c == "finish":
            show_ending(game)

    game.push(ConfirmScene(game, "Payment reminder", rows, notes, options, choose, cancel_value=None))


def show_ending(game):
    st = game.state
    if "finished" not in st.flags and st.account.owed > 0:
        st.flags.add("missed_deadline")     # the payment milestone passed with money still owed
    st.flags.add("finished")
    st.flags.discard("repay_pending")
    if not st.demo:
        try:
            st.save()
        except OSError:
            pass
    game.push(EndingScene(game))


class EndingScene(Scene):
    """The Money Skills Report: answers by topic, how credit was used, how the scam was handled."""

    def __init__(self, game):
        super().__init__(game)
        self.report = build_report(game.state)
        items = [MenuItem(text, ("line", i)) for i, (_, text) in enumerate(self.report)]
        items += [MenuItem("Keep exploring", "explore"), MenuItem("Return to title", "title")]
        self.menu = WrapList(game, items, cancel=False, font_role="small")
        game.audio.play("level")
        game.announce(self.speech_text())

    def speech_text(self):
        name = self.game.state.player_name
        lines = " ".join(text for _, text in self.report)
        return (f"Congratulations, {name}! Your Money Skills Report. {lines} "
                "Options: Keep exploring, Return to title.")

    def handle(self, event):
        res = self.menu.handle(event)
        if not res or res[0] != "select":
            return
        value = res[1]
        if value == "explore":
            self.game.pop(self)
        elif value == "title":
            self.game.start_title()
        else:
            self.game.read(self.report[value[1]][1])

    def draw(self, surf):
        theme = self.game.theme
        hc = self.game.settings.high_contrast
        surf.fill((0, 0, 0) if hc else (18, 22, 40))
        heading = self.game.fonts.get("heading")
        small = self.game.fonts.get("small")
        st = self.game.state
        t = self.game.anim_time
        badge = sprites.coin(26)
        w = max(4, int(badge.get_width() * abs(math.cos(t * 1.5))))
        img = pygame.transform.smoothscale(badge, (w, badge.get_height()))
        surf.blit(img, img.get_rect(center=(52, 44)))
        draw_text(surf, "Your Money Skills Report", heading, theme["title"], (88, 44), "midleft")
        draw_text(surf, f"Congratulations, {st.player_name}!", small, theme["on_dark"], (SCREEN_W - 24, 44),
                  "midright")
        panel = draw_panel(surf, (24, 84, SCREEN_W - 48, SCREEN_H - HINT_SPACE - 96), theme)
        area = panel.inflate(-32, -32)
        self.menu.draw(surf, area)
        # a bar beside each topic score, as well as the "x of y right" text
        scores = {f"{name}: {right} of {asked} right": (right, asked) for _, name, right, asked in topic_scores(st)}
        for i, r in self.menu.rects:
            label = self.menu.items[i].label
            if label in scores:
                right, asked = scores[label]
                bar = pygame.Rect(r.right - 172, r.centery - 7, 150, 14)
                pygame.draw.rect(surf, theme["hp_bg"], bar, border_radius=4)
                pygame.draw.rect(surf, theme["accent"], (bar.x, bar.y, int(bar.w * right / asked), bar.h),
                                 border_radius=4)
                pygame.draw.rect(surf, theme["border"], bar, 1, border_radius=4)
        draw_hints(surf, self.game, [("Up/Down", "Scroll"), ("Enter", "Select")])
