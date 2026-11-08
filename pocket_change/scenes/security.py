"""The "Something's not right" event: a scam inside the bank account.

After the player beats Saver Sam, their phone buzzes with a real PocketBank
notification of a £15 card payment they didn't make, followed by a fake text
pretending to be the bank. The player:
  1. decides what to do with the fake text (the safe choice: ignore it and open the real app),
  2. spots the payment they don't recognise in their transactions,
  3. freezes their card, and
  4. reports the payment to get a refund.
It's never a timed task, and it never touches the credit account.
"""
import random

import pygame

from ..config import SCREEN_W, SCREEN_H
from ..core.quiz import Question
from ..game import Scene
from ..ui.widgets import (Menu, MenuItem, action_of, is_click, draw_panel, draw_text, draw_wrapped, draw_hints,
                          draw_header, dim, text_height)
from .common import QuestionScene, HINT_SPACE

SCAM_AMOUNT = 15
MERCHANT = "PH1SHFIN PRIZES LTD"
FAKE_SENDER = "PockettBank-Secure"
FAKE_TEXT = (f"PockettBank: We stopped a fraud payment on your card! Your account is now LOCKED. Tap within "
             f"10 MINUTES and enter your PIN to get your £{SCAM_AMOUNT} back: pocketbank-refunds-now.co")

TEXT_QUESTION = {
    "text": "A text says it's from your bank and asks you to tap a link and enter your PIN. What do you do?",
    "choices": ["Ignore the text and open the real PocketBank app myself",
                "Tap the link quickly before the 10 minutes run out",
                "Reply to the text with my PIN"],
    "explain": "Red flags: a misspelled sender (PockettBank), pressure to act within 10 minutes, a strange link and "
               "a request for your PIN. Your bank never asks for your PIN. Check your account in the real app "
               "instead.",
    "terms": ["phishing", "PIN", "scam"],
}


def scam_ready(state):
    return ("trainer:sam" in state.flags and "scam_started" not in state.flags
            and state.account.money >= SCAM_AMOUNT)


def suspicious_payment(account):
    """The scam card payment if it hasn't been reported yet."""
    refunded = {t.detail for t in account.transactions if t.kind == "refund"}
    for t in reversed(account.transactions):
        if t.kind == "card" and f"#{t.seq}" not in refunded:
            return t
    return None


def security_alert(state):
    return "scam_started" in state.flags and "scam_reported" not in state.flags


def start_scam_event(game, on_done):
    """Runs the whole event, then calls on_done()."""
    st = game.state
    st.flags.add("scam_started")
    st.account.unauthorised_payment(SCAM_AMOUNT, MERCHANT)
    game.audio.play("alert")

    def after_text(correct):
        st.flags.add("scam_text_safe" if correct else "scam_text_unsafe")
        lines = (["Good call. Let's check the account in the real PocketBank app instead."] if correct else
                 ["Luckily, nothing was sent. Now let's check the account in the real PocketBank app."])
        game.say(lines, speaker="You", then=lambda: game.push(SecurityCheckScene(game, on_close=lambda: on_done())))

    def decide():
        q = Question(TEXT_QUESTION, "security", random.Random())
        game.push(QuestionScene(game, q, "A text message about your account", after_text,
                                intro=f"From: {FAKE_SENDER}. \"{FAKE_TEXT}\""))

    game.say([("PocketBank", f"Notification: card payment of £{SCAM_AMOUNT} to {MERCHANT}."),
              "Huh? You didn't buy anything from them...",
              "Bzzt! A second message arrives straight away."],
             then=lambda: game.push(PhoneTextScene(game, then=decide)))


class PhoneTextScene(Scene):
    """Shows the fake text on the trainer's phone."""
    overlay = True

    def __init__(self, game, then):
        super().__init__(game)
        self.then = then
        game.announce(self.speech_text())

    def speech_text(self):
        return f"New text message from {FAKE_SENDER}: {FAKE_TEXT} Press Enter to decide what to do."

    def handle(self, event):
        if action_of(event) in ("confirm", "back") or is_click(event):
            self.game.pop(self)
            self.then()

    def draw(self, surf):
        theme = self.game.theme
        hc = self.game.settings.high_contrast
        dim(surf, theme)
        phone = pygame.Rect(0, 0, 400, SCREEN_H - HINT_SPACE - 40)
        phone.center = (SCREEN_W // 2, (SCREEN_H - HINT_SPACE) // 2)
        pygame.draw.rect(surf, (30, 32, 44), phone, border_radius=28)
        screen = phone.inflate(-24, -48)
        pygame.draw.rect(surf, (0, 0, 0) if hc else (238, 242, 248), screen, border_radius=12)
        small = self.game.fonts.get("small")
        body = self.game.fonts.get("body")
        ink = (255, 255, 255) if hc else (30, 34, 50)
        draw_text(surf, "Messages", small, ink, (screen.centerx, screen.y + 12), "midtop")
        y = screen.y + 16 + small.get_linesize()
        draw_text(surf, FAKE_SENDER, body, ink, (screen.x + 16, y))
        y += body.get_linesize() + 6
        bubble = pygame.Rect(screen.x + 12, y, screen.w - 24, 0)
        bubble.h = text_height(FAKE_TEXT, small, bubble.w - 24) + 20
        pygame.draw.rect(surf, (40, 40, 40) if hc else (255, 255, 255), bubble, border_radius=14)
        pygame.draw.rect(surf, theme["border"], bubble, 2, border_radius=14)
        draw_wrapped(surf, FAKE_TEXT, small, ink, (bubble.x + 12, bubble.y + 10, bubble.w - 24, 0))
        hint = "Press Enter to decide what to do."
        draw_wrapped(surf, hint, small, ink, (screen.x + 16, min(bubble.bottom + 16, screen.bottom - 60),
                                             screen.w - 32, 0))
        draw_hints(surf, self.game, [("Enter", "Continue")])


class SecurityCheckScene(Scene):
    """PocketBank's security check: spot the payment, freeze the card, report it. One step at a time."""

    STEPS = ["spot", "freeze", "report", "done"]

    def __init__(self, game, on_close=None):
        super().__init__(game)
        self.acc = game.state.account
        self.on_close = on_close
        self.tx = suspicious_payment(self.acc)
        self.notice = ""
        flags = game.state.flags
        if self.tx is None:
            self.step = "done"
        elif self.acc.card_frozen:
            self.step = "report"
        elif "scam_spotted" in flags:
            self.step = "freeze"
        else:
            self.step = "spot"
        self.enter()

    @property
    def index(self):
        return self.STEPS.index(self.step)

    def enter(self):
        if self.step == "spot":
            recent = list(reversed(self.acc.transactions))[:6]
            items = [MenuItem(f"{t.label}: {'+' if t.money_change > 0 else '-'}£{abs(t.money_change)}"
                              if t.money_change else t.label, t.seq) for t in recent]
            items.append(MenuItem("Come back later", "leave"))
        elif self.step == "freeze":
            items = [MenuItem("Freeze my card", "freeze"), MenuItem("Come back later", "leave")]
        elif self.step == "report":
            items = [MenuItem(f"Report it and ask for a refund of £{-self.tx.money_change}", "report"),
                     MenuItem("Come back later", "leave")]
        else:
            items = [MenuItem("Done", "leave")]
        self.menu = Menu(self.game, items)
        self.game.announce(self.speech_text())

    def content(self):
        a = self.acc
        if self.step == "spot":
            return ("Check your recent payments",
                    ["Your phone says there was a card payment you didn't make. Look through your recent "
                     "transactions (newest first) and choose the one you don't recognise."])
        if self.step == "freeze":
            return ("Freeze your card",
                    [f"You found it: {self.tx.label}, £{-self.tx.money_change}.",
                     "Freezing your card stops any new card payments straight away, so whoever took this can't "
                     "take more. You can unfreeze it any time in PocketBank."])
        if self.step == "report":
            return ("Report the payment",
                    ["Your card is frozen. Now report the payment you didn't make.",
                     "When you report a payment you didn't make, your bank looks into it and refunds you."])
        refund = next((t for t in reversed(a.transactions) if t.kind == "refund"), None)
        lines = ["Card: frozen. Unfreeze it in PocketBank when you're ready to shop again."]
        if refund:
            lines.insert(0, f"Refunded: £{refund.money_change}. Your money is now £{a.money}.")
        lines.append("In real life, contact your bank straight away using the number on your card or the "
                     "official app, never a number or link from a message.")
        return ("Your account is safe", lines)

    def speech_text(self):
        title, lines = self.content()
        parts = [f"PocketBank security check. Step {self.index + 1} of 4. {title}."] + lines
        if self.notice:
            parts.append(self.notice)
        parts.append("Options: " + ", ".join(Menu.item_speech(i) for i in self.menu.items))
        return " ".join(parts)

    def close(self):
        self.game.pop(self)
        if self.on_close:
            self.on_close()

    def handle(self, event):
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        st = self.game.state
        if kind == "back" or value == "leave":
            self.close()
            return
        if self.step == "spot":
            if value == self.tx.seq:
                st.flags.add("scam_spotted")
                self.notice = ""
                self.game.audio.play("correct")
                self.step = "freeze"
                self.enter()
            else:
                t = next(t for t in self.acc.transactions if t.seq == value)
                self.notice = f"That one's yours: {why_yours(t)}"
                self.game.audio.play("bump")
                self.game.announce(self.notice)
        elif value == "freeze":
            self.acc.set_card_frozen(True)
            st.flags.add("scam_frozen")
            self.game.audio.play("select")
            self.step = "report"
            self.enter()
        elif value == "report":
            self.acc.report_payment(self.tx)
            st.flags.add("scam_reported")
            if st.demo and st.demo_task == "scam":
                st.demo_task = "done"
            self.game.audio.play("coin")
            self.step = "done"
            self.enter()

    def draw(self, surf):
        theme = self.game.theme
        top = draw_header(surf, self.game, "PocketBank: Security check", "Practice account. No real money") + 12
        panel = draw_panel(surf, (40, top, SCREEN_W - 80, SCREEN_H - HINT_SPACE - top - 12), theme)
        x, w = panel.x + 28, panel.w - 56
        small = self.game.fonts.get("small")
        body = self.game.fonts.get("body")
        heading = self.game.fonts.get("heading")
        y = panel.y + 14
        draw_text(surf, f"Step {self.index + 1} of 4", small, theme["muted"], (x, y))
        for k in range(4):
            cx = panel.right - 28 - (3 - k) * 22
            if k <= self.index:
                pygame.draw.circle(surf, theme["accent"], (cx, y + 9), 7)
            pygame.draw.circle(surf, theme["text"], (cx, y + 9), 7, 2)
        y += small.get_linesize() + 6
        title, lines = self.content()
        draw_text(surf, title, heading, theme["text"], (x, y))
        y += heading.get_linesize() + 8
        for line in lines:
            y += draw_wrapped(surf, line, body, theme["text"], (x, y, w, 0)) + 6
        if self.notice:
            y += draw_wrapped(surf, self.notice, small, theme["muted"], (x, y, w, 0)) + 6
        menu_h = self.menu.needed_height()
        area_top = max(y + 6, panel.bottom - menu_h - 16) if self.step != "spot" else y + 6
        self.menu.draw(surf, (x, area_top, w, panel.bottom - 16 - area_top))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Select"), ("Esc", "Come back later")])


def why_yours(t):
    return {
        "gift": "your starting money.",
        "reward": "a battle reward you won.",
        "earning": "a Task Board job you did.",
        "purchase": "your own PoketMart shopping.",
        "repayment": "a repayment you made.",
        "refund": "a refund you were given.",
        "loss": "money lost after losing a battle.",
    }.get(t.kind, "a payment you made.")
