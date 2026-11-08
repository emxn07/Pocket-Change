"""PocketBank practice: the accessible account tasks on their own, without the adventure.

Opened from the title screen. It uses a fresh practice account every time
(owe £20, have £50, like the Judge Demo) and never saves anything.
"""
from ..config import SCREEN_W, SCREEN_H
from ..game import Scene
from ..ui.widgets import Menu, MenuItem, draw_panel, draw_text, draw_wrapped, draw_hints, draw_header
from .common import HINT_SPACE

INTRO = ("Practise real account tasks with a pretend account. Nothing here is saved and no real money is involved. "
         "Everything works with the keyboard, the mouse, large text, high contrast and read aloud.")


class PracticeHubScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.build()
        game.announce(self.speech_text())

    @property
    def acc(self):
        return self.game.state.account

    def build(self, focus=0):
        from .security import security_alert
        st = self.game.state
        if security_alert(st):
            scam_note = "In progress"
        elif "scam_reported" in st.flags:
            scam_note = "Done"
        else:
            scam_note = None
        items = [
            MenuItem("Guided Mode: check and repay what you owe", "guided",
                     note="Done" if self.acc.owed == 0 else None),
            MenuItem("Security check: a payment you didn't make", "security", note=scam_note),
            MenuItem("Set a payment reminder", "reminder", note="On" if self.acc.reminder_on else None),
            MenuItem("Open the full PocketBank app", "bank"),
            MenuItem("Options: text size, contrast, read aloud", "options"),
            MenuItem("Start again with a fresh account", "reset"),
            MenuItem("Back to title", "title"),
        ]
        self.menu = Menu(self.game, items)
        self.menu.focus = min(focus, len(items) - 1)

    def on_resume(self):
        self.build(self.menu.focus)

    def summary(self):
        a = self.acc
        return f"Your money: £{a.money}. You owe: £{a.owed}. Available credit: £{a.available_credit}."

    def speech_text(self):
        return (f"PocketBank practice. {INTRO} {self.summary()} Options: " +
                ", ".join(Menu.item_speech(i) for i in self.menu.items))

    def handle(self, event):
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        g = self.game
        if kind == "back" or value == "title":
            g.start_title()
        elif value == "guided":
            from .bank import GuidedBankScene
            g.push(GuidedBankScene(g))
        elif value == "security":
            self.security()
        elif value == "reminder":
            self.reminder()
        elif value == "bank":
            from .bank import BankScene
            g.push(BankScene(g))
        elif value == "options":
            from .menus import OptionsScene
            g.push(OptionsScene(g, from_title=True))
        elif value == "reset":
            g.start_practice()

    def security(self):
        from .security import security_alert, start_scam_event, SecurityCheckScene
        g, st = self.game, self.game.state
        if security_alert(st):
            g.push(SecurityCheckScene(g))
        elif "scam_started" in st.flags:
            g.say(["You've already completed the security check. Choose 'Start again with a fresh account' "
                   "to try it again."], speaker="PocketBank")
        elif self.acc.money < 15:
            g.say(["This practice needs at least £15 in your money. Start again with a fresh account."],
                  speaker="PocketBank")
        else:
            start_scam_event(g, on_done=lambda: None)

    def reminder(self):
        from .bank import reminder_dialog, reminder_text
        g = self.game

        def preview():
            if self.acc.reminder_on and self.acc.owed > 0:
                g.say([("PocketBank", reminder_text(self.acc)),
                       "In the adventure, this reminder appears when you reach the Copperleaf Gym, before your "
                       "payment is due."], speaker="Preview")

        reminder_dialog(g, then=preview)

    def draw(self, surf):
        theme = self.game.theme
        top = draw_header(surf, self.game, "PocketBank practice", "Pretend account. Nothing is saved") + 12
        body = self.game.fonts.get("body")
        small = self.game.fonts.get("small")
        panel = draw_panel(surf, (24, top, SCREEN_W - 48, SCREEN_H - HINT_SPACE - top - 12), theme)
        x, w = panel.x + 24, panel.w - 48
        y = panel.y + 16
        y += draw_wrapped(surf, INTRO, small, theme["muted"], (x, y, w, 0)) + 6
        draw_text(surf, self.summary(), body, theme["text"], (x, y))
        y += body.get_linesize() + 14
        self.menu.draw(surf, (x, y, w, panel.bottom - 16 - y))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Open"), ("Esc", "Title")])
