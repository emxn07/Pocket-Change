"""Headless end-to-end playthrough using the real scenes and synthetic key presses.

Run:  python -m unittest tests.test_playthrough
Set POCKET_SHOTS=/some/dir to save screenshots along the way.
"""
import os
import random
import tempfile
import unittest
from collections import deque

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

from pocket_change import config  # noqa: E402

SHOTS = os.environ.get("POCKET_SHOTS")


def key_event(k, uni=""):
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode=uni, scancode=0)


class Driver:
    def __init__(self, tmp):
        # keep saves and settings out of the real save folder
        config.SAVE_PATH = os.path.join(tmp, "save.json")
        config.SETTINGS_PATH = os.path.join(tmp, "settings.json")
        from pocket_change.game import Game
        self.g = Game()
        self.g.quiz.rng = random.Random(7)
        self.shot_n = 0

    # ---------------------------------------------------------------- loop
    def frame(self, events=()):
        g = self.g
        for e in events:
            if not g._global_key(e) and g.top:
                g.top.handle(e)
        if g.top:
            g.top.update(1 / 30)
        g.draw()

    def frames(self, n):
        for _ in range(n):
            self.frame()

    def press(self, k, after=3):
        self.frame([key_event(k)])
        self.frames(after)

    def type_text(self, text):
        self.frame([pygame.event.Event(pygame.TEXTINPUT, text=text)])

    def shot(self, name):
        if SHOTS:
            os.makedirs(SHOTS, exist_ok=True)
            self.shot_n += 1
            pygame.image.save(self.g.screen, os.path.join(SHOTS, f"{self.shot_n:02d}_{name}.png"))

    @property
    def top(self):
        return self.g.top

    def top_is(self, name):
        return type(self.top).__name__ == name

    def enter_until(self, cond, limit=400):
        for _ in range(limit):
            if cond():
                return
            self.press(pygame.K_RETURN, 2)
        raise AssertionError(f"Condition not reached; top scene is {type(self.top).__name__}")

    # ---------------------------------------------------------------- world
    def world(self):
        from pocket_change.scenes.overworld import Overworld
        return next(s for s in self.g.scenes if isinstance(s, Overworld))

    def walk_to(self, target, handler=None):
        """Walk along a shortest path; handler() deals with anything that pops up."""
        from pocket_change.scenes.overworld import DIRS
        from pocket_change.data import world as wd
        ow = self.world()
        doors = set(ow.door_at)
        for _ in range(3000):
            if tuple(ow.st.pos) == tuple(target):
                return
            if self.top is not ow or ow.busy or ow.moving:
                if handler:
                    handler()
                else:
                    self.press(pygame.K_RETURN, 2)
                continue
            start = tuple(ow.st.pos)
            prev = {start: None}
            q = deque([start])
            while q:
                cur = q.popleft()
                if cur == tuple(target):
                    break
                for d, (dx, dy) in DIRS.items():
                    nxt = (cur[0] + dx, cur[1] + dy)
                    if nxt in prev or (ow.solid(*nxt) and nxt != tuple(target)):
                        continue
                    if nxt in doors and nxt != tuple(target):
                        continue
                    if wd.MAP[nxt[1]][nxt[0]] == ",":
                        continue            # avoid random encounters while walking
                    prev[nxt] = (cur, d)
                    q.append(nxt)
            node, step = tuple(target), None
            while prev.get(node) and prev[node][0] != start:
                node = prev[node][0]
            step = prev[node][1]
            ow.try_move(step)
            for _ in range(12):
                self.frame()
                if not ow.moving:
                    break
        raise AssertionError(f"Could not reach {target}, at {ow.st.pos}, top={type(self.top).__name__}")

    def handle_battle_step(self):
        """Answer correctly and use the strongest damaging move."""
        from pocket_change.data.moves import MOVES
        t = self.top
        name = type(t).__name__
        if name == "QuestionScene":
            if t.phase == "ask":
                t.menu.focus = t.q.correct_index
            self.press(pygame.K_RETURN, 2)
        elif name == "BattleScene" and t.mode == "action":
            t.menu.focus = 0
            self.press(pygame.K_RETURN, 2)
        elif name == "BattleScene" and t.mode == "moves":
            dmg = [i for i, it in enumerate(t.menu.items) if it.value in MOVES and MOVES[it.value]["kind"] == "damage"]
            t.menu.focus = max(dmg, key=lambda i: MOVES[t.menu.items[i].value]["power"])
            self.press(pygame.K_RETURN, 2)
        elif name in ("BankScene", "GuidedBankScene"):
            self.press(pygame.K_ESCAPE, 2)
        elif name == "PartyPicker":
            t.menu.focus = next((i for i, it in enumerate(t.menu.items) if it.enabled), 0)
            self.press(pygame.K_RETURN, 2)
        else:
            self.press(pygame.K_RETURN, 2)


class PlaythroughTest(unittest.TestCase):
    def test_full_adventure(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Driver(tmp)
            g = d.g
            g.start_title()
            d.frames(100)
            d.shot("title")
            g.start_new_game()
            d.frames(5)
            d.shot("guide")
            d.enter_until(lambda: d.top_is("NameEntryScene"))
            d.shot("name_entry")
            d.type_text("Sam")
            d.type_text("r")             # R is a letter here, not read-aloud
            d.press(pygame.K_r)
            self.assertEqual(d.top.name, "Samr")
            d.press(pygame.K_BACKSPACE)
            d.press(pygame.K_RETURN, 10)
            self.assertTrue(d.top_is("Dialogue"))
            d.shot("name_confirm")
            d.top.menu.focus = 1          # "No" returns to editing
            d.press(pygame.K_RETURN)
            self.assertTrue(d.top_is("NameEntryScene"))
            d.press(pygame.K_RETURN, 10)
            d.press(pygame.K_RETURN)      # Yes
            self.assertEqual(g.state.player_name, "Sam")
            d.enter_until(lambda: d.top_is("NameEntryScene"))
            self.assertEqual(d.top.name, "Finn")
            d.press(pygame.K_RETURN, 10)
            d.press(pygame.K_RETURN)
            d.enter_until(lambda: d.top_is("StarterScene"))
            self.assertEqual([i.value for i in d.top.menu.items], ["coincub", "owlend", "sproutlet"])
            d.shot("starter")
            d.top.menu.focus = 2          # Sproutlet
            d.press(pygame.K_RETURN, 40)
            d.press(pygame.K_RETURN)      # Yes
            self.assertEqual(g.state.party[0].species_id, "sproutlet")
            self.assertEqual(g.state.rival_species, "coincub")
            # Penny's type lesson, then the rival battle straight away
            d.enter_until(lambda: d.top_is("TypeChartScene"))
            d.shot("type_chart")
            d.enter_until(lambda: d.top_is("BattleScene"))
            seen_guide = False
            for _ in range(400):
                if d.top_is("Overworld"):
                    break
                if d.top_is("Dialogue") and d.top.raw[0][0] == "Professor Penny" and not seen_guide \
                        and any(type(sc).__name__ == "BattleScene" for sc in g.scenes):
                    seen_guide = True
                    d.shot("penny_first_turn")
                d.handle_battle_step()
            self.assertTrue(seen_guide)
            self.assertIn("rival_done", g.state.flags)
            acc = g.state.account
            self.assertEqual(acc.money, 130)           # £100 + £30 rival reward
            self.assertEqual(g.state.inventory["capsule"], 3)
            self.assertEqual((g.state.party[0].level, g.state.party[0].xp), (6, 0))   # 30 XP: 5 -> 6
            d.frames(10)
            d.shot("town")

            # ---------------- Security guide task (no eligible Mintling yet)
            d.walk_to((10, 43))
            d.world().st.facing = "down"
            d.press(pygame.K_RETURN)
            for _ in range(80):
                if "task:security" in g.state.flags and d.top_is("Overworld") and not d.world().busy:
                    break
                d.handle_battle_step()
            self.assertIn("task:security", g.state.flags)

            # ---------------- PoketMart: £160 basket with £130 -> borrow £30
            d.walk_to((26, 41))
            self.assertTrue(d.top_is("InteriorScene"))
            d.shot("mart")
            d.press(pygame.K_RETURN)      # Shop
            self.assertTrue(d.top_is("ShopScene"))
            shop = d.top
            for k in ("potion", "super_potion", "revive", "super_potion"):
                shop.basket.add(k)
            shop.build()
            d.frames(2)
            d.shot("shop_basket")
            shop.menu.focus = 4           # Checkout
            d.press(pygame.K_RETURN)
            self.assertTrue(d.top_is("ConfirmScene"))
            d.shot("shortfall")
            d.top.menu.focus = 2          # Borrow
            d.press(pygame.K_RETURN)
            d.shot("credit_agreement")
            d.press(pygame.K_RETURN)      # I understand
            self.assertEqual((acc.money, acc.owed, acc.available_credit), (0, 30, 70))
            # after borrowing, the shop offers a payment reminder; decline it here (tested separately)
            d.enter_until(lambda: d.top_is("ConfirmScene") and d.top.title == "Set a payment reminder?")
            d.top.menu.focus = 1
            d.press(pygame.K_RETURN)
            self.assertFalse(acc.reminder_on)
            d.enter_until(lambda: d.top_is("ShopScene"))
            d.press(pygame.K_ESCAPE)
            d.press(pygame.K_ESCAPE)      # leave PoketMart
            self.assertTrue(d.top_is("Overworld"))

            # ---------------- the two route trainers
            d.walk_to((16, 8), handler=d.handle_battle_step)
            self.assertIn("trainer:sam", g.state.flags)
            self.assertIn("trainer:hana", g.state.flags)
            self.assertEqual(acc.owed, 30)        # rewards never reduce debt automatically
            self.assertIn("scam_reported", g.state.flags)     # the phone-scam event ran after Saver Sam
            self.assertEqual(acc.owed, 30)                    # ...without touching the credit account
            acc.set_card_frozen(False)

            # ---------------- gym (retry after any loss: back at the clinic, money docked, never debt)
            gym_levels = set()
            for attempt in range(4):
                d.walk_to((15, 7), handler=d.handle_battle_step)
                g.state.heal_party()
                d.world().try_move("up")
                d.frames(12)
                self.assertTrue(d.top_is("InteriorScene"))
                if attempt == 0:
                    d.shot("gym")
                d.press(pygame.K_RETURN)  # Challenge
                for _ in range(900):
                    if d.top_is("ConfirmScene") and d.top.title == "Payment reminder":
                        break
                    if d.top_is("QuestionScene") and d.top.phase == "ask":
                        gym_levels.add(d.top.q.level)
                    if d.top_is("Overworld") and not d.world().busy:
                        break            # lost: back at Mintwell Clinic
                    if d.top_is("QuestionScene") and d.top.phase == "ask" and d.shot_n < 16:
                        d.shot("question")
                    d.handle_battle_step()
                if "gym_beaten" in g.state.flags:
                    break
                self.assertEqual(acc.owed, 30)    # losing never adds debt
            self.assertIn("gym_beaten", g.state.flags)
            self.assertEqual(gym_levels, {3})                 # Penny asks hard questions
            d.shot("payment_reminder")
            money_before = acc.money
            d.press(pygame.K_RETURN)      # Open PocketBank to repay
            self.assertTrue(d.top_is("BankScene"))
            d.shot("bank_repay")
            d.press(pygame.K_RETURN)      # Pay the full amount owed
            self.assertTrue(d.top_is("ConfirmScene"))
            d.shot("repay_review")
            d.press(pygame.K_RETURN)      # Confirm
            self.assertEqual((acc.money, acc.owed, acc.available_credit), (money_before - 30, 0, 100))
            d.press(pygame.K_RETURN)      # Done
            d.press(pygame.K_ESCAPE)      # close bank -> finale -> ending
            d.enter_until(lambda: d.top_is("EndingScene"))
            d.frames(5)
            d.shot("ending")
            self.assertIn("finished", g.state.flags)
            report = [text for _, text in d.top.report]
            self.assertTrue(any("repaid it all by the deadline" in t for t in report))
            self.assertTrue(any(t.startswith("Fake text: you ignored it") for t in report))
            self.assertTrue(any(t.startswith("Hard questions (Professor Penny)") for t in report))

            # ---------------- post-game: Penny's rematch for the Gold Balance Badge
            ending = d.top
            ending.menu.focus = next(i for i, it in enumerate(ending.menu.items) if it.value == "explore")
            d.press(pygame.K_RETURN)
            self.assertTrue(d.top_is("InteriorScene"))
            self.assertEqual(d.top.menu.items[0].value, "rematch")
            money_before = acc.money
            for attempt in range(4):
                d.top.menu.focus = 0
                d.press(pygame.K_RETURN)  # Rematch Penny
                for _ in range(900):
                    if d.top_is("InteriorScene"):
                        break
                    if d.top_is("QuestionScene") and d.top.phase == "ask":
                        self.assertEqual(d.top.q.level, 3)
                    d.handle_battle_step()
                if "gold_badge" in g.state.flags:
                    break
            self.assertIn("gold_badge", g.state.flags)
            self.assertEqual(acc.money, money_before + 30)
            self.assertEqual(g.state.badge_name, "Gold Balance Badge")
            self.assertTrue(os.path.exists(config.SAVE_PATH))
            self.assertTrue(any(t.label == "Gym reward: Balance Badge" for t in acc.transactions))

    def test_judge_demo_guided_mode_and_accessibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Driver(tmp)
            g = d.g
            g.settings.data["text_size"] = 2
            g.settings.data["high_contrast"] = True
            g.settings.data["reduce_motion"] = True
            g.start_demo()
            d.frame()
            self.assertTrue(d.top.page_done)                  # Reduce motion: text appears at once
            d.frames(5)
            d.shot("demo_intro")
            d.enter_until(lambda: d.top_is("Overworld"))
            d.shot("demo_world_hc_xl")
            acc = g.state.account
            self.assertEqual((acc.money, acc.owed), (50, 20))
            # Keyboard only: Esc > PocketBank > Guided Mode
            d.press(pygame.K_ESCAPE)
            d.press(pygame.K_DOWN)
            d.press(pygame.K_RETURN)
            self.assertTrue(d.top_is("BankScene"))
            d.press(pygame.K_RETURN)        # Guided Mode is first
            self.assertTrue(d.top_is("GuidedBankScene"))
            self.assertEqual(d.top.steps, ["purchase", "owed", "choose", "review", "receipt"])
            d.shot("guided_purchase")
            d.press(pygame.K_RETURN)        # Next
            d.shot("guided_owed")
            d.press(pygame.K_RETURN)        # Next
            self.assertEqual(d.top.step, "choose")
            d.shot("guided_choose")
            d.press(pygame.K_DOWN)
            d.press(pygame.K_DOWN)          # "Type a different amount"
            d.press(pygame.K_RETURN)
            self.assertTrue(d.top_is("AmountEntry"))
            d.type_text("30")
            d.press(pygame.K_RETURN)
            self.assertIn("only owe", d.top.error)
            d.shot("guided_amount_error")
            d.press(pygame.K_BACKSPACE)
            d.press(pygame.K_BACKSPACE)
            d.type_text("20")
            d.press(pygame.K_RETURN)
            self.assertEqual(d.top.step, "review")
            self.assertEqual((acc.money, acc.owed), (50, 20))     # nothing paid before confirming
            d.shot("guided_review_xl")
            d.press(pygame.K_RETURN)        # Confirm payment
            self.assertEqual(d.top.step, "receipt")
            self.assertEqual((acc.money, acc.owed), (30, 0))      # the design's demo figures
            d.shot("guided_receipt")
            d.press(pygame.K_RETURN)        # Done
            d.press(pygame.K_ESCAPE)        # close PocketBank
            d.press(pygame.K_ESCAPE)        # close menu
            d.frames(3)
            self.assertEqual(g.state.demo_task, "battle")
            # battle Saver Sam: one wrong answer, then right ones
            d.walk_to((15, 20))
            d.world().try_move("up")
            for _ in range(40):
                if d.top_is("BattleScene"):
                    self.assertEqual(d.top.intro, 0.0)        # no white/black flash with Reduce motion
                    break
                d.press(pygame.K_RETURN, 2)
            wrong_done = False
            for _ in range(500):
                if d.top_is("Overworld") and not d.world().busy and "trainer:sam" in g.state.flags:
                    break
                t = d.top
                if d.top_is("QuestionScene") and t.phase == "ask" and not wrong_done:
                    self.assertEqual(t.q.topic, "budget")     # Trainer 1 asks budgeting questions
                    t.menu.focus = (t.q.correct_index + 1) % 4
                    d.press(pygame.K_RETURN)
                    d.shot("demo_wrong_answer")
                    wrong_done = True
                    continue
                d.handle_battle_step()
            self.assertIn("trainer:sam", g.state.flags)
            self.assertEqual(g.state.demo_task, "scam")
            # "Something's not right": one step and the phone buzzes
            money_before = acc.money
            d.world().try_move("down")
            d.frames(8)
            self.assertIn("scam_started", g.state.flags)
            self.assertEqual(acc.money, money_before - 15)
            self.assertEqual(acc.owed, 0)                     # fraud never touches the credit account
            d.enter_until(lambda: d.top_is("PhoneTextScene"))
            d.shot("scam_text")
            d.press(pygame.K_RETURN)
            self.assertTrue(d.top_is("QuestionScene"))
            d.top.menu.focus = d.top.q.correct_index          # ignore the text, use the real app
            d.press(pygame.K_RETURN)
            d.press(pygame.K_RETURN)
            d.enter_until(lambda: d.top_is("SecurityCheckScene"))
            check = d.top
            legit = next(i for i, it in enumerate(check.menu.items) if it.value not in (check.tx.seq, "leave"))
            check.menu.focus = legit                          # pick one of your own payments first
            d.press(pygame.K_RETURN)
            self.assertIn("That one's yours", check.notice)
            d.shot("scam_spot")
            check.menu.focus = next(i for i, it in enumerate(check.menu.items) if it.value == check.tx.seq)
            d.press(pygame.K_RETURN)
            self.assertEqual(check.step, "freeze")
            d.press(pygame.K_RETURN)                          # freeze
            self.assertTrue(acc.card_frozen)
            d.press(pygame.K_RETURN)                          # report
            self.assertEqual(check.step, "done")
            self.assertEqual(acc.money, money_before)         # refunded in full
            d.shot("scam_done")
            d.press(pygame.K_RETURN)
            d.frames(3)
            self.assertEqual(g.state.demo_task, "done")
            self.assertTrue({"scam_text_safe", "scam_spotted", "scam_frozen", "scam_reported"} <= g.state.flags)
            d.press(pygame.K_ESCAPE)        # demo never writes a save
            d.g.top.menu.focus = 4
            d.press(pygame.K_RETURN)
            self.assertFalse(os.path.exists(config.SAVE_PATH))

    def test_guided_mode_with_no_debt_and_npc_task_unlock(self):
        from pocket_change.core.mintling import Mintling
        from pocket_change.data import world
        from pocket_change.scenes.bank import GuidedBankScene
        from pocket_change.scenes.tasks import run_npc_task
        with tempfile.TemporaryDirectory() as tmp:
            d = Driver(tmp)
            g = d.g
            g.start_new_game()
            g.state.party = [Mintling("coincub", 5)]
            g.reset(GuidedBankScene(g))
            self.assertEqual(d.top.steps, ["nothing"])            # £0 debt: no borrowing suggested
            self.assertNotIn("borrow the", d.top.speech_text().lower())
            d.press(pygame.K_RETURN)
            self.assertTrue(d.top is None or not d.top_is("GuidedBankScene"))
            # Banking guide's repayment task teaches Tabbit "Due Date"
            g.state = __import__("pocket_change.core.game_state", fromlist=["GameState"]).GameState.new_demo()
            g.state.party.append(Mintling("tabbit", 5))
            from pocket_change.scenes.title import TitleScene
            g.reset(TitleScene(g))
            cora = next(n for n in world.NPCS if n["task"] == "repayment")
            run_npc_task(g, cora)
            for _ in range(60):
                if "task:repayment" in g.state.flags and d.top_is("TitleScene"):
                    break
                d.press(pygame.K_RETURN, 3)
            self.assertIn("due_date", g.state.party[2].moves)
            self.assertEqual(g.state.account.owed, 0)


    def test_practice_mode_and_payment_reminder(self):
        from pocket_change.core.game_state import GameState
        from pocket_change.scenes.overworld import Overworld
        with tempfile.TemporaryDirectory() as tmp:
            d = Driver(tmp)
            g = d.g
            g.start_title()
            d.frames(100)
            title = d.top
            title.menu.focus = next(i for i, it in enumerate(title.menu.items) if it.value == "practice")
            d.press(pygame.K_RETURN)
            self.assertTrue(d.top_is("PracticeHubScene"))
            d.shot("practice_hub")
            acc = g.state.account
            # Guided Mode, keyboard only: next, next, pay £20, confirm, done
            d.press(pygame.K_RETURN)
            for _ in range(5):
                d.press(pygame.K_RETURN)
            self.assertTrue(d.top_is("PracticeHubScene"))
            self.assertEqual((acc.money, acc.owed), (30, 0))
            # Security check
            d.press(pygame.K_DOWN)
            d.press(pygame.K_RETURN)
            for _ in range(60):
                if d.top_is("PracticeHubScene") and "scam_reported" in g.state.flags:
                    break
                if d.top_is("QuestionScene") and d.top.phase == "ask":
                    d.top.menu.focus = d.top.q.correct_index
                d.press(pygame.K_RETURN, 2)
            self.assertIn("scam_reported", g.state.flags)
            self.assertEqual(acc.money, 30)
            # Payment reminder on
            d.press(pygame.K_DOWN)
            d.press(pygame.K_RETURN)
            self.assertEqual(d.top.title, "Set a payment reminder?")
            d.press(pygame.K_RETURN)
            self.assertTrue(acc.reminder_on)
            # Fresh account, then back to title; nothing was saved
            hub = d.top
            hub.menu.focus = next(i for i, it in enumerate(hub.menu.items) if it.value == "reset")
            d.press(pygame.K_RETURN)
            self.assertEqual((g.state.account.money, g.state.account.owed), (50, 20))
            self.assertFalse(os.path.exists(config.SAVE_PATH))

            # The reminder in the adventure: it fires on reaching the gym plaza while money is owed
            g.state = GameState.new_demo()
            g.state.account.reminder_on = True
            g.state.pos, g.state.facing = [16, 10], "up"
            ow = g.reset(Overworld(g))
            ow.try_move("up")
            d.frames(10)
            self.assertTrue(d.top_is("Dialogue"))
            self.assertIn("PocketBank reminder: you owe £20", d.top.page_text)
            d.shot("gym_reminder")
            d.press(pygame.K_RETURN, 3)
            d.press(pygame.K_RETURN, 3)   # "Open PocketBank to repay"
            self.assertTrue(d.top_is("BankScene"))
            d.press(pygame.K_RETURN)      # pay the full £20
            d.press(pygame.K_RETURN)      # confirm
            self.assertEqual(g.state.account.owed, 0)
            d.press(pygame.K_RETURN)      # done
            d.press(pygame.K_ESCAPE)      # close PocketBank
            d.frames(3)
            self.assertTrue(d.top_is("Overworld"))
            self.assertFalse(d.top.busy)


if __name__ == "__main__":
    unittest.main()
