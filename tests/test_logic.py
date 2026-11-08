"""Logic tests against the numbers in the final design document.
Run with:  python -m unittest discover tests"""
import math
import os
import re
import random
import tempfile
import unittest

from pocket_change.core.account import Account, AccountError
from pocket_change.core.battle import Battle, calc_damage, catch_chance, make_team
from pocket_change.core.game_state import GameState
from pocket_change.core.mintling import Mintling, xp_to_next
from pocket_change.core.quiz import QuizDeck
from pocket_change.core.shop import Basket, checkout
from pocket_change.data.moves import MOVES
from pocket_change.data.questions import QUESTIONS
from pocket_change.data.species import SPECIES, RIVAL_PICK, STARTERS, DEX_ORDER
from pocket_change.data.types import effectiveness
from pocket_change.data import world


class FixedRng(random.Random):
    """uniform() always returns the top of the range, so damage is predictable."""
    def uniform(self, a, b):
        return b


class AccountTests(unittest.TestCase):
    def test_starting_values(self):
        a = Account()
        self.assertEqual((a.money, a.owed, a.limit, a.available_credit), (100, 0, 100, 100))
        self.assertEqual(a.payment_due_text, "No payment due")

    def test_design_complete_example(self):
        """Start £100 -> buy £120 -> win £40 -> repay £20 (design doc table)."""
        a = Account()
        a.purchase(120, "Mart", allow_borrow=True)
        self.assertEqual((a.money, a.owed, a.available_credit), (0, 20, 80))
        a.earn(40, "Battle reward")
        self.assertEqual((a.money, a.owed, a.available_credit), (40, 20, 80))
        a.repay(20)
        self.assertEqual((a.money, a.owed, a.available_credit), (20, 0, 100))
        self.assertEqual(a.payment_due_text, "No payment due")

    def test_never_silently_borrows(self):
        a = Account()
        with self.assertRaises(AccountError):
            a.purchase(120, "Mart")
        self.assertEqual((a.money, a.owed), (100, 0))

    def test_shortfall_over_available_credit(self):
        plan = Account(money=10).plan_purchase(200)
        self.assertFalse(plan.allowed)
        self.assertIn("more than your available credit", plan.reason)

    def test_repayment_validation(self):
        a = Account(money=50, owed=20)
        self.assertIn("only owe", a.check_repayment(30))
        a.repay(20)
        self.assertEqual((a.money, a.owed), (30, 0))   # the design's working example
        self.assertIn("only have", Account(money=5, owed=20).check_repayment(10))
        self.assertIn("do not owe", Account().check_repayment(5))

    def test_rewards_do_not_reduce_debt_or_raise_limit(self):
        a = Account(money=0, owed=20)
        a.earn(40, "Reward")
        self.assertEqual((a.money, a.owed, a.limit), (40, 20, 100))

    def test_battle_loss_penalty(self):
        """10% of own money, capped at £20, rounded down; never touches debt."""
        for money, lost in ((100, 10), (45, 4), (300, 20), (5, 0), (0, 0)):
            a = Account(money=money, owed=20)
            a.apply_battle_loss()
            self.assertEqual(a.money, money - lost, money)
            self.assertEqual(a.owed, 20)


class CardSecurityTests(unittest.TestCase):
    def test_unauthorised_payment_report_and_refund(self):
        a = Account(money=50, owed=20)
        tx = a.unauthorised_payment(15, "PH1SHFIN PRIZES LTD")
        self.assertEqual((a.money, a.owed), (35, 20))         # own money only, never debt
        a.report_payment(tx)
        self.assertEqual(a.money, 50)
        with self.assertRaises(AccountError):
            a.report_payment(tx)                              # can't be refunded twice

    def test_frozen_card_blocks_purchases(self):
        a = Account()
        a.set_card_frozen(True)
        with self.assertRaises(AccountError):
            a.purchase(20, "Potion")
        a.set_card_frozen(False)
        a.purchase(20, "Potion")
        self.assertEqual(a.money, 80)
        self.assertFalse(Account.from_dict(a.to_dict()).card_frozen)


class ShopTests(unittest.TestCase):
    def test_design_baskets(self):
        for items, money_left, borrow in (({"potion": 2}, 60, 0),
                                          ({"super_potion": 1, "revive": 1}, 0, 0),
                                          ({"potion": 1, "super_potion": 1, "revive": 1}, 0, 20)):
            s = GameState.new_game()
            b = Basket()
            for k, n in items.items():
                b.add(k, n)
            checkout(s, b, allow_borrow=borrow > 0)
            self.assertEqual((s.account.money, s.account.owed), (money_left, borrow))


class TypeTests(unittest.TestCase):
    def test_chart(self):
        self.assertEqual(effectiveness("Savings", "Debt"), 2.0)
        self.assertEqual(effectiveness("Debt", "Growth"), 2.0)
        self.assertEqual(effectiveness("Growth", "Savings"), 2.0)
        self.assertEqual(effectiveness("Debt", "Savings"), 1.0)      # asymmetric, no resistances
        self.assertEqual(effectiveness("Scam", "Growth"), 2.0)
        self.assertEqual(effectiveness("Security", "Security"), 2.0)

    def test_starters_and_rival(self):
        self.assertEqual(STARTERS, ["coincub", "owlend", "sproutlet"])
        for starter in STARTERS:
            rival = RIVAL_PICK[starter]
            self.assertIn(rival, STARTERS)
            self.assertEqual(effectiveness(SPECIES[starter]["type"], SPECIES[rival]["type"]), 2.0, starter)

    def test_starters_not_wild(self):
        wild = {e[0] for table in world.ENCOUNTERS.values() for e in table}
        self.assertEqual(wild, set(DEX_ORDER) - set(STARTERS))


class StatTests(unittest.TestCase):
    def test_level5_stats_match_design(self):
        table = {"coincub": (50, 12, 18), "owlend": (45, 15, 15), "sproutlet": (40, 19, 11),
                 "stashrew": (48, 15, 12), "tabbit": (36, 20, 10), "acornest": (44, 11, 20),
                 "guardillo": (46, 10, 21), "phishfin": (34, 21, 10)}
        for sid, stats in table.items():
            m = Mintling(sid, 5)
            self.assertEqual((m.max_hp, m.atk, m.df), stats, sid)

    def test_growth(self):
        m = Mintling("coincub", 8)                      # +4 / +1 / +2 per level
        self.assertEqual((m.max_hp, m.atk, m.df), (62, 15, 24))

    def test_xp_table(self):
        self.assertEqual([xp_to_next(l) for l in range(5, 10)], [30, 40, 50, 60, 70])

    def test_level_up_adds_hp_without_full_heal(self):
        m = Mintling("coincub", 5)
        m.hp = 10
        events = m.gain_xp(35)
        self.assertEqual(m.level, 6)
        self.assertEqual(m.xp, 5)                       # spare XP carries over
        self.assertEqual(m.hp, 14)                      # +4, not a full heal
        self.assertEqual(events[0], ("level", 6, (4, 1, 2)))

    def test_moves(self):
        for sid, sp in SPECIES.items():
            m = Mintling(sid, 5)
            self.assertEqual(len(m.moves), 2, sid)
            self.assertIn(sp["third"], MOVES)
        o = Mintling("owlend", 6)
        o.gain_xp(40)
        self.assertIn("repayment_strike", o.moves)      # Owlend: third move at Level 7
        self.assertNotIn("rainy_day", Mintling("coincub", 10).moves)   # Coincub's comes from an NPC task

    def test_questions(self):
        for m in MOVES.values():
            self.assertIn(m["topic"], QUESTIONS)
        for qs in QUESTIONS.values():
            for q in qs:
                self.assertEqual(len(set(q["choices"])), 4, q["text"])
        deck = QuizDeck(random.Random(1))
        for _ in range(20):
            q = deck.draw("borrowing")
            self.assertEqual(sum(q.is_correct(i) for i in range(4)), 1)


class BattleTests(unittest.TestCase):
    def setUp(self):
        self.state = GameState.new_game()
        self.state.party = [Mintling("coincub", 5)]

    def test_damage_formula(self):
        """(((2*5/5+2) * 40 * 12/15)/50 + 2) = 4.56; x1.5 same type x2 advantage = 13.68 -> 13."""
        a, d = Mintling("coincub", 5), Mintling("owlend", 5)
        dmg, eff = calc_damage(a, d, "coin_toss", FixedRng())
        self.assertEqual((dmg, eff), (13, 2.0))
        d.shielded = True
        self.assertEqual(calc_damage(a, d, "coin_toss", FixedRng())[0], math.floor(13.68 * 0.5))

    def test_relaxed_battles_soften_only_opponents(self):
        a, d = Mintling("coincub", 5), Mintling("owlend", 5)
        self.assertEqual(calc_damage(a, d, "coin_toss", FixedRng(), scale=0.75)[0], math.floor(13.68 * 0.75))
        b = Battle(self.state, make_team([("stashrew", 5)]), rng=FixedRng(0), opponent_damage=0.75)
        hp = b.enemy.hp
        b._apply_move(b.player, b.enemy, "coin_toss", "player")
        self.assertEqual(hp - b.enemy.hp, calc_damage(b.player, b.enemy, "coin_toss", FixedRng())[0])

    def test_shield_expires_after_one_hit(self):
        b = Battle(self.state, make_team([("stashrew", 5)]), rng=FixedRng(0))
        b.enemy.shielded = True
        b._apply_move(b.player, b.enemy, "coin_toss", "player")
        self.assertFalse(b.enemy.shielded)

    def test_stat_changes_are_capped(self):
        b = Battle(self.state, make_team([("stashrew", 5)]), rng=FixedRng(0))
        for _ in range(4):
            b._apply_move(b.player, b.enemy, "budget_guard", "player")
        self.assertEqual(b.player.stages["df"], 0.5)
        self.assertEqual(b.player.effective("df"), 27)          # 18 x 1.5
        b.finish()
        self.assertEqual(b.player.stages["df"], 0.0)           # changes last only for the battle

    def test_heal_never_exceeds_max(self):
        b = Battle(self.state, make_team([("stashrew", 5)]), rng=FixedRng(0))
        b.player.hp = b.player.max_hp - 2
        b._apply_move(b.player, b.enemy, "rainy_day", "player")
        self.assertEqual(b.player.hp, b.player.max_hp)

    def test_incorrect_answer_fails_move(self):
        enemy = make_team([("tabbit", 5)])
        b = Battle(self.state, enemy, rng=random.Random(0))
        hp = enemy[0].hp
        b.player_move("coin_toss", correct=False)
        self.assertEqual(enemy[0].hp, hp)

    def test_trainer_reward_goes_to_money_and_xp(self):
        self.state.account.purchase(120, "Mart", allow_borrow=True)
        trainer = {"name": "Tester", "reward": 40, "xp": "trainer", "topics": ["budget"]}
        b = Battle(self.state, make_team([("tabbit", 5)]), trainer, rng=random.Random(0))
        self.assertEqual(b.question_topic("coin_toss"), "budget")
        for _ in range(15):
            if b.outcome:
                break
            b.player_move("coin_toss", correct=True)
        self.assertEqual(b.outcome, "win")
        self.assertEqual((self.state.account.money, self.state.account.owed), (40, 20))
        self.assertEqual((self.state.party[0].level, self.state.party[0].xp), (6, 0))   # 30 XP: 5 -> 6

    def test_xp_split_between_participants(self):
        self.state.party = [Mintling("coincub", 5), Mintling("stashrew", 5)]
        b = Battle(self.state, make_team([("tabbit", 5)]), {"name": "T", "reward": 0, "xp": "trainer"})
        b.participants.add(self.state.party[1].uid)
        b.award_xp(30)
        self.assertEqual([m.xp for m in self.state.party], [15, 15])

    def test_first_catch_guaranteed_and_gives_xp(self):
        self.state.inventory["capsule"] = 3
        b = Battle(self.state, make_team([("phishfin", 6)]), rng=random.Random(0))
        b.attempt_catch(correct=True)
        self.assertEqual(b.outcome, "caught")
        self.assertEqual(self.state.inventory["capsule"], 2)
        self.assertEqual(self.state.dex["phishfin"], "caught")
        self.assertEqual(self.state.party[0].xp, 15)

    def test_catch_chance_rules(self):
        self.assertGreater(catch_chance(0.5, True), catch_chance(0.5, False))
        self.assertGreater(catch_chance(0.1, True), catch_chance(0.9, True))

    def test_fourth_catch_goes_to_storage(self):
        self.state.party = [Mintling("coincub", 5), Mintling("stashrew", 5), Mintling("tabbit", 5)]
        self.assertEqual(self.state.add_mintling(Mintling("acornest", 5)), "storage")
        self.assertEqual(len(self.state.storage), 1)

    def test_loss(self):
        self.state.party = [Mintling("tabbit", 5), Mintling("phishfin", 5)]
        b = Battle(self.state, make_team([("guardillo", 15)]), {"name": "Tough", "reward": 0},
                   rng=random.Random(1))
        for _ in range(40):
            if b.outcome:
                break
            if b.need_switch:
                b.switch(b.alive_party()[0], forced=True)
            else:
                b.player_move("overdraft_kick", correct=False)
        self.assertEqual(b.outcome, "lose")


class ReportTests(unittest.TestCase):
    def test_topics_and_advice(self):
        from pocket_change.core.report import build_report
        s = GameState.new_game()
        for correct, topic in ((True, "budget"), (True, "budget"), (False, "security"), (True, "security")):
            s.record_answer(correct, topic)
        text = [t for _, t in build_report(s)]
        self.assertIn("Budgeting: 2 of 2 right", text)
        self.assertIn("Staying secure: 1 of 2 right", text)
        self.assertTrue(any(t.startswith("Practise next: Staying secure") for t in text))
        self.assertTrue(any("didn't need to borrow" in t for t in text))

    def test_credit_verdicts(self):
        from pocket_change.core.report import credit_verdict
        s = GameState.new_game()
        s.account.purchase(120, "Mart", allow_borrow=True)
        self.assertIn("still owe £20", credit_verdict(s))
        s.account.earn(40, "Reward")
        s.account.repay(20)
        self.assertIn("by the deadline", credit_verdict(s))
        s.flags.add("missed_deadline")
        self.assertIn("after the deadline", credit_verdict(s))


class GeneratedQuestionTests(unittest.TestCase):
    def test_every_template_is_well_formed(self):
        import re
        from pocket_change.core import question_gen
        rng = random.Random(11)
        for (topic, level), templates in question_gen.TEMPLATES.items():
            for template in templates:
                for _ in range(300):
                    raw = template(rng, level=level)
                    choices = raw["choices"]
                    self.assertEqual(len(choices), 4, (template.__name__, choices))
                    self.assertEqual(len(set(choices)), 4, (template.__name__, choices))
                    self.assertNotIn("£-", " ".join(choices) + raw["explain"], template.__name__)
                    # the correct answer's amount is shown in the worked explanation
                    amount = re.search(r"\d+", choices[0]).group()
                    self.assertIn(amount, raw["explain"], (template.__name__, raw))

    def test_sums_are_right(self):
        from pocket_change.core import question_gen as g
        rng = random.Random(3)
        for _ in range(200):
            raw = g.borrowing_sequence(rng)
            owed, borrow, repay = map(int, re.findall(r"£(\d+)", raw["text"])[1:4])
            self.assertEqual(raw["choices"][0], f"£{100 - (owed + borrow - repay)}")
            raw = g.budget_month(rng)
            income, *costs = map(int, re.findall(r"£(\d+)", raw["text"]))
            self.assertEqual(raw["choices"][0], f"£{income - sum(costs)}")

    def test_deck_mixes_fresh_and_written_questions(self):
        deck = QuizDeck(random.Random(4))
        texts = {deck.draw("budget", 2).text for _ in range(30)}
        self.assertGreater(len(texts), 10)       # 3 written medium questions + fresh numbers


class TierAndReminderTests(unittest.TestCase):
    def test_question_levels(self):
        deck = QuizDeck(random.Random(2))
        for level in (1, 2, 3):
            for topic in QUESTIONS:
                self.assertEqual(deck.draw(topic, level).level, level, (topic, level))
        hard = [q for qs in QUESTIONS.values() for q in qs if q["level"] == 3]
        self.assertGreaterEqual(len(hard), 12)

    def test_battle_question_level(self):
        s = GameState.new_game()
        s.party = [Mintling("coincub", 5)]
        self.assertEqual(Battle(s, make_team([("tabbit", 5)])).question_level(), 1)
        gym = Battle(s, make_team([("tabbit", 5)]), {"name": "Penny", "level": 3})
        self.assertEqual(gym.question_level(), 3)

    def test_report_hard_reminder_and_weakest(self):
        from pocket_change.core.report import build_report, weakest_topic
        s = GameState.new_game()
        s.record_answer(True, "budget", 3)
        s.record_answer(False, "security", 3)
        s.flags.add("reminder_set")
        text = [t for _, t in build_report(s)]
        self.assertIn("Hard questions (Professor Penny): 1 of 2 right.", text)
        self.assertTrue(any("payment reminder" in t for t in text))
        self.assertEqual(weakest_topic(s), "security")
        s.flags.add("gold_badge")
        s.flags.add("gym_beaten")
        self.assertTrue(build_report(s)[0][1].startswith("Gold Balance Badge"))

    def test_reminder_saved(self):
        a = Account()
        a.reminder_on = True
        self.assertTrue(Account.from_dict(a.to_dict()).reminder_on)

    def test_practice_state_never_saves(self):
        s = GameState.new_practice()
        self.assertTrue(s.practice)
        self.assertEqual((s.account.money, s.account.owed), (50, 20))
        with self.assertRaises(RuntimeError):
            s.save("/nonexistent/x.json")


class SaveAndDemoTests(unittest.TestCase):
    def test_round_trip(self):
        s = GameState.new_game()
        s.player_name, s.rival_name = "Sam", "Kai"
        s.party = [Mintling("sproutlet", 6)]
        s.storage = [Mintling("acornest", 5)]
        s.flags.add("task:budget")
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "save.json")
            s.save(path)
            t = GameState.load(path)
        self.assertEqual((t.player_name, t.rival_name), ("Sam", "Kai"))
        self.assertEqual((t.party[0].species_id, t.storage[0].species_id), ("sproutlet", "acornest"))
        self.assertIn("task:budget", t.flags)

    def test_demo_matches_presentation_script(self):
        """Judge demo: check £20 owed, pay from £50, review £30 left."""
        s = GameState.new_demo()
        a = s.account
        self.assertEqual((a.money, a.owed, a.available_credit), (50, 20, 80))
        with self.assertRaises(RuntimeError):
            s.save("/nonexistent/should-not-write.json")


if __name__ == "__main__":
    unittest.main()
