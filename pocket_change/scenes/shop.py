"""PoketMart. Basket total and your money are always visible. If the basket
costs more than your money you choose what to do; borrowing is never silent."""
import pygame

from ..config import SCREEN_W, SCREEN_H, PAYMENT_MILESTONE
from ..core.shop import Basket, checkout
from ..data.items import ITEMS, SHOP_ORDER
from ..game import Scene
from ..ui import sprites
from ..ui.widgets import (Menu, MenuItem, action_of, is_click, draw_panel, draw_text, draw_wrapped, draw_hints,
                          draw_header, wrap)
from .common import ConfirmScene, HINT_SPACE


class ShopScene(Scene):
    def __init__(self, game, on_close=None):
        super().__init__(game)
        self.basket = Basket()
        self.on_close = on_close
        self.buttons = []
        self.build()
        game.announce("PoketMart. " + self.summary_speech())

    @property
    def acc(self):
        return self.game.state.account

    def build(self, focus=0):
        items = []
        for k in SHOP_ORDER:
            it = ITEMS[k]
            n = self.basket.qty[k]
            items.append(MenuItem(f"{it['name']}  £{it['price']}", k, note=f"In basket: {n}",
                                  speech=f"{it['name']}, £{it['price']} each. In basket: {n}. {it['desc']} "
                                         f"Left and right change the amount."))
        items += [MenuItem("Checkout", "checkout", enabled=not self.basket.empty,
                           note=None if not self.basket.empty else "Basket empty"),
                  MenuItem("Empty basket", "clear", enabled=not self.basket.empty),
                  MenuItem("Leave shop", "leave")]
        self.menu = Menu(self.game, items)
        self.menu.focus = focus

    def summary_speech(self):
        total, money = self.basket.total, self.acc.money
        text = f"Basket total £{total}. Your money £{money}."
        if total > money:
            text += f" You are £{total - money} short."
        return text

    def speech_text(self):
        return Menu.item_speech(self.menu.current) + " " + self.summary_speech()

    def change(self, item, n):
        before = self.basket.qty[item]
        self.basket.add(item, n)
        if self.basket.qty[item] != before:
            self.game.audio.play("move")
            self.build(self.menu.focus)
            self.game.announce(f"{ITEMS[item]['name']}: {self.basket.qty[item]} in basket. {self.summary_speech()}")
        else:
            self.game.audio.play("bump")

    # ------------------------------------------------------------------ input
    def handle(self, event):
        if is_click(event):
            for (item, n), r in self.buttons:
                if r.collidepoint(event.pos):
                    self.change(item, n)
                    return
        act = action_of(event)
        cur = self.menu.current.value
        if act in ("left", "right") and cur in ITEMS:
            self.change(cur, -1 if act == "left" else 1)
            return
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        if kind == "back" or value == "leave":
            self.leave()
        elif value in ITEMS:
            self.change(value, 1)
        elif value == "clear":
            self.basket.clear()
            self.build(self.menu.focus)
        elif value == "checkout":
            self.checkout()

    def leave(self):
        self.game.pop(self)
        if self.on_close:
            self.on_close()

    # ------------------------------------------------------------------ checkout flow
    def checkout(self):
        if self.acc.card_frozen:
            def answer(yes):
                if yes:
                    self.acc.set_card_frozen(False)
                    self.game.toast("Card unfrozen.")
                    self.checkout()
            self.game.ask("Your card is frozen, so card payments are blocked. Unfreeze it now?",
                          [("Unfreeze my card and pay", True), ("Not now", False)], answer, speaker="Shopkeeper")
            return
        total, money = self.basket.total, self.acc.money
        if total <= money:
            rows = [("Basket", self.basket.describe()), ("Total", f"£{total}"),
                    ("Your money", f"£{money}  to  £{money - total}"), ("Borrowing", "£0")]
            self.game.push(ConfirmScene(self.game, "Pay with your money?", rows,
                                        ["This purchase is paid entirely from your own money."],
                                        [("Pay £%d" % total, "pay"), ("Go back", "back")],
                                        lambda c: c == "pay" and self.complete(False)))
        else:
            self.shortfall()

    def shortfall(self):
        total, money = self.basket.total, self.acc.money
        plan = self.acc.plan_purchase(total)
        short = total - money
        options = [MenuItem("Remove some items", "remove"),
                   MenuItem("Earn money and come back later", "earn")]
        if plan.allowed:
            options.append(MenuItem(f"Borrow the £{short} shortfall (credit)", "borrow"))
        else:
            options.append(MenuItem(f"Borrow £{short}", "borrow", enabled=False,
                                    note="More than available credit"))
        rows = [("Basket total", f"£{total}"), ("Your money", f"£{money}"), ("You are short by", f"£{short}"),
                ("Available credit", f"£{self.acc.available_credit}")]
        notes = ["You can't pay for this basket with your money alone. What would you like to do?"]
        if not plan.allowed:
            notes.append(plan.reason + " Change the basket or come back later.")

        def choose(c):
            if c == "borrow":
                self.agreement()
            elif c == "earn":
                self.game.say(["Good plan. Win trainer battles or take a job at the Task Board in town, "
                               "then come back. Your basket has been emptied."],
                              speaker="Shopkeeper", then=self.leave)
            # "remove" (or cancel) just returns to the basket

        self.game.push(ConfirmScene(self.game, "Not enough money", rows, notes, options, choose))

    def agreement(self):
        a = self.acc
        total = self.basket.total
        plan = a.plan_purchase(total)
        rows = [("Paid from your money", f"£{plan.from_money}"),
                ("Borrowed on credit", f"£{plan.borrow}"),
                ("Interest", "£0 for this tutorial agreement"),
                ("Total to repay", f"£{plan.borrow}"),
                ("Payment due", PAYMENT_MILESTONE),
                ("Your money", f"£{a.money}  to  £{a.money - plan.from_money}"),
                ("Amount you owe", f"£{a.owed}  to  £{a.owed + plan.borrow}")]
        notes = [f"Basket total £{total}. Credit is borrowed money, not extra earnings: you'll repay it from your "
                 "own money in PocketBank. Most real credit charges interest; this tutorial agreement doesn't."]
        self.game.push(ConfirmScene(self.game, "Credit agreement: please review", rows, notes,
                                    [(f"I understand. Borrow £{plan.borrow} and buy", "yes"), ("Go back", "no")],
                                    lambda c: c == "yes" and self.complete(True)))

    def complete(self, borrow):
        st = self.game.state
        bought = self.basket.describe()
        tx = checkout(st, self.basket, allow_borrow=borrow)
        self.game.audio.play("coin")
        self.build(self.menu.focus)
        lines = [f"Thank you! You bought: {bought}"]
        if tx.debt_change:
            lines.append(f"You paid £{-tx.money_change} from your money and borrowed £{tx.debt_change}. "
                         f"You now owe £{st.account.owed}, due: {PAYMENT_MILESTONE.lower()}.")
            lines.append("You can check this purchase and repay any time in PocketBank.")
        else:
            lines.append(f"You paid £{-tx.money_change}. Your money is now £{st.account.money}.")
        if tx.debt_change and not st.account.reminder_on:
            from .bank import reminder_dialog
            self.game.say(lines, speaker="Shopkeeper", then=lambda: reminder_dialog(self.game))
        else:
            self.game.say(lines, speaker="Shopkeeper")

    # ------------------------------------------------------------------ drawing
    def draw(self, surf):
        theme = self.game.theme
        top = draw_header(surf, self.game, "PoketMart", "Prices are fixed. Compare before you buy") + 14
        left = draw_panel(surf, (16, top, 540, SCREEN_H - HINT_SPACE - top - 14), theme)
        inner = left.inflate(-24, -24)
        menu_w = inner.w - 112
        self.menu.draw(surf, (inner.x, inner.y, menu_w, inner.h))
        body = self.game.fonts.get("body")
        small = self.game.fonts.get("small")
        self.buttons = []
        for i, r in self.menu.rects:
            if i < len(SHOP_ORDER):
                k = SHOP_ORDER[i]
                for j, (label, n) in enumerate((("-", -1), ("+", 1))):
                    b = pygame.Rect(inner.x + menu_w + 10 + j * 52, r.y, 46, r.h)
                    pygame.draw.rect(surf, theme["panel_alt"], b, border_radius=8)
                    pygame.draw.rect(surf, theme["border"], b, 2, border_radius=8)
                    draw_text(surf, label, body, theme["text"], b.center, "center")
                    self.buttons.append(((k, n), b))
        right = draw_panel(surf, (left.right + 14, top, SCREEN_W - left.right - 30, left.h), theme)
        x, y, w = right.x + 20, right.y + 16, right.w - 40
        cur = self.menu.current.value
        if cur in ITEMS:
            surf.blit(sprites.item_icon(cur, 48), (x, y))
            y2 = y + 4
            draw_text(surf, ITEMS[cur]["name"], body, theme["text"], (x + 60, y2))
            draw_text(surf, f"You have: {self.game.state.inventory.get(cur, 0)}", small, theme["muted"],
                      (x + 60, y2 + body.get_linesize()))
            y += 60
            y += draw_wrapped(surf, ITEMS[cur]["desc"], small, theme["text"], (x, y, w, 0)) + 6
        pygame.draw.line(surf, theme["border"], (x, y), (x + w, y), 2)
        y += 10
        draw_text(surf, "Basket", body, theme["text"], (x, y))
        y += body.get_linesize() + 2
        lines = [(f"{n} x {ITEMS[k]['name']}", f"£{n * ITEMS[k]['price']}") for k, n in self.basket.qty.items() if n]
        if not lines:
            draw_text(surf, "Empty", small, theme["muted"], (x, y))
            y += small.get_linesize()
        for a, b in lines:
            draw_text(surf, a, small, theme["text"], (x, y))
            draw_text(surf, b, small, theme["text"], (x + w, y), "topright")
            y += small.get_linesize()
        y += 6
        total, money = self.basket.total, self.acc.money
        rows = [("Basket total", f"£{total}"), ("Your money", f"£{money}")]
        if total <= money:
            rows.append(("Money after paying", f"£{money - total}"))
        else:
            rows.append(("Short by", f"£{total - money}"))
        for a, b in rows:
            if y + body.get_linesize() > right.bottom - 2 * small.get_linesize() - 14:
                break
            draw_text(surf, a, body, theme["text"], (x, y))
            draw_text(surf, b, body, theme["bad"] if a == "Short by" else theme["text"], (x + w, y), "topright")
            y += body.get_linesize() + 2
        note = f"Credit is separate: you owe £{self.acc.owed}."
        nh = len(wrap(note, small, w)) * (small.get_linesize() + 4)
        draw_wrapped(surf, note, small, theme["muted"], (x, right.bottom - nh - 10, w, 0))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Left/Right", "Fewer/More"), ("Enter", "Select"),
                                     ("Esc", "Leave")])
