"""Overlays shared by many screens: dialogue, questions, confirmations and pickers."""
import pygame

from ..config import SCREEN_W, SCREEN_H, MAX_MOVES
from ..data.moves import MOVES
from ..data.questions import GLOSSARY, TOPIC_NAMES
from ..game import Scene
from ..ui import sprites
from ..ui.widgets import (Menu, MenuItem, WrapList, action_of, is_click, draw_panel, draw_text, draw_wrapped,
                          wrap, dim, draw_hints, draw_hp_bar, draw_type_badge, text_height)

HINT_SPACE = 34   # height reserved for the hint bar


# =========================================================================== dialogue
class Dialogue(Scene):
    overlay = True

    def __init__(self, game, pages, then=None, speaker=None, choices=None, portrait=None):
        super().__init__(game)
        self.raw = [p if isinstance(p, tuple) else (speaker, p) for p in pages]
        self.raw = [(game.fmt(s) if s else s, game.fmt(t)) for s, t in self.raw]
        self.then = then
        self.choices = choices
        self.portrait = portrait
        self.pages = None
        self.index = 0
        self.shown = 0.0
        self.menu = None
        self.closed = False
        self._announced = -1

    def _layout(self):
        font = self.game.fonts.get("body")
        width = SCREEN_W - 40 - 48
        max_lines = 4
        pages = []
        for spk, text in self.raw:
            lines = wrap(text, font, width)
            for i in range(0, len(lines), max_lines):
                pages.append((spk, lines[i:i + max_lines]))
        self.pages = pages or [(None, [""])]
        self.line_h = font.get_linesize() + 4
        name_h = self.game.fonts.get("small").get_linesize() + 10
        h = 24 + max_lines * self.line_h + 8
        self.box = pygame.Rect(20, SCREEN_H - HINT_SPACE - h - 8, SCREEN_W - 40, h)
        self.name_h = name_h

    @property
    def page_text(self):
        return " ".join(self.pages[self.index][1])

    @property
    def page_done(self):
        return self.shown >= len(self.page_text)

    @property
    def last_page(self):
        return self.index >= len(self.pages) - 1

    def _maybe_menu(self):
        if self.choices and self.last_page and self.page_done and self.menu is None:
            self.menu = Menu(self.game, [MenuItem(lbl, val) for lbl, val in self.choices], font_role="body")
            self.game.announce("Options: " + ", ".join(lbl for lbl, _ in self.choices))

    def update(self, dt):
        if self.pages is None:
            self._layout()
        if self._announced != self.index:
            self._announced = self.index
            spk = self.pages[self.index][0]
            self.game.announce((spk + " says: " if spk else "") + self.page_text)
        self.shown = min(len(self.page_text), self.shown + dt * 75) if self.game.motion else len(self.page_text)
        self._maybe_menu()

    def handle(self, event):
        if self.pages is None:
            return
        if self.menu:
            res = self.menu.handle(event)
            if res:
                kind, value = res
                self.finish(value if kind == "select" else None)
            return
        if action_of(event) == "confirm" or is_click(event) or action_of(event) == "back":
            if not self.page_done:
                self.shown = len(self.page_text)
            elif not self.last_page:
                self.index += 1
                self.shown = 0
                self.game.audio.play("move")
            elif not self.choices:
                self.finish()

    def finish(self, value=None):
        if self.closed:
            return
        self.closed = True
        self.game.pop(self)
        if self.then:
            if self.choices is not None:
                self.then(value)
            else:
                self.then()

    def speech_text(self):
        if self.pages is None:
            return ""
        spk = self.pages[self.index][0]
        text = (spk + " says: " if spk else "") + self.page_text
        if self.menu:
            text += ". Options: " + ", ".join(i.label for i in self.menu.items)
        return text

    def draw(self, surf):
        if self.pages is None:
            self._layout()
        theme = self.game.theme
        if self.portrait:
            img = sprites.portrait(self.portrait, 220)
            surf.blit(img, (SCREEN_W - img.get_width() - 40, self.box.y - img.get_height() + 10))
        draw_panel(surf, self.box, theme)
        spk, lines = self.pages[self.index]
        small = self.game.fonts.get("small")
        if spk:
            img = small.render(spk, True, (255, 255, 255))
            tab = pygame.Rect(self.box.x + 18, self.box.y - img.get_height() - 12, img.get_width() + 24,
                              img.get_height() + 12)
            pygame.draw.rect(surf, (44, 50, 78) if not self.game.settings.high_contrast else (0, 0, 0), tab,
                             border_top_left_radius=8, border_top_right_radius=8)
            pygame.draw.rect(surf, theme["border"], tab, 2, border_top_left_radius=8, border_top_right_radius=8)
            surf.blit(img, (tab.x + 12, tab.y + 6))
        font = self.game.fonts.get("body")
        remaining = int(self.shown)
        y = self.box.y + 16
        for line in lines:
            part = line[:max(0, remaining)]
            remaining -= len(line) + 1
            surf.blit(font.render(part, True, theme["text"]), (self.box.x + 24, y))
            y += self.line_h
        if self.page_done and not self.menu:
            bob = int(abs(((self.game.anim_time * 3) % 2) - 1) * 4)
            x, yb = self.box.right - 30, self.box.bottom - 22 + bob
            pygame.draw.polygon(surf, theme["accent"], [(x, yb), (x + 14, yb), (x + 7, yb + 9)])
        if self.menu:
            longest = max(font.size(i.label)[0] for i in self.menu.items) + 70
            w = min(SCREEN_W - 80, max(220, longest))
            h = self.menu.needed_height()
            r = pygame.Rect(SCREEN_W - w - 30, self.box.y - h - 34, w, h + 24)
            draw_panel(surf, r, theme)
            self.menu.draw(surf, r.inflate(-24, -24))
        draw_hints(surf, self.game, [("Enter", "Choose" if self.menu else "Continue")])


# =========================================================================== questions
class QuestionScene(Scene):
    """Ask a multiple-choice question, then explain the answer. No timer."""
    overlay = True

    def __init__(self, game, question, header, on_done, intro=None, on_cancel=None):
        super().__init__(game)
        self.on_cancel = on_cancel
        self.q = question
        self.header = header
        self.intro = intro
        self.on_done = on_done
        self.phase = "ask"
        self.chosen = None
        self.correct = False
        self.menu = WrapList(game, [MenuItem(f"{'ABCD'[i]}.  {c}", i, speech=f"Answer {'ABCD'[i]}: {c}")
                                    for i, c in enumerate(question.choices)], cancel=False)
        self.buttons = []
        game.announce(self.speech_text())

    def speech_text(self):
        if self.phase == "ask":
            opts = ". ".join(f"{'ABCD'[i]}: {c}" for i, c in enumerate(self.q.choices))
            hard = "Hard question. " if getattr(self.q, "level", 1) == 3 else ""
            return (f"{self.header}. {hard}{self.intro + '. ' if self.intro else ''}Question: {self.q.text} "
                    f"Answers: {opts}")
        verdict = "Correct!" if self.correct else "Not quite."
        return f"{verdict} The answer is {self.q.correct_text}. {self.q.explain}"

    def _show_terms(self):
        if not self.q.terms:
            self.game.toast("This question has no special terms.")
            return
        pages = [f"{t[0].upper() + t[1:]}: {GLOSSARY[t]}" for t in self.q.terms]
        self.game.say(pages, speaker="Terms explained")

    def _answer(self, index):
        self.chosen = index
        self.correct = self.q.is_correct(index)
        self.game.record_answer(self.correct, self.q.topic, getattr(self.q, "level", 1))
        self.game.audio.play("correct" if self.correct else "wrong")
        self.phase = "result"
        self.game.announce(self.speech_text())

    def handle(self, event):
        act = action_of(event)
        if is_click(event):
            for name, r in self.buttons:
                if r.collidepoint(event.pos):
                    self._button(name)
                    return
        if self.phase == "ask":
            if act == "terms":
                self._show_terms()
                return
            if act == "back" and self.on_cancel:
                self.game.audio.play("back")
                self.game.pop(self)
                self.on_cancel()
                return
            res = self.menu.handle(event)
            if res and res[0] == "select":
                self._answer(res[1])
        elif act == "confirm":
            self._finish()

    def _button(self, name):
        if name == "terms":
            self._show_terms()
        elif name == "read":
            self.game.read(self.speech_text())
        elif name == "continue":
            self._finish()

    def _finish(self):
        self.game.pop(self)
        self.on_done(self.correct)

    def draw(self, surf):
        theme = self.game.theme
        dim(surf, theme)
        panel = draw_panel(surf, (30, 20, SCREEN_W - 60, SCREEN_H - HINT_SPACE - 30), theme)
        inner = panel.inflate(-44, -36)
        small = self.game.fonts.get("small")
        body = self.game.fonts.get("body")
        heading = self.game.fonts.get("heading")
        y = inner.y
        draw_text(surf, self.header, small, theme["muted"], (inner.x, y))
        topic = TOPIC_NAMES.get(self.q.topic, "")
        level_note = "Hard question. " if getattr(self.q, "level", 1) == 3 else ""
        draw_text(surf, f"{level_note}Topic: {topic}", small, theme["muted"], (inner.right, y), "topright")
        y += small.get_linesize() + 8
        if self.intro:
            y += draw_wrapped(surf, self.intro, small, theme["muted"], (inner.x, y, inner.w, 0)) + 2
        y += draw_wrapped(surf, self.q.text, heading if self.game.settings.text_size == 0 else body,
                          theme["text"], (inner.x, y, inner.w, 0)) + 10
        buttons_h = small.get_linesize() + 22
        self.buttons = []
        if self.phase == "ask":
            self.menu.draw(surf, (inner.x, y, inner.w, inner.bottom - y - buttons_h - 10))
            labels = [("read", "Read aloud (R)")]
            if self.q.terms:
                labels.insert(0, ("terms", "Explain terms (G)"))
        else:
            marks = {self.q.correct_index: ("good", "Correct answer")}
            if not self.correct:
                marks[self.chosen] = ("bad", "Your answer")
            verdict = "Correct!" if self.correct else "Not quite."
            colour = theme["good"] if self.correct else theme["bad"]
            icon = pygame.Rect(inner.x, y, 34, 34)
            pygame.draw.circle(surf, colour, icon.center, 17)
            if self.correct:
                pygame.draw.lines(surf, (255, 255, 255), False,
                                  [(icon.x + 8, icon.centery), (icon.x + 15, icon.bottom - 9), (icon.right - 7, icon.y + 9)], 4)
            else:
                pygame.draw.line(surf, (255, 255, 255), (icon.x + 10, icon.y + 10), (icon.right - 10, icon.bottom - 10), 4)
                pygame.draw.line(surf, (255, 255, 255), (icon.right - 10, icon.y + 10), (icon.x + 10, icon.bottom - 10), 4)
            draw_text(surf, verdict, heading, colour, (icon.right + 12, icon.centery), "midleft")
            y = icon.bottom + 10
            shown = [self.q.correct_index] + ([self.chosen] if not self.correct else [])
            labels_txt = {i: f"{'ABCD'[i]}.  {self.q.choices[i]}" for i in shown}
            avail = inner.bottom - y - buttons_h - small.get_linesize() - 24
            text_w = inner.w - 200
            # Each answer box grows to fit its words; with large text, step down a size if needed.
            for ans_font, exp_font in ((body, body), (small, body), (small, small)):
                boxes = {i: len(wrap(labels_txt[i], ans_font, text_w)) * ans_font.get_linesize() + 16
                         for i in shown}
                need = sum(boxes.values()) + 8 * len(shown) + 4 + text_height(self.q.explain, exp_font, inner.w)
                if need <= avail:
                    break
            for i in shown:
                r = pygame.Rect(inner.x, y, inner.w, boxes[i])
                kind = marks[i][0]
                pygame.draw.rect(surf, theme["panel_alt"], r, border_radius=8)
                pygame.draw.rect(surf, theme[kind], r, 4, border_radius=8)
                draw_wrapped(surf, labels_txt[i], ans_font, theme["text"], (r.x + 16, r.y + 8, text_w, 0), 0)
                draw_text(surf, marks[i][1], small, theme[kind], (r.right - 14, r.centery), "midright")
                y = r.bottom + 8
            y += 4
            y += draw_wrapped(surf, self.q.explain, exp_font, theme["text"], (inner.x, y, inner.w, 0))
            draw_text(surf, "Fictional practice, not financial advice.", small, theme["muted"], (inner.x, y + 4))
            labels = [("continue", "Continue (Enter)"), ("read", "Read aloud (R)")]
        x = inner.x
        for name, lbl in labels:
            img = small.render(lbl, True, theme["text"])
            r = pygame.Rect(x, inner.bottom - buttons_h, img.get_width() + 30, buttons_h)
            pygame.draw.rect(surf, theme["panel_alt"], r, border_radius=8)
            pygame.draw.rect(surf, theme["focus"] if name == "continue" else theme["border"], r,
                             3 if name == "continue" else 2, border_radius=8)
            surf.blit(img, img.get_rect(center=r.center))
            self.buttons.append((name, r))
            x = r.right + 12
        hints = [("Up/Down", "Move"), ("Enter", "Answer")] if self.phase == "ask" else [("Enter", "Continue")]
        if self.phase == "ask" and self.on_cancel:
            hints.append(("Esc", "Back"))
        if self.phase == "ask" and self.q.terms:
            hints.append(("G", "Terms"))
        draw_hints(surf, self.game, hints)


# =========================================================================== confirmation
class ConfirmScene(Scene):
    """A clear review card: a title, label/value rows, notes and a choice of buttons."""
    overlay = True

    def __init__(self, game, title, rows, notes, options, then, cancel_value=None):
        super().__init__(game)
        self.title, self.rows, self.notes = title, rows, notes
        self.then = then
        self.cancel_value = cancel_value
        self.menu = Menu(game, [MenuItem(*o) if isinstance(o, tuple) else o for o in options])
        game.announce(self.speech_text())

    def speech_text(self):
        parts = [self.title]
        parts += [f"{a}: {b}" for a, b in self.rows]
        parts += self.notes
        parts.append("Options: " + ", ".join(Menu.item_speech(i) for i in self.menu.items))
        return ". ".join(parts)

    def handle(self, event):
        res = self.menu.handle(event)
        if res:
            self.game.pop(self)
            self.then(res[1] if res[0] == "select" else self.cancel_value)

    def draw(self, surf):
        theme = self.game.theme
        dim(surf, theme)
        fonts = self.game.fonts
        heading = fonts.get("heading")
        max_h = SCREEN_H - HINT_SPACE - 20
        # With large text, step the details down a size until the card fits, so nothing overlaps
        # the buttons. The title and options keep their size for as long as possible.
        for row_role, note_role, pad, menu_role, w in (("body", "small", 10, "body", SCREEN_W - 140),
                                                       ("body", "small", 8, "body", SCREEN_W - 40),
                                                       ("small", "small", 8, "body", SCREEN_W - 40),
                                                       ("small", "tiny", 6, "small", SCREEN_W - 40),
                                                       ("tiny", "tiny", 4, "small", SCREEN_W - 40)):
            row_font, note_font = fonts.get(row_role), fonts.get(note_role)
            self.menu.font_role = menu_role
            inner_w = w - 48
            row_h = row_font.get_linesize() + pad
            notes_h = sum(text_height(n, note_font, inner_w) + 6 for n in self.notes)
            menu_h = self.menu.needed_height()
            h = heading.get_linesize() + 20 + len(self.rows) * row_h + notes_h + menu_h + 60
            if h <= max_h:
                break
        h = min(h, max_h)
        panel = draw_panel(surf, ((SCREEN_W - w) // 2, max(10, (SCREEN_H - HINT_SPACE - h) // 2), w, h), theme)
        x, y = panel.x + 24, panel.y + 18
        draw_text(surf, self.title, heading, theme["text"], (x, y))
        y += heading.get_linesize() + 12
        menu_top = panel.bottom - menu_h - 18
        surf.set_clip(pygame.Rect(panel.x, y, panel.w, max(0, menu_top - 8 - y)))   # details never cover buttons
        for label, value in self.rows:
            pygame.draw.line(surf, theme["border"], (x, y + row_h - 4), (x + inner_w, y + row_h - 4), 1)
            draw_text(surf, label, row_font, theme["muted"], (x, y + 2))
            draw_text(surf, value, row_font, theme["text"], (x + inner_w, y + 2), "topright")
            y += row_h
        y += 8
        for n in self.notes:
            y += draw_wrapped(surf, n, note_font, theme["text"], (x, y, inner_w, 0)) + 6
        surf.set_clip(None)
        self.menu.draw(surf, (x, menu_top, inner_w, menu_h))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Choose"), ("Esc", "Back")])


# =========================================================================== Mintling picker
class PartyPicker(Scene):
    """Choose a party Mintling. check(mon) returns a reason it can't be picked, or None."""
    overlay = True

    def __init__(self, game, title, on_pick, check=None, cancel=True, on_cancel=None):
        super().__init__(game)
        self.title = title
        self.on_pick = on_pick
        self.on_cancel = on_cancel
        party = game.state.party
        items = []
        for i, m in enumerate(party):
            problem = check(m) if check else None
            status = "Fainted" if m.fainted else f"HP {m.hp}/{m.max_hp}"
            items.append(MenuItem(f"{m.name}  Lv {m.level}  {status}", i, enabled=problem is None,
                                  note=problem, speech=f"{m.name}, level {m.level}, {m.type} type, {status}"))
        self.menu = Menu(game, items, cancel=cancel)
        game.announce(title + ". " + Menu.item_speech(self.menu.current))

    def speech_text(self):
        return self.title + ". " + ". ".join(Menu.item_speech(i) for i in self.menu.items)

    def handle(self, event):
        res = self.menu.handle(event)
        if res:
            self.game.pop(self)
            if res[0] == "select":
                self.on_pick(res[1])
            elif self.on_cancel:
                self.on_cancel()

    def draw(self, surf):
        theme = self.game.theme
        dim(surf, theme)
        heading = self.game.fonts.get("heading")
        h = self.menu.needed_height() + heading.get_linesize() + 70
        panel = draw_panel(surf, (40, 40, SCREEN_W - 80, min(h + 140, SCREEN_H - HINT_SPACE - 60)), theme)
        draw_text(surf, self.title, heading, theme["text"], (panel.x + 24, panel.y + 18))
        top = panel.y + heading.get_linesize() + 34
        list_w = panel.w - 230
        self.menu.draw(surf, (panel.x + 24, top, list_w, panel.bottom - top - 20))
        m = self.game.state.party[self.menu.focus]
        img = sprites.mintling(m.species_id, 128)
        surf.blit(img, (panel.right - 180, top))
        draw_type_badge(surf, m.type, self.game.fonts.get("tiny"), (panel.right - 116, top + 138), "midtop")
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Choose")] +
                   ([("Esc", "Back")] if self.menu.cancel else []))


# =========================================================================== move replacement
class MoveReplaceScene(Scene):
    overlay = True

    def __init__(self, game, mon, new_move, on_done):
        super().__init__(game)
        self.mon, self.new_move, self.on_done = mon, new_move, on_done
        nm = MOVES[new_move]["name"]
        items = [MenuItem(f"Forget {MOVES[m]['name']}", m) for m in mon.moves]
        items.append(MenuItem(f"Don't learn {nm}", None))
        self.menu = Menu(game, items, cancel=False)
        self.text = (f"{mon.name} wants to learn {nm}, but already knows {MAX_MOVES} moves. "
                     f"Choose a move to forget, or keep the moves it has.")
        game.announce(self.speech_text())

    def speech_text(self):
        return self.text + " Options: " + ", ".join(i.label for i in self.menu.items)

    def handle(self, event):
        res = self.menu.handle(event)
        if res and res[0] == "select":
            self.game.pop(self)
            nm = MOVES[self.new_move]["name"]
            if res[1] is None:
                self.game.say([f"{self.mon.name} did not learn {nm}."], then=lambda: self.on_done(False))
            else:
                old = MOVES[res[1]]["name"]
                self.mon.replace_move(res[1], self.new_move)
                self.game.audio.play("level")
                self.game.say([f"{self.mon.name} forgot {old} and learned {nm}!"],
                              then=lambda: self.on_done(True))

    def draw(self, surf):
        theme = self.game.theme
        dim(surf, theme)
        body = self.game.fonts.get("body")
        small = self.game.fonts.get("small")
        panel = draw_panel(surf, (60, 40, SCREEN_W - 120, SCREEN_H - HINT_SPACE - 80), theme)
        y = panel.y + 20
        y += draw_wrapped(surf, self.text, body, theme["text"], (panel.x + 24, y, panel.w - 48, 0)) + 10
        nm = MOVES[self.new_move]
        y += draw_wrapped(surf, f"New move: {nm['name']} ({nm['type'] or 'No type'}). {nm['desc']}", small,
                          theme["muted"], (panel.x + 24, y, panel.w - 48, 0)) + 10
        self.menu.draw(surf, (panel.x + 24, y, panel.w - 48, panel.bottom - y - 20))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Choose")])


def mon_summary(mon):
    status = "fainted" if mon.fainted else f"{mon.hp} of {mon.max_hp} HP"
    extra = []
    if getattr(mon, "shielded", False):
        extra.append("shielded")
    for stat, label in (("atk", "Attack"), ("df", "Defence")):
        v = round(mon.stages[stat] * 100)
        if v:
            extra.append(f"{label} {'up' if v > 0 else 'down'} {abs(v)} percent")
    return f"{mon.name}, level {mon.level}, {mon.type} type, {status}" + (", " + ", ".join(extra) if extra else "")


# =========================================================================== type chart
# Laid out so that no two arrows cross: the starter triangle on the right,
# Scam and Security down the left.
CHART_POS = {"Savings": (0.62, 0.08), "Growth": (0.42, 0.62), "Debt": (0.9, 0.62),
             "Scam": (0.15, 0.32), "Security": (0.15, 0.9)}


def _arrow(surf, colour, a, b, gap=34, width=4):
    import math
    ax, ay = a
    bx, by = b
    ang = math.atan2(by - ay, bx - ax)
    sx, sy = ax + math.cos(ang) * gap, ay + math.sin(ang) * gap
    ex, ey = bx - math.cos(ang) * gap, by - math.sin(ang) * gap
    pygame.draw.line(surf, colour, (sx, sy), (ex, ey), width)
    head = [(ex, ey), (ex - math.cos(ang - 0.45) * 16, ey - math.sin(ang - 0.45) * 16),
            (ex - math.cos(ang + 0.45) * 16, ey - math.sin(ang + 0.45) * 16)]
    pygame.draw.polygon(surf, colour, head)
    return (sx + ex) / 2, (sy + ey) / 2


class TypeChartScene(Scene):
    """The five types with labelled arrows meaning 'strong against (2x)', plus the same chart as text."""
    overlay = True

    def __init__(self, game, then=None, highlight=None):
        super().__init__(game)
        self.then = then
        self.highlight = highlight      # (attacking type, defending type) to emphasise
        game.announce(self.speech_text())

    def speech_text(self):
        from ..data.types import chart_lines
        text = "Type chart. Arrows mean strong against, which is 2x damage. " + " ".join(chart_lines())
        if self.highlight:
            text += f" Your {self.highlight[0]} type is strong against {self.highlight[1]}."
        return text + " Press Enter to close."

    def handle(self, event):
        if action_of(event) in ("confirm", "back") or is_click(event):
            self.game.pop(self)
            if self.then:
                self.then()

    def draw(self, surf):
        from ..data.types import TYPES, STRONG_AGAINST, chart_lines
        theme = self.game.theme
        dim(surf, theme)
        panel = draw_panel(surf, (24, 16, SCREEN_W - 48, SCREEN_H - HINT_SPACE - 30), theme)
        heading = self.game.fonts.get("heading")
        small = self.game.fonts.get("small")
        tiny = self.game.fonts.get("tiny", scaled=False)
        draw_text(surf, "Type chart", heading, theme["text"], (panel.x + 24, panel.y + 14))
        draw_text(surf, "Arrow = strong against (2x damage)", small, theme["muted"],
                  (panel.right - 24, panel.y + 22), "topright")
        area = pygame.Rect(panel.x + 30, panel.y + 70, 430, panel.h - 100)
        pts = {t: (area.x + area.w * fx, area.y + area.h * fy) for t, (fx, fy) in CHART_POS.items()}
        for atk in TYPES:
            for dfn in STRONG_AGAINST[atk]:
                hl = self.highlight == (atk, dfn)
                colour = theme["focus"] if hl else theme["text"]
                if atk == dfn:      # Security vs Security: a loop
                    x, y = pts[atk]
                    loop = pygame.Rect(x + 34, y - 26, 52, 40)
                    pygame.draw.arc(surf, colour, loop, -2.4, 2.4, 4)
                    pygame.draw.polygon(surf, colour, [(x + 40, y + 8), (x + 30, y + 2), (x + 42, y - 2)])
                    draw_text(surf, "2x", tiny, colour, (loop.right + 4, loop.centery), "midleft")
                    continue
                mx, my = _arrow(surf, colour, pts[atk], pts[dfn], width=6 if hl else 4)
                lbl = tiny.render("2x", True, colour)
                r = lbl.get_rect(center=(mx, my)).inflate(8, 4)
                pygame.draw.rect(surf, theme["panel"], r, border_radius=4)
                surf.blit(lbl, lbl.get_rect(center=r.center))
        for t in TYPES:
            badge_rect = draw_type_badge(surf, t, self.game.fonts.get("small", scaled=False), pts[t], "center")
            if self.highlight and t in self.highlight:
                pygame.draw.rect(surf, theme["focus"], badge_rect.inflate(8, 8), 3, border_radius=10)
        x = area.right + 30
        y = area.y
        w = panel.right - 24 - x
        for line in chart_lines():
            y += draw_wrapped(surf, line, small, theme["text"], (x, y, w, 0)) + 8
        if self.highlight:
            y += 6
            draw_wrapped(surf, f"Your {self.highlight[0]} type is strong against {self.highlight[1]}!",
                         self.game.fonts.get("body"), theme["good"], (x, y, w, 0))
        draw_hints(surf, self.game, [("Enter", "Close")])


__all__ = ["Dialogue", "QuestionScene", "ConfirmScene", "PartyPicker", "MoveReplaceScene", "TypeChartScene",
           "HINT_SPACE", "mon_summary", "draw_hp_bar"]
