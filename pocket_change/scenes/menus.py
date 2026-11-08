"""The pause menu and its screens: Mintlings, Items, Mintdex, Save and Options."""
import pygame

from ..config import SCREEN_W, SCREEN_H, MAX_MOVES
from ..core.battle import item_problem, use_item_outside_battle
from ..core.mintling import xp_to_next
from ..data.items import ITEMS, SHOP_ORDER
from ..data.moves import MOVES
from ..data.species import SPECIES, DEX_ORDER
from ..game import Scene
from ..settings import TEXT_SIZES, SPEECH_RATES
from ..ui import sprites
from ..ui.widgets import (Menu, MenuItem, draw_panel, draw_text, draw_wrapped, draw_hints, draw_header,
                          draw_hp_bar, draw_type_badge, dim)
from ..data.types import chart_lines
from .common import PartyPicker, TypeChartScene, HINT_SPACE, mon_summary


# =========================================================================== pause menu
class PauseMenu(Scene):
    overlay = True

    def __init__(self, game):
        super().__init__(game)
        self.menu = Menu(game, [
            MenuItem("Mintlings", "mintlings", note="Party"),
            MenuItem("PocketBank", "bank", note="Money & credit"),
            MenuItem("Items", "items"),
            MenuItem("Mintdex", "dex"),
            MenuItem("Save", "save"),
            MenuItem("Options", "options"),
            MenuItem("Close menu", "close"),
        ])
        game.announce("Menu. " + Menu.item_speech(self.menu.current))

    def speech_text(self):
        return "Menu. Options: " + ", ".join(Menu.item_speech(i) for i in self.menu.items)

    def handle(self, event):
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        g = self.game
        if kind == "back" or value == "close":
            g.pop(self)
        elif value == "mintlings":
            g.push(PartyScene(g))
        elif value == "bank":
            from .bank import BankScene
            g.push(BankScene(g))
        elif value == "items":
            g.push(ItemsScene(g))
        elif value == "dex":
            g.push(DexScene(g))
        elif value == "save":
            ok, msg = g.save()
            if ok:
                g.audio.play("coin")
            g.say([msg])
        elif value == "options":
            g.push(OptionsScene(g))

    def draw(self, surf):
        theme = self.game.theme
        dim(surf, theme)
        w = 380
        heading = self.game.fonts.get("heading")
        mh = self.menu.needed_height()
        h = min(SCREEN_H - HINT_SPACE - 30, mh + heading.get_linesize() + 60)
        panel = draw_panel(surf, (SCREEN_W - w - 20, 16, w, h), theme)
        st = self.game.state
        draw_text(surf, f"{st.player_name}", heading, theme["text"], (panel.x + 20, panel.y + 14))
        if st.gym_beaten:
            draw_text(surf, st.badge_name, self.game.fonts.get("tiny"), theme["accent"],
                      (panel.right - 20, panel.y + 22), "topright")
        top = panel.y + heading.get_linesize() + 26
        self.menu.draw(surf, (panel.x + 20, top, w - 40, panel.bottom - top - 16))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Open"), ("Esc", "Close")])


# =========================================================================== party
def draw_mon_details(surf, game, mon, rect):
    theme = game.theme
    body = game.fonts.get("body")
    small = game.fonts.get("small")
    tiny = game.fonts.get("tiny")
    r = draw_panel(surf, rect, theme)
    img = sprites.mintling(mon.species_id, 128)
    surf.blit(img, (r.x + 16, r.y + 12))
    x = r.x + 160
    y = r.y + 16
    draw_text(surf, f"{mon.name}  Lv {mon.level}", body, theme["text"], (x, y))
    y += body.get_linesize() + 4
    draw_type_badge(surf, mon.type, tiny, (x, y))
    y += tiny.get_linesize() + 18
    draw_hp_bar(surf, (x, y, r.right - x - 20, 16), mon.hp, mon.max_hp, theme, small)
    y += 16 + small.get_linesize() + 6
    draw_text(surf, f"Attack {mon.atk}   Defence {mon.df}", small, theme["text"], (x, y))
    y += small.get_linesize() + 2
    draw_text(surf, f"XP {mon.xp}/{xp_to_next(mon.level)} to next level", small, theme["muted"], (x, y))
    y = max(y + small.get_linesize() + 12, r.y + 150)
    draw_text(surf, "Moves", body, theme["text"], (r.x + 20, y))
    y += body.get_linesize() + 4
    for mid in mon.moves:
        m = MOVES[mid]
        kind = f"Power {m['power']}" if m["kind"] == "damage" else "Support"
        line = f"{m['name']} ({m['type'] or 'No type'}, {kind}): {m['desc']}"
        y += draw_wrapped(surf, line, small, theme["text"], (r.x + 20, y, r.w - 40, 0), 2) + 4
        if y > r.bottom - 20:
            break
    if len(mon.moves) < MAX_MOVES and y < r.bottom - 20:
        draw_wrapped(surf, third_move_hint(mon), small, theme["muted"], (r.x + 20, y + 4, r.w - 40, 0), 2)


def third_move_hint(mon):
    sp = mon.species
    move = MOVES[sp["third"]]["name"]
    kind, value = sp["unlock"]
    if kind == "level":
        return f"Third move: {move}, learned at level {value}."
    who = {"budget": "the PoketMart shopkeeper's budgeting task", "repayment": "Banking Guide Cora's task",
           "security": "Security Guide Ollie's task"}[value]
    return f"Third move: {move}, taught after {who}."


class PartyScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.build()

    def build(self, focus=0):
        party = self.game.state.party
        items = [MenuItem(f"{m.name}  Lv {m.level}", i, note="Fainted" if m.fainted else f"HP {m.hp}/{m.max_hp}",
                          speech=mon_summary(m)) for i, m in enumerate(party)]
        items.append(MenuItem("Back", "back"))
        self.menu = Menu(self.game, items)
        self.menu.focus = min(focus, len(items) - 1)

    def speech_text(self):
        cur = self.menu.current.value
        if cur == "back":
            return "Back"
        m = self.game.state.party[cur]
        moves = ", ".join(MOVES[x]["name"] for x in m.moves)
        return f"{mon_summary(m)}. Attack {m.atk}, defence {m.df}. Moves: {moves}. Press Enter to change party order."

    def handle(self, event):
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        if kind == "back" or value == "back":
            self.game.pop(self)
            return
        party = self.game.state.party
        if len(party) < 2:
            self.game.say(["You only have one Mintling. Befriend more in the tall grass!"])
            return
        first = value

        def swap(second):
            party[first], party[second] = party[second], party[first]
            self.build(second)
            self.game.toast("Party order changed. The first Mintling leads in battle.")

        self.game.push(PartyPicker(self.game, f"Swap {party[first].name} with which Mintling?", swap,
                                   check=lambda m: "Selected" if m is party[first] else None))

    def draw(self, surf):
        top = draw_header(surf, self.game, "Mintlings", "The first Mintling leads in battle") + 16
        left = pygame.Rect(16, top, 330, SCREEN_H - HINT_SPACE - top - 16)
        draw_panel(surf, left, self.game.theme)
        self.menu.draw(surf, left.inflate(-24, -24))
        cur = self.menu.current.value
        if cur != "back":
            draw_mon_details(surf, self.game, self.game.state.party[cur],
                             (left.right + 16, top, SCREEN_W - left.right - 32, left.h))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Swap order"), ("Esc", "Back")])


# =========================================================================== items
class ItemsScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.build()

    def build(self, focus=0):
        inv = self.game.state.inventory
        items = [MenuItem(ITEMS[k]["name"], k, note=f"x{inv.get(k, 0)}", enabled=inv.get(k, 0) > 0,
                          speech=f"{ITEMS[k]['name']}, you have {inv.get(k, 0)}. {ITEMS[k]['desc']}")
                 for k in SHOP_ORDER]
        items.append(MenuItem("Back", "back"))
        self.menu = Menu(self.game, items)
        self.menu.focus = focus

    def speech_text(self):
        return "Items. " + ". ".join(Menu.item_speech(i) for i in self.menu.items)

    def handle(self, event):
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        if kind == "back" or value == "back":
            self.game.pop(self)
            return
        st = self.game.state
        if ITEMS[value]["capsule"]:
            self.game.say(["Mint Capsules are for wild encounters. Use one from Items during a wild battle."])
            return
        focus = self.menu.focus

        def pick(i):
            msg = use_item_outside_battle(st, value, st.party[i])
            self.game.audio.play("heal")
            self.build(focus)
            self.game.say([msg])

        self.game.push(PartyPicker(self.game, f"Use {ITEMS[value]['name']} on which Mintling?", pick,
                                   check=lambda m: item_problem(st, value, m)))

    def draw(self, surf):
        theme = self.game.theme
        top = draw_header(surf, self.game, "Items", "Buy more at PoketMart") + 16
        left = pygame.Rect(16, top, 440, SCREEN_H - HINT_SPACE - top - 16)
        draw_panel(surf, left, theme)
        self.menu.draw(surf, left.inflate(-24, -24))
        right = draw_panel(surf, (left.right + 16, top, SCREEN_W - left.right - 32, left.h), theme)
        cur = self.menu.current.value
        if cur in ITEMS:
            surf.blit(sprites.item_icon(cur, 96), (right.x + 20, right.y + 20))
            body = self.game.fonts.get("body")
            draw_text(surf, ITEMS[cur]["name"], self.game.fonts.get("heading"), theme["text"],
                      (right.x + 130, right.y + 30))
            y = right.y + 130
            y += draw_wrapped(surf, ITEMS[cur]["desc"], body, theme["text"], (right.x + 20, y, right.w - 40, 0))
            draw_wrapped(surf, f"Shop price: £{ITEMS[cur]['price']}", self.game.fonts.get("small"),
                         theme["muted"], (right.x + 20, y + 10, right.w - 40, 0))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Use"), ("Esc", "Back")])


# =========================================================================== Mintdex
class DexScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        dex = game.state.dex
        items = [MenuItem("Type chart", "chart", note="Strong against")]
        for i, sp in enumerate(DEX_ORDER):
            status = dex.get(sp)
            name = SPECIES[sp]["name"] if status else "???"
            label = {"caught": "CAUGHT", "seen": "SEEN", None: "UNSEEN"}[status]
            items.append(MenuItem(f"No.{i + 1}  {name}", sp, note=label))
        items.append(MenuItem("Back", "back"))
        self.menu = Menu(game, items)

    def speech_text(self):
        sp = self.menu.current.value
        if sp == "back":
            return "Back"
        if sp == "chart":
            return "Type chart. Press Enter to open it. " + " ".join(chart_lines())
        status = self.game.state.dex.get(sp)
        if not status:
            return "Unknown Mintling. Not seen yet."
        s = SPECIES[sp]
        return f"{s['name']}, {s['type']} type, {'caught' if status == 'caught' else 'seen'}. {s['desc']}"

    def handle(self, event):
        res = self.menu.handle(event)
        if res and (res[0] == "back" or res[1] == "back"):
            self.game.pop(self)
        elif res and res[1] == "chart":
            self.game.push(TypeChartScene(self.game))

    def draw(self, surf):
        theme = self.game.theme
        dex = self.game.state.dex
        seen = len(dex)
        caught = sum(1 for v in dex.values() if v == "caught")
        top = draw_header(surf, self.game, "Mintdex", f"Seen {seen}   Caught {caught}   of {len(DEX_ORDER)}") + 16
        left = pygame.Rect(16, top, 420, SCREEN_H - HINT_SPACE - top - 16)
        draw_panel(surf, left, theme)
        self.menu.draw(surf, left.inflate(-24, -24))
        right = draw_panel(surf, (left.right + 16, top, SCREEN_W - left.right - 32, left.h), theme)
        sp = self.menu.current.value
        if sp == "back":
            return draw_hints(surf, self.game, [("Up/Down", "Move"), ("Esc", "Back")])
        if sp == "chart":
            y = right.y + 20
            for line in chart_lines():
                y += draw_wrapped(surf, line, self.game.fonts.get("small"), theme["text"],
                                  (right.x + 20, y, right.w - 40, 0)) + 6
            draw_wrapped(surf, "Press Enter to see the chart with arrows.", self.game.fonts.get("small"),
                         theme["muted"], (right.x + 20, y + 10, right.w - 40, 0))
            return draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Open"), ("Esc", "Back")])
        status = dex.get(sp)
        body = self.game.fonts.get("body")
        img = sprites.mintling(sp, 160, silhouette=not status)
        surf.blit(img, img.get_rect(midtop=(right.centerx, right.y + 16)))
        y = right.y + 186
        if status:
            s = SPECIES[sp]
            draw_text(surf, s["name"], self.game.fonts.get("heading"), theme["text"], (right.x + 20, y))
            draw_type_badge(surf, s["type"], self.game.fonts.get("tiny"), (right.right - 20, y + 6), "topright")
            y += self.game.fonts.get("heading").get_linesize() + 6
            mark = "Caught (in your collection)" if status == "caught" else "Seen (not caught yet)"
            if status == "caught":
                surf.blit(sprites.item_icon("capsule", 32), (right.x + 18, y - 4))
            draw_text(surf, mark, self.game.fonts.get("small"), theme["muted"], (right.x + 56, y))
            y += self.game.fonts.get("small").get_linesize() + 10
            draw_wrapped(surf, s["desc"], body, theme["text"], (right.x + 20, y, right.w - 40, 0))
        else:
            draw_wrapped(surf, "Not seen yet. Explore the tall grass on Route 1 to find it!", body, theme["text"],
                         (right.x + 20, y, right.w - 40, 0))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Esc", "Back")])


# =========================================================================== options
OPTION_HELP = {
    "text_size": "Makes all text bigger. Layouts wrap and scroll so nothing is cut off.",
    "high_contrast": "White text on black with bright yellow focus outlines.",
    "auto_read": "Reads dialogue, questions, menus and account figures aloud automatically. "
                 "You can always press R to read the screen, or T to stop.",
    "sound": "Turns sound effects on or off.",
    "reduce_motion": "Stops bobbing, spinning, flashing and sliding effects, shows text instantly and skips the "
                     "title animation. Helpful for motion sensitivity or if movement is distracting.",
    "speech_rate": "How fast read aloud speaks: Slow, Normal or Fast.",
    "relaxed_battles": "Opponents deal 25% less damage, for anyone who wants less pressure in battle. "
                       "Questions, money and rewards work exactly the same.",
    "test": "Plays a short sample so you can check read aloud works on this computer.",
    "controls": "Shows every keyboard and mouse control.",
    "title": "Leaves the adventure. Save first if you want to keep your progress.",
    "back": "Return to the previous screen.",
}

CONTROLS = [
    ("Arrow keys or WASD", "Move, and move between options"),
    ("Enter, Space or Z", "Talk, select, confirm"),
    ("Esc, X or Backspace", "Back. Opens the menu while exploring"),
    ("R (or F5)", "Read the current screen aloud. Press again to replay"),
    ("T (or F6)", "Stop reading aloud"),
    ("G", "Explain the terms in a question"),
    ("F11", "Toggle full screen"),
    ("Mouse", "Hover to focus, left click to choose, right click to go back, wheel to scroll"),
]


class OptionsScene(Scene):
    def __init__(self, game, from_title=False):
        super().__init__(game)
        self.from_title = from_title
        self.build()

    def build(self, focus=0):
        s = self.game.settings
        on = lambda v: "On" if v else "Off"
        items = [
            MenuItem(f"Text size: {TEXT_SIZES[s.text_size]}", "text_size"),
            MenuItem(f"High contrast: {on(s.high_contrast)}", "high_contrast"),
            MenuItem(f"Auto read-aloud: {on(s.auto_read)}", "auto_read"),
            MenuItem(f"Speech speed: {SPEECH_RATES[s.speech_rate]}", "speech_rate"),
            MenuItem(f"Reduce motion: {on(s.reduce_motion)}", "reduce_motion"),
            MenuItem(f"Sound effects: {on(s.sound)}", "sound"),
            MenuItem(f"Relaxed battles: {on(s.relaxed_battles)}", "relaxed_battles"),
            MenuItem("Test read aloud", "test", enabled=self.game.speaker.available),
            MenuItem("Controls", "controls"),
        ]
        if not self.from_title:
            items.append(MenuItem("Return to title", "title"))
        items.append(MenuItem("Back", "back"))
        self.menu = Menu(self.game, items)
        self.menu.focus = focus

    def speech_text(self):
        cur = self.menu.current
        return f"Options. {Menu.item_speech(cur)}. {OPTION_HELP.get(cur.value, '')}"

    def change(self, key, step=1):
        s = self.game.settings
        if key == "text_size":
            s.set("text_size", (s.text_size + step) % len(TEXT_SIZES))
        elif key == "speech_rate":
            s.set("speech_rate", (s.speech_rate + step) % len(SPEECH_RATES))
        elif key in ("high_contrast", "auto_read", "sound", "relaxed_battles", "reduce_motion"):
            s.set(key, not s.data[key])
        else:
            return False
        self.build(self.menu.focus)
        self.game.announce(Menu.item_speech(self.menu.current))
        return True

    def handle(self, event):
        from ..ui.widgets import action_of
        act = action_of(event)
        if act in ("left", "right") and self.change(self.menu.current.value, -1 if act == "left" else 1):
            self.game.audio.play("move")
            return
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        if kind == "back" or value == "back":
            self.game.pop(self)
        elif self.change(value):
            pass
        elif value == "test":
            self.game.read("This is Pocket Change read aloud. Your money: 40 pounds. Amount you owe: 20 pounds.")
        elif value == "controls":
            self.game.say([f"{k}: {v}." for k, v in CONTROLS], speaker="Controls")
        elif value == "title":
            self.game.ask("Return to the title screen? Anything you haven't saved will be lost.",
                          [("Return to title", True), ("Stay", False)],
                          lambda yes: yes and self.game.start_title())

    def draw(self, surf):
        theme = self.game.theme
        top = draw_header(surf, self.game, "Options", "Settings are kept between sessions") + 16
        left = pygame.Rect(16, top, 500, SCREEN_H - HINT_SPACE - top - 16)
        draw_panel(surf, left, theme)
        self.menu.draw(surf, left.inflate(-24, -24))
        right = draw_panel(surf, (left.right + 16, top, SCREEN_W - left.right - 32, left.h), theme)
        body = self.game.fonts.get("body")
        small = self.game.fonts.get("small")
        y = right.y + 20
        y += draw_wrapped(surf, OPTION_HELP.get(self.menu.current.value, ""), body, theme["text"],
                          (right.x + 20, y, right.w - 40, 0)) + 20
        sp = self.game.speaker
        status = f"Read-aloud engine: {sp.description}."
        if not sp.available:
            status += (" To use read aloud, install a speech engine: on Linux, espeak-ng. "
                       "Windows and macOS have one built in.")
        draw_wrapped(surf, status, small, theme["muted"], (right.x + 20, y, right.w - 40, 0))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Left/Right", "Change"), ("Enter", "Select"),
                                     ("Esc", "Back")])
