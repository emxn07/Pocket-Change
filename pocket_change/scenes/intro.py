"""The opening: guide pages, Professor Penny's introduction, names and starter choice."""
import math

import pygame

from ..config import SCREEN_W, SCREEN_H, FREE_CAPSULES
from ..core.mintling import Mintling
from ..data import world
from ..data.species import SPECIES, STARTERS, RIVAL_PICK
from ..game import Scene
from ..ui import sprites
from ..ui.widgets import (Menu, MenuItem, is_click, draw_panel, draw_text, draw_wrapped, draw_hints,
                          draw_type_badge, dim)
from .common import HINT_SPACE

PENNY = "Professor Penny"

GUIDE_PAGES = [
    ("Explore and talk to people", "Walk around Copperleaf Town. Talk to people and read signs: they explain "
     "money ideas you'll use later. Press Enter to talk and Esc to open the menu."),
    ("Learn and practise", "Every move in battle comes with a money question. There's no timer. Use PocketBank "
     "on your phone to check your money, borrowing and repayments, just like a real account."),
    ("Train Mintlings and reach the gym", "Battle trainers, befriend wild Mintlings and earn money. "
     "When you're ready, take on Professor Penny at the Copperleaf Gym!"),
]


def draw_lab_background(surf, hc=False):
    if hc:
        surf.fill((0, 0, 0))
        return
    surf.fill((232, 222, 200))
    pygame.draw.rect(surf, (196, 214, 226), (0, 0, SCREEN_W, 300))
    for x in range(0, SCREEN_W, 60):
        pygame.draw.line(surf, (176, 196, 210), (x, 0), (x, 300), 2)
    for i, x in enumerate(range(60, SCREEN_W, 220)):
        pygame.draw.rect(surf, (150, 110, 80), (x, 70, 150, 110))
        for sy in (100, 140):
            pygame.draw.line(surf, (110, 80, 60), (x, sy), (x + 150, sy), 4)
        for bx in range(x + 8, x + 140, 18):
            col = [(200, 80, 80), (80, 140, 200), (90, 170, 100), (230, 190, 70)][(bx // 18 + i) % 4]
            pygame.draw.rect(surf, col, (bx, 78 if bx % 3 else 82, 12, 20))
            pygame.draw.rect(surf, col, (bx + 2, 116, 10, 22))
    for y in range(300, SCREEN_H, 48):
        for x in range(0, SCREEN_W, 48):
            if (x // 48 + y // 48) % 2:
                pygame.draw.rect(surf, (222, 210, 186), (x, y, 48, 48))
    pygame.draw.line(surf, (150, 130, 110), (0, 300), (SCREEN_W, 300), 4)


# =========================================================================== guide pages
class GuideScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.page = 0
        self.menu = self._menu()
        game.announce(self.speech_text())

    def _menu(self):
        items = [MenuItem("Next" if self.page < len(GUIDE_PAGES) - 1 else "Meet Professor Penny", "next")]
        if self.page > 0:
            items.append(MenuItem("Back", "back"))
        return Menu(self.game, items, horizontal=True)

    def speech_text(self):
        title, text = GUIDE_PAGES[self.page]
        return f"Adventure guide, page {self.page + 1} of {len(GUIDE_PAGES)}. {title}. {text}"

    def handle(self, event):
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        if kind == "back" or value == "back":
            if self.page > 0:
                self.page -= 1
        elif self.page < len(GUIDE_PAGES) - 1:
            self.page += 1
        else:
            self.game.replace(IntroScene(self.game))
            return
        self.menu = self._menu()
        self.game.announce(self.speech_text())

    def draw(self, surf):
        theme = self.game.theme
        surf.fill(theme["bg"])
        title, text = GUIDE_PAGES[self.page]
        panel = draw_panel(surf, (60, 40, SCREEN_W - 120, SCREEN_H - HINT_SPACE - 80), theme)
        small = self.game.fonts.get("small")
        draw_text(surf, f"Adventure guide  {self.page + 1} / {len(GUIDE_PAGES)}", small, theme["muted"],
                  (panel.x + 30, panel.y + 22))
        # illustration
        art = pygame.Rect(panel.x + 30, panel.y + 60, panel.w - 60, 170)
        pygame.draw.rect(surf, (150, 200, 120) if not self.game.settings.high_contrast else (20, 20, 20), art,
                         border_radius=10)
        cx = art.centerx
        bob = int(math.sin(self.game.anim_time * 3) * 4)
        if self.page == 0:
            surf.blit(sprites.person(sprites.PLAYER_LOOK, "right", 0, hat=(214, 64, 56)), (cx - 120, art.y + 70))
            surf.blit(sprites.person(world.NPCS[0]["look"], "left", 0), (cx - 40, art.y + 70))
            surf.blit(pygame.transform.scale(sprites.draw_tile("S", 0, 0), (48, 48)), (cx + 60, art.y + 70))
            pygame.draw.rect(surf, (255, 255, 255), (cx - 70, art.y + 30 + bob, 50, 30), border_radius=8)
            draw_text(surf, "Hi!", small, (30, 30, 40), (cx - 45, art.y + 45 + bob), "center")
        elif self.page == 1:
            phone = pygame.Rect(cx - 150, art.y + 15, 90, 145)
            pygame.draw.rect(surf, (40, 44, 60), phone, border_radius=12)
            pygame.draw.rect(surf, (240, 246, 250), phone.inflate(-12, -24), border_radius=4)
            draw_text(surf, "£", self.game.fonts.get("heading", scaled=False), (40, 120, 70), phone.center, "center")
            card = pygame.Rect(cx + 10, art.y + 25 + bob, 170, 120)
            pygame.draw.rect(surf, (255, 250, 236), card, border_radius=10)
            pygame.draw.rect(surf, (44, 50, 78), card, 3, border_radius=10)
            draw_text(surf, "?", self.game.fonts.get("title", scaled=False), (214, 160, 30), card.center, "center")
        else:
            for i, sp in enumerate(STARTERS):
                surf.blit(sprites.mintling(sp, 96), (cx - 200 + i * 110, art.y + 50 + (bob if i == 1 else 0)))
            surf.blit(pygame.transform.scale_by(sprites.building(world.BUILDINGS[0]), 1.2), (cx + 150, art.y + 40))
        y = art.bottom + 24
        draw_text(surf, title, self.game.fonts.get("heading"), theme["text"], (panel.x + 30, y))
        y += self.game.fonts.get("heading").get_linesize() + 10
        draw_wrapped(surf, text, self.game.fonts.get("body"), theme["text"], (panel.x + 30, y, panel.w - 60, 0))
        mh = self.menu.needed_height()
        self.menu.draw(surf, (panel.x + 30, panel.bottom - mh - 20, panel.w - 60, mh))
        draw_hints(surf, self.game, [("Left/Right", "Move"), ("Enter", "Select")])


# =========================================================================== intro director
class IntroScene(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.show = {"coincub": False, "rival": False}
        self.i = 0
        self.ready = True
        st = game.state
        self.steps = [
            lambda: self.talk(world.PENNY_INTRO[:3]),
            lambda: (self.set(coincub=True), self.talk(world.PENNY_INTRO[3:5])),
            lambda: (self.set(coincub=False), self.talk(world.PENNY_INTRO[5:])),
            lambda: game.push(NameEntryScene(game, "What's your name?", "", "So your name is {name}?",
                                             lambda n: (setattr(st, "player_name", n), self.advance()))),
            lambda: self.talk(world.PENNY_AFTER_NAME),
            lambda: (self.set(rival=True), self.talk(world.RIVAL_INTRO)),
            lambda: game.push(NameEntryScene(game, "What's your rival's name?", "Finn",
                                             "So your rival's name is {name}?",
                                             lambda n: (setattr(st, "rival_name", n), self.advance()))),
            lambda: self.talk(world.PENNY_AFTER_RIVAL),
            lambda: (self.set(rival=False), game.push(StarterScene(game, self.on_starter))),
            lambda: self.after_starter(),
            lambda: self.talk(world.TYPE_LESSON),
            lambda: self.type_chart(),
            lambda: self.talk(world.TYPE_LESSON_AFTER + [self.matchup_line()]),
            lambda: self.rival_battle(),
            lambda: self.after_rival_battle(),
            lambda: self.finish(),
        ]
        self.outcome = None

    def set(self, **kw):
        self.show.update(kw)

    def advance(self, *_):
        self.ready = True

    def talk(self, lines, speaker=PENNY):
        self.game.say(lines, speaker=speaker, then=self.advance)

    def on_starter(self, species_id):
        st = self.game.state
        st.starter = species_id
        st.rival_species = RIVAL_PICK[species_id]
        st.add_mintling(Mintling(species_id, 5))
        self.advance()

    def after_starter(self):
        st = self.game.state
        rival_mon = SPECIES[st.rival_species]
        self.set(rival=True)
        self.game.say([(st.rival_name, f"Then I'll take {rival_mon['name']}! Let's battle right now!"),
                       (PENNY, f"{rival_mon['name']} is a {rival_mon['type']} type. Hmm, {st.rival_name}, "
                               "you might regret that choice...")],
                      then=self.advance)

    def type_chart(self):
        from .common import TypeChartScene
        st = self.game.state
        pair = (SPECIES[st.starter]["type"], SPECIES[st.rival_species]["type"])
        self.game.push(TypeChartScene(self.game, then=self.advance, highlight=pair))

    def matchup_line(self):
        st = self.game.state
        me, them = SPECIES[st.starter], SPECIES[st.rival_species]
        return (f"Your {me['name']} is {me['type']}, and {me['type']} is strong against {them['type']}. "
                f"So {me['name']}'s {me['type']} moves do 2x damage to {them['name']}!")

    def rival_battle(self):
        from ..core.battle import make_team
        from .battle_scene import BattleScene
        st = self.game.state
        trainer = {"name": st.rival_name, "reward": world.RIVAL_REWARD, "id": "rival", "xp": "rival",
                   "reward_label": f"Battle reward: {st.rival_name}"}
        battle = self.game.new_battle(make_team([(st.rival_species, 5)]), trainer)

        def ended(outcome):
            self.outcome = outcome
            self.advance()

        self.game.push(BattleScene(self.game, battle, ended, tutorial=world.FIRST_TURN_GUIDE))

    def after_rival_battle(self):
        st = self.game.state
        st.flags |= {"rival_done", "trainer:rival"}
        st.heal_party()
        if self.outcome == "win":
            rival_lines = ["Aw, you won! Your type advantage really paid off.", "I'll train hard. See you at the gym!"]
        else:
            # The introductory rival battle never costs money.
            rival_lines = ["Yes! I won! Don't worry, Grandma says losing is how you learn.", "See you at the gym!"]
        st.inventory["capsule"] += FREE_CAPSULES
        money = st.account.money
        penny = [line.replace("{money}", str(money)) for line in world.PENNY_AFTER_RIVAL_BATTLE]
        self.game.say([(st.rival_name, line) for line in rival_lines] + [(PENNY, line) for line in penny],
                      then=self.advance)

    def finish(self):
        from .overworld import Overworld
        st = self.game.state
        st.flags |= {"intro_done", "got_starter", "capsules_given"}
        st.pos = list(world.START_POS)
        st.facing = "down"
        self.game.reset(Overworld(self.game))
        self.game.toast("Tip: press Esc for the menu, Enter to talk.", 5)

    def update(self, dt):
        if self.ready and self.game.top is self and self.i < len(self.steps):
            self.ready = False
            step = self.steps[self.i]
            self.i += 1
            step()

    def draw(self, surf):
        draw_lab_background(surf, self.game.settings.high_contrast)
        penny = sprites.portrait("penny", 300)
        surf.blit(penny, (140, 70))
        bob = int(math.sin(self.game.anim_time * 4) * 4)
        if self.show["coincub"]:
            surf.blit(sprites.mintling("coincub", 160), (560, 170 + bob))
        if self.show["rival"]:
            surf.blit(sprites.portrait("rival", 280), (560, 90))


# =========================================================================== name entry
ALLOWED = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -'")


class NameEntryScene(Scene):
    overlay = True
    text_input = True
    MAX = 12

    def __init__(self, game, prompt, default, confirm_text, on_done):
        super().__init__(game)
        self.prompt = prompt
        self.name = default
        self.confirm_text = confirm_text
        self.on_done = on_done
        self.error = ""
        self.done_rect = None
        game.announce(self.speech_text())

    def speech_text(self):
        current = self.name or "empty"
        return f"{self.prompt} Type a name, then press Enter. Current name: {current}."

    def _confirm(self):
        name = self.name.strip()
        if not name:
            self.error = "Please type a name first."
            self.game.audio.play("bump")
            self.game.announce(self.error)
            return
        self.name = name
        self.game.ask(self.confirm_text.format(name=name), [("Yes", True), ("No", False)], self._answer)

    def _answer(self, yes):
        if yes:
            self.game.pop(self)
            self.on_done(self.name)
        else:
            self.game.announce("Okay, edit the name. " + self.speech_text())

    def handle(self, event):
        if event.type == pygame.TEXTINPUT:
            for ch in event.text:
                if ch in ALLOWED and len(self.name) < self.MAX:
                    self.name += ch
                    self.error = ""
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.name = self.name[:-1]
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._confirm()
        elif is_click(event) and self.done_rect and self.done_rect.collidepoint(event.pos):
            self._confirm()

    def draw(self, surf):
        theme = self.game.theme
        dim(surf, theme)
        heading = self.game.fonts.get("heading")
        body = self.game.fonts.get("body")
        small = self.game.fonts.get("small")
        panel = draw_panel(surf, (110, 120, SCREEN_W - 220, 330), theme)
        draw_text(surf, self.prompt, heading, theme["text"], (panel.centerx, panel.y + 30), "midtop")
        field = pygame.Rect(panel.x + 60, panel.y + 100, panel.w - 120, body.get_linesize() + 30)
        pygame.draw.rect(surf, theme["panel_alt"], field, border_radius=8)
        pygame.draw.rect(surf, theme["focus"], field, 4, border_radius=8)
        img = heading.render(self.name, True, theme["text"])
        surf.blit(img, (field.x + 16, field.centery - img.get_height() // 2))
        if int(self.game.anim_time * 2) % 2 == 0:
            x = field.x + 18 + img.get_width()
            pygame.draw.line(surf, theme["text"], (x, field.y + 10), (x, field.bottom - 10), 3)
        draw_text(surf, f"{len(self.name)}/{self.MAX} characters", small, theme["muted"],
                  (field.right, field.bottom + 6), "topright")
        if self.error:
            draw_text(surf, "! " + self.error, small, theme["bad"], (field.x, field.bottom + 6))
        btn_img = body.render("Done (Enter)", True, theme["text"])
        self.done_rect = btn_img.get_rect(midtop=(panel.centerx, field.bottom + 50)).inflate(40, 20)
        pygame.draw.rect(surf, theme["focus_bg"], self.done_rect, border_radius=8)
        pygame.draw.rect(surf, theme["focus"], self.done_rect, 3, border_radius=8)
        surf.blit(btn_img, btn_img.get_rect(center=self.done_rect.center))
        draw_hints(surf, self.game, [("Type", "Name"), ("Backspace", "Delete"), ("Enter", "Confirm"),
                                     ("F5", "Read"), ("F6", "Stop")])


# =========================================================================== starter choice
class StarterScene(Scene):
    overlay = True

    def __init__(self, game, on_chosen):
        super().__init__(game)
        self.on_chosen = on_chosen
        items = [MenuItem(SPECIES[s]["name"], s, speech=self._describe(s)) for s in STARTERS]
        self.menu = Menu(game, items, horizontal=True, cancel=False)
        game.announce("Choose your first Mintling. " + self._describe(STARTERS[0]))

    @staticmethod
    def _describe(s):
        sp = SPECIES[s]
        return f"{sp['name']}, the {sp['type']} type. {sp['desc']}"

    def speech_text(self):
        return "Choose your first Mintling. " + self._describe(self.menu.current.value)

    def handle(self, event):
        res = self.menu.handle(event)
        if res and res[0] == "select":
            s = res[1]
            sp = SPECIES[s]
            self.game.ask(f"{sp['name']}, the {sp['type']}-type Mintling. Will you choose it?",
                          [("Yes", True), ("No", False)],
                          lambda yes: yes and self._chosen(s), speaker=PENNY)

    def _chosen(self, s):
        self.game.pop(self)
        self.game.audio.play("level")
        self.on_chosen(s)

    def draw(self, surf):
        theme = self.game.theme
        dim(surf, theme)
        heading = self.game.fonts.get("heading")
        small = self.game.fonts.get("small")
        draw_text(surf, "Choose your first Mintling", heading, theme["on_dark"], (SCREEN_W // 2, 24), "midtop")
        card_w, gap = 280, 20
        x0 = (SCREEN_W - (3 * card_w + 2 * gap)) // 2
        top = 80
        rects = []
        for i, s in enumerate(STARTERS):
            sp = SPECIES[s]
            r = pygame.Rect(x0 + i * (card_w + gap), top, card_w, SCREEN_H - HINT_SPACE - top - 90)
            focused = self.menu.focus == i
            draw_panel(surf, r, theme, border=theme["focus"] if focused else theme["border"],
                       width=5 if focused else 2)
            bob = int(math.sin(self.game.anim_time * 4) * 5) if focused else 0
            img = sprites.mintling(s, 160)
            surf.blit(img, img.get_rect(midtop=(r.centerx, r.y + 12 + bob)))
            y = r.y + 180
            draw_text(surf, sp["name"], heading, theme["text"], (r.centerx, y), "midtop")
            y += heading.get_linesize() + 4
            draw_type_badge(surf, sp["type"], self.game.fonts.get("tiny"), (r.centerx, y), "midtop")
            y += 40
            draw_wrapped(surf, sp["desc"], small, theme["text"], (r.x + 16, y, r.w - 32, 0), 2)
            rects.append((i, r))
        mh = self.menu.needed_height()
        self.menu.draw(surf, (x0, SCREEN_H - HINT_SPACE - mh - 16, 3 * card_w + 2 * gap, mh))
        self.menu.rects += rects     # the cards are clickable too
        draw_hints(surf, self.game, [("Left/Right", "Choose"), ("Enter", "Select")])
