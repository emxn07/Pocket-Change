"""Battle screen. Plays back events from core.battle and gathers the player's choices."""
from collections import deque
import math

import pygame

from ..config import SCREEN_W, SCREEN_H
from ..core.mintling import xp_to_next
from ..data.items import ITEMS
from ..data.moves import MOVES
from ..data.questions import TOPIC_NAMES
from ..data.types import effectiveness
from ..game import Scene
from ..ui import sprites
from ..ui.widgets import (Menu, MenuItem, action_of, is_click, draw_panel, draw_text, draw_wrapped, draw_hints,
                          draw_hp_bar, draw_type_badge)
from .common import QuestionScene, PartyPicker, MoveReplaceScene, HINT_SPACE, mon_summary

PANEL_H = 200
KIND_LABEL = {"damage": "Attack", "heal": "Heal", "shield": "Shield", "buff": "Raise stat", "debuff": "Lower stat"}


def status_text(mon):
    """Shield and stat changes as text (never colour alone)."""
    parts = ["Shield"] if mon.shielded else []
    for stat, label in (("atk", "Att"), ("df", "Def")):
        v = round(mon.stages[stat] * 100)
        if v:
            parts.append(f"{label} {'+' if v > 0 else ''}{v}%")
    return "  ".join(parts)
ENEMY_POS = (690, 205)     # sprite centre-bottom
PLAYER_POS = (230, 395)


class BattleScene(Scene):
    def __init__(self, game, battle, on_end, tutorial=None):
        super().__init__(game)
        self.b = battle
        self.tutorial = tutorial        # Penny's first-turn guidance (intro rival battle)
        self.on_end = on_end
        self.queue = deque(battle.opening_events())
        self.shown = {"player": None, "enemy": battle.enemy if battle.wild else None}
        self.disp_hp = {m.uid: m.hp for m in battle.party + battle.enemies}
        self.hp_anim = None
        self.flash = {"player": 0.0, "enemy": 0.0}
        self.faint = {"player": 0.0, "enemy": 0.0}
        self.fainted = {"player": False, "enemy": False}
        self.capsule = None
        self.message = ""
        self.waiting = False
        self.mode = "events"
        self.menu = None
        self.intro = 0.7 if game.motion else 0.0   # the white/black flash is skipped with Reduce motion
        self.ended = False
        self.gym = (battle.trainer or {}).get("id") == "penny"
        game.audio.play("encounter")

    # ------------------------------------------------------------------ event playback
    def _process(self, ev):
        kind = ev[0]
        if kind == "msg":
            self.message = ev[1]
            self.waiting = True
            self.game.announce(ev[1])
        elif kind == "sound":
            self.game.audio.play(ev[1])
        elif kind == "hp":
            mon, value = ev[1], ev[2]
            start = self.disp_hp.get(mon.uid, value)
            if start != value:
                self.hp_anim = [mon, start, value, 0.0]
                if value > start:
                    self.game.audio.play("heal")
            self.disp_hp[mon.uid] = value if start == value else start
        elif kind == "hit":
            self.flash[ev[1]] = 0.45 if self.game.motion else 0.0
            self.game.audio.play("hit")
        elif kind == "send":
            side, mon = ev[1], ev[2]
            self.shown[side] = mon
            self.disp_hp[mon.uid] = mon.hp
            self.fainted[side] = False
            self.faint[side] = 0.0
        elif kind == "faint":
            self.fainted[ev[1]] = True
            self.faint[ev[1]] = 0.5
        elif kind == "shake":
            self.capsule = {"n": ev[1], "t": 0.7, "caught": False}
            self.game.audio.play("shake")
        elif kind == "caught":
            self.capsule = {"n": 3, "t": 0.6, "caught": True}
            self.game.audio.play("catch")
        elif kind == "escape":
            self.capsule = None
        elif kind == "learn_full":
            self.game.push(MoveReplaceScene(self.game, ev[1], ev[2], lambda _: None))

    def _run(self, events):
        self.queue.extend(events)
        self.mode = "events"
        self.menu = None

    def _events_done(self):
        b = self.b
        if b.outcome:
            if not self.ended:
                self.ended = True
                b.finish()
                self.game.pop(self)
                self.on_end(b.outcome)
            return
        if b.need_switch:
            self.mode = "wait"
            self.game.push(PartyPicker(self.game, "Choose a Mintling to send out", self._forced_switch,
                                       check=lambda m: "Fainted" if m.fainted else None, cancel=False))
            return
        self._show_actions()

    def _forced_switch(self, index):
        self._run(self.b.switch(index, forced=True))

    # ------------------------------------------------------------------ menus
    def _show_actions(self):
        self.mode = "action"
        self.message = f"What will {self.b.player.name} do?"
        self.menu = Menu(self.game, [
            MenuItem("Fight", "fight"), MenuItem("Items", "items"),
            MenuItem("Mintlings", "mintlings"),
            MenuItem("Run", "run", enabled=self.b.wild, note=None if self.b.wild else "Trainer battle"),
        ], columns=2, cancel=False)
        if self.tutorial:
            lines, self.tutorial = self.tutorial, None
            self.game.say(lines, speaker="Professor Penny", then=lambda: self.game.announce(self.speech_text()))
            return
        self.game.announce(self.speech_text())

    def _show_moves(self):
        self.mode = "moves"
        p, e = self.b.player, self.b.enemy
        items = []
        for mid in p.moves:
            m = MOVES[mid]
            note = f"{m['type'] or 'No type'}" if m["kind"] == "damage" else KIND_LABEL[m["kind"]]
            speech = f"{m['name']}, {m['type'] or 'no'} type, {KIND_LABEL[m['kind']]}. {m['desc']}"
            if m["kind"] == "damage":
                note += f" {m['power']}"
                speech += f", power {m['power']}"
                if effectiveness(m["type"], e.type) > 1:
                    speech += ", super effective against the opponent"
            items.append(MenuItem(m["name"], mid, note=note, speech=speech))
        items.append(MenuItem("Back", "back"))
        self.menu = Menu(self.game, items, columns=2)
        self.message = "Choose a move. You'll answer a question to use it."
        self.game.announce(self.message + " " + Menu.item_speech(self.menu.current))

    def _show_items(self):
        inv = self.game.state.inventory
        items = [MenuItem(f"{ITEMS[k]['name']} x{n}", k, speech=f"{ITEMS[k]['name']}, you have {n}. {ITEMS[k]['desc']}")
                 for k, n in inv.items() if n > 0]
        if not items:
            self.game.toast("You don't have any items. PoketMart sells them.")
            return
        items.append(MenuItem("Back", "back"))
        self.mode = "items"
        self.menu = Menu(self.game, items, columns=2)
        self.message = "Choose an item. Using one takes your turn."
        self.game.announce(self.message + " " + Menu.item_speech(self.menu.current))

    def handle(self, event):
        if self.intro > 0:
            return
        if self.mode == "events":
            if self.waiting and (action_of(event) in ("confirm", "back") or is_click(event)):
                self.waiting = False
                self.game.audio.play("move")
            return
        if not self.menu:
            return
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        if kind == "back" or value == "back":
            if self.mode != "action":
                self._show_actions()
            return
        if self.mode == "action":
            self._action(value)
        elif self.mode == "moves":
            self._choose_move(value)
        elif self.mode == "items":
            self._choose_item(value)

    def _action(self, value):
        b = self.b
        if value == "fight":
            self._show_moves()
        elif value == "items":
            self._show_items()
        elif value == "mintlings":
            def check(m):
                if m.fainted:
                    return "Fainted"
                if m is b.player:
                    return "Already battling"
                return None
            self.game.push(PartyPicker(self.game, "Switch to which Mintling? Switching uses your turn.",
                                       lambda i: self._run(b.switch(i)), check=check))
        elif value == "run":
            self._run(b.run())

    def _choose_move(self, mid):
        p = self.b.player
        move = MOVES[mid]
        q = self.game.quiz.draw(self.b.question_topic(mid), self.b.question_level())
        header = f"{p.name} wants to use {move['name']}"
        self.game.push(QuestionScene(self.game, q, header,
                                     lambda correct: self._run(self.b.player_move(mid, correct)),
                                     intro="Answer correctly to make the move work. Esc to choose again.",
                                     on_cancel=self._show_moves))

    def _choose_item(self, item_id):
        b = self.b
        item = ITEMS[item_id]
        if item["capsule"]:
            problem = b.can_use_item(item_id, b.enemy)
            if problem:
                self.game.toast(problem)
                return
            e = b.enemy
            q = self.game.quiz.draw(None, 1)
            first = "first_catch" not in self.game.state.flags
            intro = ("Your first befriending is certain with a correct answer!" if first else
                     "A correct answer improves your chance, and lower HP helps too.")
            self.game.push(QuestionScene(self.game, q, f"Befriend {e.name} with a Mint Capsule",
                                         lambda correct: self._run(b.attempt_catch(correct)), intro=intro,
                                         on_cancel=self._show_items))
            return

        def pick(i):
            mon = self.game.state.party[i]
            self._run(b.use_item(item_id, mon))

        self.game.push(PartyPicker(self.game, f"Use {item['name']} on which Mintling?", pick,
                                   check=lambda m: b.can_use_item(item_id, m)))

    # ------------------------------------------------------------------ update
    def update(self, dt):
        if self.intro > 0:
            self.intro -= dt
            return
        for side in ("player", "enemy"):
            self.flash[side] = max(0.0, self.flash[side] - dt)
            self.faint[side] = max(0.0, self.faint[side] - dt)
        if self.hp_anim:
            mon, start, end, t = self.hp_anim
            t = min(1.0, t + dt / 0.5) if self.game.motion else 1.0
            self.disp_hp[mon.uid] = start + (end - start) * t
            self.hp_anim[3] = t
            if t >= 1.0:
                self.hp_anim = None
            return
        if self.capsule and self.capsule["t"] > 0:
            self.capsule["t"] -= dt
            return
        if self.mode != "events" or self.waiting or self.game.top is not self:
            return
        if self.queue:
            self._process(self.queue.popleft())
        else:
            self._events_done()

    def speech_text(self):
        status = []
        if self.shown["player"]:
            status.append("Your " + mon_summary(self.shown["player"]))
        if self.shown["enemy"]:
            status.append("Opponent " + mon_summary(self.shown["enemy"]))
        text = self.message
        if self.menu and self.mode != "events":
            text += " Options: " + ", ".join(Menu.item_speech(i) for i in self.menu.items)
        return text + " " + ". ".join(status)

    # ------------------------------------------------------------------ drawing
    def _draw_background(self, surf):
        hc = self.game.settings.high_contrast
        if hc:
            surf.fill((0, 0, 0))
            pygame.draw.ellipse(surf, (255, 255, 255), (ENEMY_POS[0] - 120, ENEMY_POS[1] - 20, 240, 50), 2)
            pygame.draw.ellipse(surf, (255, 255, 255), (PLAYER_POS[0] - 150, PLAYER_POS[1] - 25, 300, 60), 2)
            return
        if self.gym:
            surf.fill((92, 70, 64))
            for y in range(0, SCREEN_H, 40):
                pygame.draw.line(surf, (110, 86, 76), (0, y), (SCREEN_W, y), 2)
            pygame.draw.rect(surf, (176, 64, 56), (0, 0, SCREEN_W, 60))
            for x in range(40, SCREEN_W, 160):
                pygame.draw.circle(surf, (240, 190, 50), (x, 30), 16)
            pad1, pad2 = (150, 120, 100), (140, 110, 90)
        else:
            top, bottom = (150, 206, 240), (196, 232, 196)
            for y in range(0, SCREEN_H):
                f = y / SCREEN_H
                c = tuple(int(top[i] + (bottom[i] - top[i]) * f) for i in range(3))
                pygame.draw.line(surf, c, (0, y), (SCREEN_W, y))
            pygame.draw.rect(surf, (140, 200, 110), (0, 250, SCREEN_W, SCREEN_H - 250))
            pad1, pad2 = (110, 176, 86), (100, 166, 80)
        pygame.draw.ellipse(surf, pad1, (ENEMY_POS[0] - 130, ENEMY_POS[1] - 25, 260, 60))
        pygame.draw.ellipse(surf, pad2, (PLAYER_POS[0] - 160, PLAYER_POS[1] - 30, 320, 70))

    def _draw_mon(self, surf, side, size, pos):
        mon = self.shown[side]
        if mon is None:
            return
        if side == "enemy" and self.capsule:
            c = self.capsule
            img = sprites.capsule(size=64)
            wob = math.sin((0.7 - c["t"]) * 25) * 14 if c["t"] > 0 and not c["caught"] and self.game.motion else 0
            img = pygame.transform.rotate(img, wob)
            r = img.get_rect(midbottom=pos)
            surf.blit(img, r)
            if c["caught"]:
                for i in range(6):
                    a = i * math.pi / 3 + self.game.anim_time * 3
                    pygame.draw.circle(surf, (255, 240, 140), (r.centerx + int(math.cos(a) * 50),
                                                              r.centery + int(math.sin(a) * 40)), 4)
            return
        if self.fainted[side]:
            if self.faint[side] <= 0:
                return
            k = self.faint[side] / 0.5
            img = sprites.mintling(mon.species_id, size, flip=side == "player").copy()
            img.set_alpha(int(255 * k))
            surf.blit(img, img.get_rect(midbottom=(pos[0], pos[1] + int((1 - k) * 60))))
            return
        if self.flash[side] > 0 and int(self.flash[side] * 16) % 2 == 0:
            return
        bob = int(math.sin(self.game.anim_time * 3 + (0 if side == "player" else 1.5)) * 3)
        img = sprites.mintling(mon.species_id, size, flip=side == "player")
        surf.blit(img, img.get_rect(midbottom=(pos[0], pos[1] + bob)))

    def _info_box(self, surf, side, rect):
        mon = self.shown[side]
        if mon is None:
            return
        theme = self.game.theme
        body = self.game.fonts.get("body")
        tiny = self.game.fonts.get("tiny")
        small = self.game.fonts.get("small")
        r = draw_panel(surf, rect, theme)
        x, y = r.x + 16, r.y + 10
        draw_text(surf, mon.name, body, theme["text"], (x, y))
        draw_text(surf, f"Lv {mon.level}", body, theme["text"], (r.right - 16, y), "topright")
        y += body.get_linesize() + 2
        badge = draw_type_badge(surf, mon.type, tiny, (x, y))
        status = status_text(mon)
        if status:
            name_w = body.size(mon.name)[0]
            draw_text(surf, status, tiny, theme["text"], (x + name_w + 10, r.y + 10 + body.get_linesize() // 2),
                      "midleft")
        bar = pygame.Rect(badge.right + 10, y + 2, 0, 16)
        bar.w = r.right - 16 - bar.x
        draw_hp_bar(surf, bar, self.disp_hp.get(mon.uid, mon.hp), mon.max_hp, theme, small)
        if side == "player":
            y = bar.bottom + small.get_linesize() + 6
            need = xp_to_next(mon.level)
            label = f"XP {mon.xp}/{need}"
            lw = tiny.size(label)[0]
            draw_text(surf, label, tiny, theme["muted"], (x, y))
            xr = pygame.Rect(x + lw + 12, y + tiny.get_linesize() // 2 - 4, r.right - 16 - (x + lw + 12), 8)
            pygame.draw.rect(surf, theme["hp_bg"], xr, border_radius=3)
            pygame.draw.rect(surf, (80, 150, 230), (xr.x, xr.y, int(xr.w * mon.xp / need), xr.h), border_radius=3)

    def draw(self, surf):
        theme = self.game.theme
        self._draw_background(surf)
        self._draw_mon(surf, "enemy", 176, ENEMY_POS)
        self._draw_mon(surf, "player", 208, PLAYER_POS)
        body = self.game.fonts.get("body")
        line = body.get_linesize()
        self._info_box(surf, "enemy", (24, 20, 400, line * 2 + 44))
        ph = line * 2 + 44 + self.game.fonts.get("tiny").get_linesize() + 10
        self._info_box(surf, "player", (SCREEN_W - 424, SCREEN_H - HINT_SPACE - PANEL_H - ph - 16, 400, ph))
        panel = draw_panel(surf, (12, SCREEN_H - HINT_SPACE - PANEL_H - 4, SCREEN_W - 24, PANEL_H), theme)
        inner = panel.inflate(-32, -28)
        small = self.game.fonts.get("small")
        if self.mode in ("events", "wait") or not self.menu:
            draw_wrapped(surf, self.message, body, theme["text"], inner)
            if self.waiting:
                bob = int(abs(((self.game.anim_time * 3) % 2) - 1) * 4)
                x, y = inner.right - 14, inner.bottom - 12 + bob
                pygame.draw.polygon(surf, theme["accent"], [(x, y), (x + 14, y), (x + 7, y + 9)])
            draw_hints(surf, self.game, [("Enter", "Continue")])
        elif self.mode == "action":
            left = pygame.Rect(inner.x, inner.y, inner.w * 0.42, inner.h)
            draw_wrapped(surf, self.message, body, theme["text"], left)
            self.menu.draw(surf, (inner.x + inner.w * 0.45, inner.y, inner.w * 0.55, inner.h))
            draw_hints(surf, self.game, [("Arrows", "Move"), ("Enter", "Choose")])
        else:
            menu_w = inner.w * 0.6
            self.menu.draw(surf, (inner.x, inner.y, menu_w, inner.h))
            info = pygame.Rect(inner.x + menu_w + 16, inner.y, inner.w - menu_w - 16, inner.h)
            pygame.draw.line(surf, theme["border"], (info.x - 8, info.y), (info.x - 8, info.bottom), 2)
            cur = self.menu.current.value
            if self.mode == "moves" and cur in MOVES:
                m = MOVES[cur]
                y = info.y
                badge = draw_type_badge(surf, m["type"], self.game.fonts.get("tiny"), (info.x, y))
                kind = f"Power {m['power']}" if m["kind"] == "damage" else KIND_LABEL[m["kind"]]
                draw_text(surf, kind, small, theme["text"], (badge.right + 10, badge.centery), "midleft")
                y = badge.bottom + 6
                if m["kind"] == "damage" and effectiveness(m["type"], self.b.enemy.type) > 1:
                    y += draw_wrapped(surf, f"Super effective against {self.b.enemy.type}!", small,
                                      theme["good"], (info.x, y, info.w, 0))
                y += draw_wrapped(surf, m["desc"], small, theme["text"], (info.x, y, info.w, 0))
                draw_wrapped(surf, f"Question topic: {TOPIC_NAMES[m['topic']]}", small, theme["muted"],
                             (info.x, y + 2, info.w, 0))
            elif self.mode == "items" and cur in ITEMS:
                draw_wrapped(surf, ITEMS[cur]["desc"], small, theme["text"], info)
            else:
                draw_wrapped(surf, "Return to the main battle options.", small, theme["muted"], info)
            draw_hints(surf, self.game, [("Arrows", "Move"), ("Enter", "Choose"), ("Esc", "Back")])
        if self.intro > 0:
            k = self.intro / 0.7
            shade = pygame.Surface((SCREEN_W, SCREEN_H))
            shade.fill((255, 255, 255) if int(k * 6) % 2 else (0, 0, 0))
            shade.set_alpha(int(255 * k))
            surf.blit(shade, (0, 0))
