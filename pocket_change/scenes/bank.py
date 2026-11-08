"""PocketBank: the trainer phone's banking app.

Every figure has a plain-language explanation beside it. Every action works
with the keyboard alone (and the mouse), and a repayment is always reviewed
before it is made.
"""
import pygame

from ..config import SCREEN_W, SCREEN_H
from ..data.questions import GLOSSARY
from ..game import Scene
from ..ui.widgets import (Menu, MenuItem, WrapList, draw_panel, draw_text, draw_wrapped, draw_hints, draw_header,
                          dim, is_click, text_height)
from .common import ConfirmScene, HINT_SPACE

HELP_TERMS = ["your money", "amount you owe", "credit", "credit limit", "available credit", "interest",
              "repayment", "due date", "transaction"]


def money_line(change, what):
    if change > 0:
        return f"+£{change} {what}"
    if change < 0:
        return f"-£{-change} {what}"
    return f"No change to {what}"


def describe_tx(tx):
    lines = [money_line(tx.money_change, "your money"),
             money_line(tx.debt_change, "amount you owe")]
    after = f"After this: your money £{tx.money_after}, you owe £{tx.owed_after}."
    return lines, after


class BankScene(Scene):
    def __init__(self, game, start="nav", on_close=None):
        super().__init__(game)
        self.acc = game.state.account
        self.on_close = on_close
        self.build_nav()
        self.mode = "nav"
        self.sub = None
        self.notice = ""
        if start == "repay":
            self.nav.focus = 3
            self.open("repay")
        game.announce("PocketBank. " + self.overview_speech())

    def build_nav(self, focus=0):
        from .security import security_alert
        items = [
            MenuItem("Guided Mode", "guided", note="Recommended",
                     speech="Guided Mode, recommended: one step at a time, with plain-language explanations"),
            MenuItem("Overview", "overview", speech="Overview: money, amount owed and credit"),
            MenuItem("Transactions", "transactions"),
            MenuItem("Make a repayment", "repay"),
        ]
        if security_alert(self.game.state):
            items.append(MenuItem("Security check", "security", note="1 alert",
                                  speech="Security check: one alert about a payment"))
        frozen = self.acc.card_frozen
        items += [
            MenuItem("Unfreeze card" if frozen else "Freeze card", "card", note="Card frozen" if frozen else None),
            MenuItem("Payment reminder", "reminder", note="On" if self.acc.reminder_on else "Off",
                     speech=f"Payment reminder, {'on' if self.acc.reminder_on else 'off'}"),
            MenuItem("Explain terms", "help", speech="Explain terms: what do these words mean?"),
            MenuItem("Close PocketBank", "close"),
        ]
        self.nav = Menu(self.game, items)
        self.nav.focus = min(focus, len(items) - 1)

    def on_resume(self):
        if self.mode == "nav":
            self.build_nav(self.nav.focus)

    def toggle_card(self):
        a = self.acc
        if a.card_frozen:
            title, notes = "Unfreeze your card?", ["Card payments, like shopping at PoketMart, will work again."]
            options = [("Unfreeze my card", True), ("Keep it frozen", False)]
        else:
            title = "Freeze your card?"
            notes = ["Freezing stops any new card payments straight away, for example if your card is lost or "
                     "you spot a payment you didn't make. You can unfreeze it any time here."]
            options = [("Freeze my card", True), ("Go back", False)]

        def done(yes):
            if yes:
                a.set_card_frozen(not a.card_frozen)
                self.game.audio.play("select")
                self.game.toast("Card frozen." if a.card_frozen else "Card unfrozen.")
            self.build_nav(self.nav.focus)

        self.game.push(ConfirmScene(self.game, title, [("Card", "Frozen" if a.card_frozen else "Active")],
                                    notes, options, done, cancel_value=False))

    # ------------------------------------------------------------------ content
    def overview_rows(self):
        a = self.acc
        return [
            ("Your money", f"£{a.money}", "Money you earned or were given. You can spend it."),
            ("Amount you owe", f"£{a.owed}", "Borrowing you still need to repay. It is separate from your money."),
            ("Credit limit", f"£{a.limit}", "The most you can owe at once. It is not money you have."),
            ("Available credit", f"£{a.available_credit}",
             f"How much more you could borrow: £{a.limit} limit minus £{a.owed} owed."),
            ("Payment due", a.payment_due_text,
             "A deadline appears only after you borrow. This tutorial has no late fees."),
            ("Interest", "£0", "Interest £0 for this tutorial agreement. Most real credit charges interest."),
            ("Payment reminder", "On" if a.reminder_on else "Off",
             "A nudge before your payment is due, so it doesn't slip your mind."),
            ("Card", "Frozen" if a.card_frozen else "Active",
             "A frozen card blocks new card payments. You can freeze or unfreeze it here any time."),
        ]

    def overview_speech(self):
        return ". ".join(f"{l}: {v}. {e}" for l, v, e in self.overview_rows()[:5])

    def _announce_preview(self):
        pass   # the Menu already announces the focused item

    def open(self, section):
        self.notice = ""
        if section == "guided":
            self.game.push(GuidedBankScene(self.game))
            return
        if section == "security":
            from .security import SecurityCheckScene
            self.game.push(SecurityCheckScene(self.game))
            return
        if section == "card":
            self.toggle_card()
            return
        if section == "reminder":
            reminder_dialog(self.game, then=lambda: self.build_nav(self.nav.focus))
            return
        if section == "overview":
            rows = self.overview_rows()
            self.sub = WrapList(self.game, [MenuItem(f"{l}:  {v}\n{e}", l, speech=f"{l}: {v}. {e}")
                                            for l, v, e in rows])
        elif section == "transactions":
            txs = list(reversed(self.acc.transactions))
            if not txs:
                self.game.say(["No transactions yet."])
                return
            items = []
            for tx in txs:
                lines, after = describe_tx(tx)
                items.append(MenuItem(f"{tx.label}\n{lines[0]}. {lines[1]}.", tx.seq,
                                      speech=f"{tx.label}. {lines[0]}. {lines[1]}. {after} {tx.detail}"))
            self.sub = WrapList(self.game, items)
        elif section == "repay":
            self.sub = self._repay_menu()
            if self.sub is None:
                return
        elif section == "help":
            self.sub = WrapList(self.game, [MenuItem(f"{t[0].upper() + t[1:]}\n{GLOSSARY[t]}", t,
                                                     speech=f"{t}: {GLOSSARY[t]}") for t in HELP_TERMS])
        self.mode = section
        self.game.announce(self.speech_text())

    def _repay_menu(self):
        a = self.acc
        if a.owed == 0:
            self.game.say(["You don't owe anything right now, so there's nothing to repay. Nice work!"],
                          speaker="PocketBank")
            return None
        items = []
        if a.money >= a.owed:
            items.append(MenuItem(f"Pay the full amount owed: £{a.owed}", a.owed))
        else:
            items.append(MenuItem(f"Pay the full amount owed: £{a.owed}", a.owed, enabled=False,
                                  note=f"You have £{a.money}"))
            if a.money > 0:
                items.append(MenuItem(f"Pay what I can now: £{a.money}", a.money))
        if a.owed > 10 and a.money >= 10:
            items.append(MenuItem("Pay £10", 10))
        items.append(MenuItem("Type a different amount", "type"))
        items.append(MenuItem("Cancel", "cancel"))
        return Menu(self.game, items)

    # ------------------------------------------------------------------ repayment flow
    def choose_amount(self, amount):
        problem = self.acc.check_repayment(amount)
        if problem:
            self.notice = problem
            self.game.audio.play("bump")
            self.game.announce(problem)
            return False
        self.review(amount)
        return True

    def review(self, amount):
        a = self.acc
        rows = [
            ("Repayment", f"£{amount}"),
            ("Your money", f"£{a.money}  to  £{a.money - amount}"),
            ("Amount you owe", f"£{a.owed}  to  £{a.owed - amount}"),
            ("Available credit", f"£{a.available_credit}  to  £{a.available_credit + amount}"),
        ]
        notes = ["Interest £0 for this tutorial agreement, so you repay exactly what you borrowed.",
                 "Nothing is paid until you choose Confirm repayment."]

        def done(choice):
            if choice == "confirm":
                self.acc.repay(amount)
                self.game.audio.play("coin")
                self.after_payment(amount)
            elif choice == "change":
                self.open("repay")
            else:
                self.back_to_nav()

        self.game.push(ConfirmScene(self.game, "Review your repayment", rows, notes,
                                    [("Confirm repayment", "confirm"), ("Change amount", "change"),
                                     ("Cancel", "cancel")], done, cancel_value="change"))

    def after_payment(self, amount):
        a = self.acc
        rows = [("Paid", f"£{amount}"), ("Your money now", f"£{a.money}"), ("Amount you owe now", f"£{a.owed}"),
                ("Available credit now", f"£{a.available_credit}"), ("Payment due", a.payment_due_text)]
        notes = ["You've paid off everything you owed!" if a.owed == 0 else
                 f"You still owe £{a.owed}. You can repay more whenever you have the money."]

        def done(choice):
            if choice == "tx":
                self.mode = "nav"
                self.nav.focus = 2
                self.open("transactions")
            else:
                self.back_to_nav()

        self.game.push(ConfirmScene(self.game, "Payment complete", rows, notes,
                                    [("Done", "done"), ("View transactions", "tx")], done, cancel_value="done"))

    def back_to_nav(self):
        self.mode = "nav"
        self.sub = None
        self.notice = ""
        self.game.announce("PocketBank. " + Menu.item_speech(self.nav.current))

    def close(self):
        self.game.pop(self)
        if self.on_close:
            self.on_close()

    # ------------------------------------------------------------------ input
    def handle(self, event):
        if self.mode == "nav":
            res = self.nav.handle(event)
            if not res:
                return
            kind, value = res
            if kind == "back" or value == "close":
                self.close()
            else:
                self.open(value)
            return
        res = self.sub.handle(event)
        if not res:
            return
        kind, value = res
        if kind == "back" or value == "cancel":
            self.back_to_nav()
        elif self.mode == "repay":
            if value == "type":
                self.game.push(AmountEntry(self.game, self))
            else:
                self.choose_amount(value)
        elif self.mode in ("overview", "transactions", "help"):
            self.game.read(Menu.item_speech(self.sub.current))

    def speech_text(self):
        if self.mode == "nav":
            cur = self.nav.current.value
            if cur in ("overview", "close"):
                return "PocketBank. " + self.overview_speech()
            return "PocketBank. " + Menu.item_speech(self.nav.current)
        if self.mode == "repay":
            a = self.acc
            text = (f"Make a repayment. You owe £{a.owed}. Your money: £{a.money}. "
                    f"{self.notice + ' ' if self.notice else ''}Options: " +
                    ", ".join(Menu.item_speech(i) for i in self.sub.items))
            return text
        return Menu.item_speech(self.sub.current)

    # ------------------------------------------------------------------ drawing
    def draw(self, surf):
        theme = self.game.theme
        top = draw_header(surf, self.game, "PocketBank", "Practice account. No real money") + 14
        left = draw_panel(surf, (16, top, 300, SCREEN_H - HINT_SPACE - top - 14), theme)
        self.nav.draw(surf, left.inflate(-20, -24))
        if self.mode == "nav":
            # highlight is on the nav; show a summary on the right
            pass
        right = draw_panel(surf, (left.right + 14, top, SCREEN_W - left.right - 30, left.h), theme)
        inner = right.inflate(-36, -30)
        body = self.game.fonts.get("body")
        small = self.game.fonts.get("small")
        heading = self.game.fonts.get("heading")
        section = self.mode if self.mode != "nav" else self.nav.current.value
        titles = {"guided": "Guided Mode", "security": "Security check", "card": "Your card",
                  "reminder": "Payment reminder", "overview": "Overview", "transactions": "Transactions", "repay": "Make a repayment",
                  "help": "Explain terms", "close": "Overview"}
        draw_text(surf, titles.get(section, ""), heading, theme["text"], (inner.x, inner.y))
        y = inner.y + heading.get_linesize() + 10
        area = pygame.Rect(inner.x, y, inner.w, inner.bottom - y)
        if self.mode == "nav":
            self._draw_preview(surf, section, area)
            hint = [("Up/Down", "Move"), ("Enter", "Open"), ("Esc", "Close")]
        else:
            if self.mode == "repay":
                a = self.acc
                summary = f"You owe £{a.owed}.   Your money: £{a.money}."
                draw_text(surf, summary, body, theme["text"], (area.x, area.y))
                area.y += body.get_linesize() + 8
                area.h -= body.get_linesize() + 8
                if self.notice:
                    h = draw_wrapped(surf, "! " + self.notice, small, theme["bad"], (area.x, area.y, area.w, 0))
                    area.y += h + 6
                    area.h -= h + 6
                self.sub.draw(surf, area)
            else:
                self.sub.draw(surf, area)
            hint = [("Up/Down", "Move"), ("Enter", "Select"), ("Esc", "Back")]
        draw_hints(surf, self.game, hint)

    def _draw_preview(self, surf, section, area):
        theme = self.game.theme
        body = self.game.fonts.get("body")
        small = self.game.fonts.get("small")
        y = area.y
        if section in ("overview", "close"):
            for label, value, explain in self.overview_rows():
                if y + body.get_linesize() > area.bottom:
                    break
                draw_text(surf, label, body, theme["text"], (area.x, y))
                draw_text(surf, value, body, theme["text"], (area.right, y), "topright")
                y += body.get_linesize()
                h = draw_wrapped(surf, explain, small, theme["muted"], (area.x, y, area.w, 0), 2)
                y += h + 6
                pygame.draw.line(surf, theme["border"], (area.x, y - 3), (area.right, y - 3), 1)
                if y > area.bottom:
                    break
        elif section == "transactions":
            txs = list(reversed(self.acc.transactions))[:4]
            if not txs:
                draw_text(surf, "No transactions yet.", body, theme["muted"], (area.x, y))
            for tx in txs:
                lines, _ = describe_tx(tx)
                draw_text(surf, tx.label, body, theme["text"], (area.x, y))
                y += body.get_linesize()
                y += draw_wrapped(surf, f"{lines[0]}. {lines[1]}.", small, theme["muted"],
                                  (area.x, y, area.w, 0), 2) + 8
                if y > area.bottom - 40:
                    break
            draw_text(surf, "Press Enter to see every transaction.", small, theme["muted"], (area.x, area.bottom - 20))
        elif section == "repay":
            a = self.acc
            text = (f"You owe £{a.owed} and have £{a.money}. " +
                    ("Press Enter to choose an amount. You'll review it before anything is paid."
                     if a.owed else "You don't owe anything right now."))
            draw_wrapped(surf, text, body, theme["text"], area)
        elif section == "security":
            draw_wrapped(surf, "There's a card payment you might not recognise. Press Enter to check your recent "
                               "payments, freeze your card and report anything you didn't make.",
                         body, theme["text"], area)
        elif section == "reminder":
            state = "on" if self.acc.reminder_on else "off"
            draw_wrapped(surf, f"Your payment reminder is {state}. When it's on and you owe money, PocketBank "
                               "reminds you when you reach the Copperleaf Gym, before your payment is due.",
                         body, theme["text"], area)
        elif section == "card":
            state = "frozen. New card payments are blocked" if self.acc.card_frozen else "active"
            draw_wrapped(surf, f"Your card is {state}. Freeze it if it's lost or you spot a payment you didn't "
                               "make; unfreeze it when you're ready to shop again.", body, theme["text"], area)
        elif section == "guided":
            draw_wrapped(surf, "Guided Mode shows one task at a time, with a clear next step and a way back. "
                               "Check a purchase, see what you owe, choose a repayment, review it, and get a "
                               "receipt. Press Enter to start.", body, theme["text"], area)
        elif section == "help":
            draw_wrapped(surf, "Plain-language explanations of every account term, such as credit limit, "
                               "available credit and interest.", body, theme["text"], area)


class AmountEntry(Scene):
    """Type a repayment amount with the keyboard. Mistakes get a clear explanation."""
    overlay = True
    text_input = True

    def __init__(self, game, bank):
        super().__init__(game)
        self.bank = bank
        self.text = ""
        self.error = ""
        self.buttons = []
        game.announce(self.speech_text())

    def speech_text(self):
        a = self.bank.acc
        return (f"Type a repayment amount in pounds, then press Enter. You owe £{a.owed} and have £{a.money}. "
                f"Current amount: {self.text or 'empty'}. {self.error}")

    def submit(self):
        if not self.text:
            self.error = "Type an amount first."
            self.game.announce(self.error)
            return
        amount = int(self.text)
        problem = self.bank.acc.check_repayment(amount)
        if problem:
            self.error = problem
            self.game.audio.play("bump")
            self.game.announce(problem)
            return
        self.game.pop(self)
        self.bank.review(amount)

    def handle(self, event):
        if event.type == pygame.TEXTINPUT:
            for ch in event.text:
                if ch.isdigit() and len(self.text) < 4:
                    self.text = (self.text + ch).lstrip("0")
                    self.error = ""
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.submit()
            elif event.key == pygame.K_ESCAPE:
                self.game.pop(self)
        elif is_click(event):
            for name, r in self.buttons:
                if r.collidepoint(event.pos):
                    if name == "ok":
                        self.submit()
                    else:
                        self.game.pop(self)

    def draw(self, surf):
        theme = self.game.theme
        dim(surf, theme)
        heading = self.game.fonts.get("heading")
        body = self.game.fonts.get("body")
        small = self.game.fonts.get("small")
        panel = draw_panel(surf, (120, 110, SCREEN_W - 240, 360), theme)
        a = self.bank.acc
        draw_text(surf, "Repayment amount", heading, theme["text"], (panel.x + 30, panel.y + 24))
        draw_text(surf, f"You owe £{a.owed}. Your money: £{a.money}.", body, theme["muted"],
                  (panel.x + 30, panel.y + 30 + heading.get_linesize()))
        field = pygame.Rect(panel.x + 30, panel.y + 110, panel.w - 60, heading.get_linesize() + 24)
        pygame.draw.rect(surf, theme["panel_alt"], field, border_radius=8)
        pygame.draw.rect(surf, theme["focus"], field, 4, border_radius=8)
        img = heading.render("£" + self.text, True, theme["text"])
        surf.blit(img, (field.x + 16, field.centery - img.get_height() // 2))
        if int(self.game.anim_time * 2) % 2 == 0:
            x = field.x + 18 + img.get_width()
            pygame.draw.line(surf, theme["text"], (x, field.y + 10), (x, field.bottom - 10), 3)
        y = field.bottom + 10
        if self.error:
            y += draw_wrapped(surf, "! " + self.error, small, theme["bad"], (field.x, y, field.w, 0))
        self.buttons = []
        x = field.x
        for name, label in (("ok", "Review (Enter)"), ("cancel", "Cancel (Esc)")):
            im = body.render(label, True, theme["text"])
            r = im.get_rect(topleft=(x, panel.bottom - im.get_height() - 40)).inflate(30, 16)
            pygame.draw.rect(surf, theme["focus_bg"] if name == "ok" else theme["panel_alt"], r, border_radius=8)
            pygame.draw.rect(surf, theme["focus"] if name == "ok" else theme["border"], r, 3, border_radius=8)
            surf.blit(im, im.get_rect(center=r.center))
            self.buttons.append((name, r))
            x = r.right + 16
        draw_hints(surf, self.game, [("0-9", "Type amount"), ("Backspace", "Delete"), ("Enter", "Review"),
                                     ("Esc", "Cancel"), ("F5", "Read")])


# =========================================================================== Guided Mode
class GuidedBankScene(Scene):
    """PocketBank Guided Mode: one task at a time, a clear next action and a way back.

    Steps: check the purchase -> what you owe and what you have -> choose a repayment
    -> review -> receipt. Cancelling never changes balances. With £0 owed it simply
    says there's nothing to repay (and never suggests borrowing)."""

    def __init__(self, game, on_close=None, title="PocketBank: Guided Mode"):
        super().__init__(game)
        self.acc = game.state.account
        self.on_close = on_close
        self.title = title
        self.completed = False
        self.notice = ""
        self.amount = None
        self.paid = None
        purchases = [t for t in self.acc.transactions if t.kind == "purchase" and t.debt_change > 0]
        self.purchase = purchases[-1] if purchases else None
        if self.acc.owed == 0:
            self.steps = ["nothing"]
        else:
            self.steps = (["purchase"] if self.purchase else []) + ["owed", "choose", "review", "receipt"]
        self.i = 0
        self.enter()

    # ------------------------------------------------------------------ steps
    @property
    def step(self):
        return self.steps[self.i]

    def go(self, step):
        self.i = self.steps.index(step)
        self.enter()

    def enter(self):
        a = self.acc
        step = self.step
        if step == "nothing":
            items = [MenuItem("Done", "done")]
        elif step == "purchase":
            items = [MenuItem("Next: see what you owe", "next"), MenuItem("Leave Guided Mode", "leave")]
        elif step == "owed":
            items = [MenuItem("Next: choose a repayment", "next"), MenuItem("Go back", "back")]
        elif step == "choose":
            items = []
            if a.money >= a.owed:
                items.append(MenuItem(f"£{a.owed}: everything you owe", a.owed))
            elif a.money > 0:
                items.append(MenuItem(f"£{a.money}: all the money you have", a.money))
            if a.owed > 10 and a.money >= 10 and a.money != 10:
                items.append(MenuItem("£10", 10))
            if a.money > 0:
                items.append(MenuItem("Type a different amount", "type"))
            items.append(MenuItem("Go back", "back"))
        elif step == "review":
            items = [MenuItem("Confirm payment", "confirm"), MenuItem("Go back and change it", "back")]
        else:
            items = [MenuItem("Done", "done")]
        self.menu = Menu(self.game, items, on_focus=lambda _: self.game.announce(self.amount_explainer()))
        self.game.announce(self.speech_text())

    def amount_explainer(self):
        if self.step != "choose" or not isinstance(self.menu.current.value, int):
            return Menu.item_speech(self.menu.current) if self.step == "choose" else ""
        amount = self.menu.current.value
        left = self.acc.owed - amount
        return (f"Paying £{amount} clears everything you owe." if left == 0 else
                f"Paying £{amount} leaves £{left} still to repay. You can pay the rest later.")

    def blocks(self):
        """The current step's content as simple blocks: (kind, ...)."""
        a = self.acc
        step = self.step
        if step == "nothing":
            return [("title", "You don't owe anything"),
                    ("card", "You owe", "£0", "There's nothing to repay."),
                    ("card", "Your money", f"£{a.money}", "Money you earned or were given."),
                    ("card", "Available credit", f"£{a.available_credit}",
                     "How much you could borrow. It's borrowing capacity, not money you've earned."),
                    ("text", "You don't need to borrow anything. Nice work!")]
        if step == "purchase":
            t = self.purchase
            total = -t.money_change + t.debt_change
            return [("title", "Check the purchase"),
                    ("text", f"{t.label}: {t.detail.split(' £')[0] if t.detail else ''}"),
                    ("rows", [("Total cost", f"£{total}"), ("Paid from your money", f"£{-t.money_change}"),
                              ("Borrowed on credit", f"£{t.debt_change}"),
                              ("Interest", "£0 for this tutorial agreement")]),
                    ("text", "The borrowed part is what you now owe.")]
        if step == "owed":
            return [("title", "What you owe and what you have"),
                    ("card", "You owe", f"£{a.owed}", f"Borrowing you still need to repay. Due: {a.payment_due_text}."),
                    ("card", "Your money", f"£{a.money}", "Your own money. Repayments come from here."),
                    ("card", "Available credit", f"£{a.available_credit}",
                     "How much more you could borrow. It's borrowing capacity, not earnings.")]
        if step == "choose":
            blocks = [("title", "How much would you like to repay?"),
                      ("text", f"You owe £{a.owed}. You have £{a.money}.")]
            if a.money == 0:
                blocks.append(("text", "You don't have any money to repay with yet. Earn some at the Task Board or "
                                       "in trainer battles, then come back. You don't need to borrow."))
            else:
                blocks.append(("note", self.amount_explainer()))
            if self.notice:
                blocks.append(("error", self.notice))
            return blocks
        if step == "review":
            n = self.amount
            return [("title", "Review your payment"),
                    ("big", f"You will pay £{n}. You will have £{a.money - n} left and owe £{a.owed - n}."),
                    ("rows", [("Your money", f"£{a.money}  to  £{a.money - n}"),
                              ("Amount you owe", f"£{a.owed}  to  £{a.owed - n}"),
                              ("Available credit", f"£{a.available_credit}  to  £{a.available_credit + n}")]),
                    ("text", "Nothing is paid until you choose Confirm payment.")]
        return [("title", "Payment complete"),
                ("big", f"Payment complete: £{self.paid} paid. Your money: £{a.money}. Amount owed: £{a.owed}."),
                ("text", "This payment is recorded in your transactions." +
                 ("" if a.owed == 0 else f" You still owe £{a.owed}. You can repay more whenever you're ready."))]

    def speech_text(self):
        parts = [f"{self.title}. Step {self.i + 1} of {len(self.steps)}."]
        for b in self.blocks():
            if b[0] in ("title", "text", "big", "note", "error"):
                parts.append(b[1])
            elif b[0] == "card":
                parts.append(f"{b[1]}: {b[2]}. {b[3]}")
            elif b[0] == "rows":
                parts += [f"{l}: {v}" for l, v in b[1]]
        parts.append("Options: " + ", ".join(Menu.item_speech(i) for i in self.menu.items))
        return " ".join(parts)

    # ------------------------------------------------------------------ actions
    def review(self, amount):
        """Called by AmountEntry or a preset amount."""
        problem = self.acc.check_repayment(amount)
        if problem:
            self.notice = problem
            self.game.audio.play("bump")
            self.game.announce(problem)
            return
        self.notice = ""
        self.amount = amount
        self.go("review")

    def close(self):
        self.game.pop(self)
        if self.on_close:
            self.on_close(self.completed)

    def handle(self, event):
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        step = self.step
        if kind == "back" or value in ("back", "leave"):
            if self.i == 0 or step == "receipt" or value == "leave":
                self.close()
            elif step == "review":
                self.go("choose")
            else:
                self.i -= 1
                self.enter()
            return
        if value == "done":
            self.completed = True
            self.close()
        elif value == "next":
            self.i += 1
            self.enter()
        elif value == "type":
            self.game.push(AmountEntry(self.game, self))
        elif value == "confirm":
            self.acc.repay(self.amount)
            self.paid = self.amount
            self.completed = True
            self.game.audio.play("coin")
            self.go("receipt")
        elif isinstance(value, int):
            self.review(value)

    # ------------------------------------------------------------------ drawing
    def draw(self, surf):
        theme = self.game.theme
        top = draw_header(surf, self.game, self.title, "Practice account. No real money") + 12
        panel = draw_panel(surf, (40, top, SCREEN_W - 80, SCREEN_H - HINT_SPACE - top - 12), theme)
        x, w = panel.x + 28, panel.w - 56
        small = self.game.fonts.get("small")
        body = self.game.fonts.get("body")
        heading = self.game.fonts.get("heading")
        y = panel.y + 14
        # progress: text plus dots (never colour alone)
        draw_text(surf, f"Step {self.i + 1} of {len(self.steps)}", small, theme["muted"], (x, y))
        for k in range(len(self.steps)):
            cx = panel.right - 28 - (len(self.steps) - 1 - k) * 22
            if k <= self.i:
                pygame.draw.circle(surf, theme["accent"], (cx, y + 9), 7)
            pygame.draw.circle(surf, theme["text"], (cx, y + 9), 7, 2)
        y += small.get_linesize() + 6
        menu_h = self.menu.needed_height()
        bottom = panel.bottom - menu_h - 22
        for b in self.blocks():
            kind = b[0]
            if y > bottom - 10:
                break
            if kind == "title":
                draw_text(surf, b[1], heading, theme["text"], (x, y))
                y += heading.get_linesize() + 8
            elif kind in ("text", "note"):
                y += draw_wrapped(surf, b[1], small if kind == "note" else body,
                                  theme["muted"] if kind == "note" else theme["text"], (x, y, w, 0)) + 6
            elif kind == "error":
                y += draw_wrapped(surf, "! " + b[1], small, theme["bad"], (x, y, w, 0)) + 6
            elif kind == "big":
                y += draw_wrapped(surf, b[1], heading, theme["text"], (x, y, w, 0)) + 8
            elif kind == "card":
                _, label, value, explain = b
                eh = text_height(explain, small, w - 24, 2)
                r = pygame.Rect(x, y, w, body.get_linesize() + eh + 18)
                pygame.draw.rect(surf, theme["panel_alt"], r, border_radius=10)
                pygame.draw.rect(surf, theme["border"], r, 2, border_radius=10)
                draw_text(surf, label, body, theme["text"], (r.x + 12, r.y + 8))
                draw_text(surf, value, body, theme["text"], (r.right - 12, r.y + 8), "topright")
                draw_wrapped(surf, explain, small, theme["muted"], (r.x + 12, r.y + 10 + body.get_linesize(),
                                                                     w - 24, 0), 2)
                y = r.bottom + 8
            elif kind == "rows":
                for label, value in b[1]:
                    draw_text(surf, label, body, theme["muted"], (x, y))
                    draw_text(surf, value, body, theme["text"], (x + w, y), "topright")
                    y += body.get_linesize() + 4
                    pygame.draw.line(surf, theme["border"], (x, y - 2), (x + w, y - 2), 1)
                y += 6
        self.menu.draw(surf, (x, panel.bottom - menu_h - 16, w, menu_h))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Select"), ("Esc", "Go back")])


# =========================================================================== payment reminder
REMINDER_WHEN = "when you reach the Copperleaf Gym, before your payment is due"


def reminder_text(account):
    return (f"PocketBank reminder: you owe £{account.owed}. Your payment is due "
            f"{account.payment_due_text.lower()}. You have £{account.money}.")


def reminder_dialog(game, then=None):
    """Turn the payment reminder on or off, with a plain explanation."""
    a = game.state.account
    if a.reminder_on:
        title, options = "Turn off your payment reminder?", [("Turn it off", True), ("Keep it on", False)]
        notes = ["You won't get a nudge before your payment is due. You can turn it back on any time."]
    else:
        title, options = "Set a payment reminder?", [("Turn reminder on", True), ("Not now", False)]
        notes = [f"If you owe money, PocketBank will remind you {REMINDER_WHEN}.",
                 "Reminders help payments not slip your mind. Many real banking apps offer them."]

    def done(yes):
        if yes:
            a.reminder_on = not a.reminder_on
            if a.reminder_on:
                game.state.flags.add("reminder_set")
            game.audio.play("select")
            game.toast("Payment reminder on." if a.reminder_on else "Payment reminder off.")
        if then:
            then()

    game.push(ConfirmScene(game, title, [("Payment reminder", "On" if a.reminder_on else "Off"),
                                         ("Amount you owe now", f"£{a.owed}")],
                           notes, options, done, cancel_value=False))
