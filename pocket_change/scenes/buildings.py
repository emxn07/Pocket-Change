"""Inside buildings, plus the town Task Board."""
import math

import pygame

from ..config import SCREEN_W, SCREEN_H, PARTY_MAX, SHOP_NAME, CLINIC_NAME, BADGE_NAME
from ..core.battle import make_team
from ..data import world
from ..game import Scene
from ..ui import sprites
from ..ui.widgets import Menu, MenuItem, draw_panel, draw_text, draw_hints, draw_header, draw_wrapped
from .common import QuestionScene, PartyPicker, HINT_SPACE, mon_summary
from .tasks import run_npc_task

PENNY = "Professor Penny"
CARETAKER = "Caretaker Mo"
TASK_REWARD = 10

ROOMS = {
    "lab": dict(title="Professor Penny's Lab", floor=(226, 220, 200), wall=(196, 214, 226), host="penny"),
    "clinic": dict(title=CLINIC_NAME, floor=(240, 226, 230), wall=(250, 240, 244),
                   host=((220, 90, 120), (240, 220, 120), (240, 200, 170))),
    "mart": dict(title=SHOP_NAME, floor=(210, 226, 214), wall=(232, 244, 236),
                 host=((60, 150, 140), (40, 30, 30), (170, 120, 90))),
    "gym": dict(title="Copperleaf Gym", floor=(150, 110, 96), wall=(176, 64, 56), host="penny"),
}

ROOM_INFO = {
    "lab": "Penny can explain credit limits, interest and repayments before you meet them in battle.",
    "clinic": f"Free, unlimited healing for your whole party, including fainted Mintlings. Mintlings that don't "
              f"fit in your party of {PARTY_MAX} are kept in storage here.",
    "mart": "Potions, Super Potions, Revives and Mint Capsules. Your money and basket total are always shown.",
    "gym": "Penny's challenge tests budgeting, borrowing, repaying and staying safe. No timer, ever.",
}


class InteriorScene(Scene):
    def __init__(self, game, building, on_exit, world_scene):
        super().__init__(game)
        self.b = building
        self.id = building["id"]
        self.on_exit = on_exit
        self.world = world_scene
        self.room = ROOMS[self.id]
        self.build()
        game.announce(self.speech_text())

    @property
    def st(self):
        return self.game.state

    def build(self):
        st = self.st
        if self.id == "lab":
            items = [MenuItem("Ask Penny about money", "lessons"), MenuItem("Talk to Penny", "talk")]
        elif self.id == "clinic":
            items = [MenuItem("Heal my Mintlings (free)", "heal"),
                     MenuItem("Mintling storage", "storage", note=f"{len(st.storage)} stored")]
        elif self.id == "mart":
            done = "task:budget" in st.flags
            items = [MenuItem("Shop", "shop"),
                     MenuItem("Talk to the shopkeeper", "task", note="Task done" if done else "Budgeting task")]
        else:
            ready = self.world.gym_ready()
            if st.gym_beaten:
                gold = "gold_badge" in st.flags
                items = [MenuItem("Rematch Penny", "rematch", note=f"Hard questions, £{world.REMATCH_REWARD} prize"
                                  if gold else "Win the Gold Badge"),
                         MenuItem("See your Money Skills Report", "after_gym")]
            else:
                items = [MenuItem("Challenge Professor Penny", "challenge", enabled=ready,
                                  note=None if ready else "Beat the Route 1 trainers first")]
        items.append(MenuItem("Leave", "leave"))
        self.menu = Menu(self.game, items)

    def speech_text(self):
        return f"{self.room['title']}. {ROOM_INFO[self.id]} Options: " + \
            ", ".join(Menu.item_speech(i) for i in self.menu.items)

    def on_resume(self):
        focus = self.menu.focus
        self.build()
        self.menu.focus = min(focus, len(self.menu.items) - 1)

    def handle(self, event):
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        g, st = self.game, self.st
        if kind == "back" or value == "leave":
            g.pop(self)
            self.on_exit()
        elif value == "heal":
            st.heal_party()
            for m in st.storage:
                m.full_heal()
            g.audio.play("heal")
            g.say(["Your whole party is fully healed, fainted Mintlings included. It's always free, "
                   "as often as you like!"], speaker=CARETAKER)
        elif value == "lessons":
            self.lessons()
        elif value == "talk":
            g.say(["Remember: rewards add to your money, but they don't pay off what you owe by themselves.",
                   "Check PocketBank any time from the menu. It shows your money and your credit separately."],
                  speaker=PENNY)
        elif value == "storage":
            g.push(StorageScene(g))
        elif value == "shop":
            from .shop import ShopScene
            g.push(ShopScene(g))
        elif value == "task":
            run_npc_task(g, world.SHOPKEEPER)
        elif value == "challenge":
            self.challenge()
        elif value == "rematch":
            self.rematch()
        elif value == "after_gym":
            from .ending import finale
            if "finished" in st.flags:
                g.ask("Thanks for taking my challenge! Would you like to see your ending summary again?",
                      [("Yes", True), ("No", False)], lambda yes: yes and finale(g), speaker=PENNY)
            else:
                g.say(["Welcome back! Let's check in on your account."], speaker=PENNY, then=lambda: finale(g))

    def lessons(self):
        options = [(title, i) for i, (title, _) in enumerate(world.PENNY_LESSONS)] + [("That's all, thanks", None)]

        def chosen(i):
            if i is None:
                return
            self.game.say(world.PENNY_LESSONS[i][1], speaker=PENNY, then=self.lessons)

        self.game.ask("What would you like to know about?", options, chosen, speaker=PENNY)

    def challenge(self):
        from .battle_scene import BattleScene
        g, st = self.game, self.st
        if not st.has_able_mintling():
            g.say([f"Your Mintlings need to rest first. {CLINIC_NAME} in town will heal them for free."],
                  speaker=PENNY)
            return

        def start():
            trainer = {"name": "Professor Penny", "reward": world.GYM_REWARD, "id": "penny", "xp": "gym",
                       "reward_label": f"Gym reward: {BADGE_NAME}", "level": 3}
            battle = g.new_battle(make_team(world.GYM_TEAM, full_moves=True), trainer)
            g.push(BattleScene(g, battle, self.after_battle))

        g.say(world.PENNY_GYM_INTRO, speaker=PENNY, then=start)

    def rematch(self):
        """Post-game practice: hard questions on the player's weakest topic."""
        from ..core.report import weakest_topic
        from ..data.questions import TOPIC_NAMES
        from .battle_scene import BattleScene
        g, st = self.game, self.st
        topic = weakest_topic(st)
        focus = (f"I'll focus my questions on {TOPIC_NAMES[topic]}, the topic you found hardest." if topic else
                 "You've got every question right so far, so I'll mix hard questions from every topic.")
        prize = ("Win, and your Balance Badge turns gold!" if "gold_badge" not in st.flags else
                 f"Each win is worth £{world.REMATCH_REWARD}.")

        def start(yes):
            if not yes:
                return
            st.heal_party()
            trainer = {"name": "Professor Penny", "reward": world.REMATCH_REWARD, "id": "penny_rematch",
                       "xp": "gym", "level": 3, "topics": [topic] if topic else None,
                       "reward_label": "Rematch reward: Professor Penny"}
            battle = g.new_battle(make_team(world.REMATCH_TEAM, full_moves=True), trainer)
            g.push(BattleScene(g, battle, self.after_rematch))

        g.say(["Back for more? This is my full-strength team, and every question is a hard one.", focus, prize,
               "I'll heal your Mintlings first, and there's nothing to lose but practice."], speaker=PENNY,
              then=lambda: g.ask("Ready for the rematch?", [("Let's battle", True), ("Not yet", False)], start,
                                 speaker=PENNY))

    def after_rematch(self, outcome):
        g, st = self.game, self.st
        st.heal_party()
        if outcome == "win":
            first_gold = "gold_badge" not in st.flags
            st.flags.add("gold_badge")
            g.audio.play("level")
            lines = (["Outstanding! Your Balance Badge is now a Gold Balance Badge!"] if first_gold else
                     ["Another win! You really know your stuff."])
            lines.append(f"The £{world.REMATCH_REWARD} reward has gone into your money. Your Money Skills Report "
                         "shows how your scores have improved.")
        else:
            # A practice rematch never costs money.
            lines = ["Good effort! Hard questions take practice. Check your Money Skills Report, then try again "
                     "whenever you like. I've healed your Mintlings."]
        g.say(lines, speaker=PENNY)

    def after_battle(self, outcome):
        from .ending import finale
        g, st = self.game, self.st
        if outcome == "win":
            st.flags.add("gym_beaten")
            g.audio.play("level")
            g.say(world.PENNY_GYM_WIN + [f"Here's your £{world.GYM_REWARD} reward. You can see it in PocketBank.",
                                         "Now, let's check in on your account."],
                  speaker=PENNY, then=lambda: finale(g))
        else:
            # A normal loss: back to Mintwell Clinic, healed, losing 10% of your money (max £20).
            g.say(["A good effort! Rest up and come back when you're ready. No rush."], speaker=PENNY,
                  then=lambda: (g.pop(self), self.world.blackout()))

    def draw(self, surf):
        theme = self.game.theme
        hc = self.game.settings.high_contrast
        top = draw_header(surf, self.game, self.room["title"])
        if not hc:
            pygame.draw.rect(surf, self.room["wall"], (0, top, SCREEN_W, 200))
            for y in range(top + 200, SCREEN_H, 48):
                for x in range(0, SCREEN_W, 48):
                    c = self.room["floor"]
                    if (x // 48 + y // 48) % 2:
                        c = tuple(max(0, v - 14) for v in c)
                    pygame.draw.rect(surf, c, (x, y, 48, 48))
            pygame.draw.rect(surf, (140, 100, 70), (360, top + 230, 300, 40))   # counter
            pygame.draw.rect(surf, (100, 70, 50), (360, top + 230, 300, 40), 3)
        host = self.room["host"]
        bob = int(math.sin(self.game.anim_time * 2) * 3)
        if host == "penny":
            img = sprites.portrait("penny", 220)
            surf.blit(img, img.get_rect(midbottom=(510, top + 250 + bob)))
        else:
            img = pygame.transform.scale_by(sprites.person(host, "down", 0), 2.5)
            surf.blit(img, img.get_rect(midbottom=(510, top + 236 + bob)))
        panel = draw_panel(surf, (SCREEN_W - 440, top + 290, 420, SCREEN_H - HINT_SPACE - top - 300), theme)
        self.menu.draw(surf, panel.inflate(-24, -24))
        info = draw_panel(surf, (20, top + 290, SCREEN_W - 480, panel.h), theme)
        draw_wrapped(surf, ROOM_INFO[self.id], self.game.fonts.get("small"), theme["text"], info.inflate(-28, -24))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Select"), ("Esc", "Leave")])


# =========================================================================== storage
class StorageScene(Scene):
    """Swap Mintlings between the party (max 3) and storage at Mintwell Clinic."""

    def __init__(self, game):
        super().__init__(game)
        self.build()

    def build(self):
        st = self.game.state
        items = [MenuItem(f"Take {m.name} (Lv {m.level})", ("take", i), speech=mon_summary(m))
                 for i, m in enumerate(st.storage)]
        items.append(MenuItem("Store a party Mintling here", "store", enabled=len(st.party) > 1,
                              note=None if len(st.party) > 1 else "Need at least 1 in party"))
        items.append(MenuItem("Back", "back"))
        self.menu = Menu(self.game, items)

    def speech_text(self):
        return "Mintling storage. Options: " + ", ".join(Menu.item_speech(i) for i in self.menu.items)

    def handle(self, event):
        res = self.menu.handle(event)
        if not res:
            return
        kind, value = res
        st = self.game.state
        if kind == "back" or value == "back":
            self.game.pop(self)
        elif value == "store":
            def store(i):
                m = st.party.pop(i)
                m.full_heal()
                st.storage.append(m)
                self.build()
                self.game.toast(f"{m.name} is resting in storage.")
            self.game.push(PartyPicker(self.game, "Store which Mintling?", store))
        elif value[0] == "take":
            idx = value[1]
            if len(st.party) < PARTY_MAX:
                m = st.storage.pop(idx)
                st.party.append(m)
                self.build()
                self.game.toast(f"{m.name} joined your party.")
            else:
                def swap(i):
                    incoming = st.storage.pop(idx)
                    outgoing = st.party[i]
                    outgoing.full_heal()
                    st.party[i] = incoming
                    st.storage.append(outgoing)
                    self.build()
                    self.game.toast(f"{incoming.name} swapped in for {outgoing.name}.")
                self.game.push(PartyPicker(self.game, f"Your party is full. Swap {st.storage[idx].name} with?",
                                           swap))

    def draw(self, surf):
        theme = self.game.theme
        st = self.game.state
        top = draw_header(surf, self.game, "Mintling storage", f"Party {len(st.party)}/{PARTY_MAX}") + 16
        left = draw_panel(surf, (16, top, 520, SCREEN_H - HINT_SPACE - top - 16), theme)
        self.menu.draw(surf, left.inflate(-24, -24))
        right = draw_panel(surf, (left.right + 16, top, SCREEN_W - left.right - 32, left.h), theme)
        body = self.game.fonts.get("body")
        draw_text(surf, "Your party", body, theme["text"], (right.x + 20, right.y + 16))
        for i, m in enumerate(st.party):
            y = right.y + 56 + i * 100
            surf.blit(sprites.mintling(m.species_id, 80), (right.x + 20, y))
            draw_text(surf, f"{m.name} Lv {m.level}", self.game.fonts.get("small"), theme["text"],
                      (right.x + 110, y + 28))
        draw_hints(surf, self.game, [("Up/Down", "Move"), ("Enter", "Select"), ("Esc", "Back")])


# =========================================================================== task board
def task_board(game):
    """A repeatable way to earn money from existing content, so repayment is always possible."""
    st = game.state

    def paid(correct):
        if correct:
            world.pay_task_job(st.account, TASK_REWARD)
            game.audio.play("coin")
            game.say([f"Great work! You earned £{TASK_REWARD}. It's been added to your money.",
                      f"Your money is now £{st.account.money}."], speaker="Task Board")
        else:
            game.say(["Not quite, so no pay this time. You can take another job whenever you like."],
                     speaker="Task Board")

    job, place = world.next_task_job(st.account)

    def take(yes):
        if yes:
            game.push(QuestionScene(game, game.quiz.draw(None), f"Task Board job: {job} at {place}",
                                    paid, intro=f"Answer correctly to earn £{TASK_REWARD}.",
                                    on_cancel=lambda: None))

    game.say(["Copperleaf Task Board: odd jobs for anyone who needs to earn a little money.",
              f"Today's job: {job} at {place}. Answer one money question correctly to earn "
              f"£{TASK_REWARD}. You can take a job as often as you like."],
             speaker="Task Board",
             then=lambda: game.ask("Take a job?", [("Take a job", True), ("Not now", False)], take,
                                   speaker="Task Board"))
