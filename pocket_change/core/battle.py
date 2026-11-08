"""Turn-based battle logic, independent of any drawing code.

Rules from the design document:
* Turn order: the player acts (a move needs a correct answer), then the opponent.
  Switching or using an item takes the turn; replacing a fainted Mintling is free.
* Damage: Base = (((2 x Level / 5 + 2) x Power x Attack / Defence) / 50) + 2,
  x1.5 if the move matches the user's type, x2 for a type advantage,
  x0.85-1.00 random, x0.5 for an active shield. Rounded down, at least 1.
* Support moves don't use damage multipliers. Stat changes last for the battle,
  capped at +/-50%. Shields don't stack and expire after one damaging hit.
* XP per opposing Mintling is split equally between participating Mintlings.
  Catching gives the same XP as defeating a wild Mintling.

Every action returns a list of *events* for the battle scene to play back:
    ("msg", text)            show a message, wait for the player
    ("hp", mintling, value)  animate an HP bar to a value
    ("hit", side)            flash the Mintling on "player" / "enemy" side
    ("send", side, mintling) show a new Mintling on a side
    ("faint", side)          the Mintling on a side fainted
    ("shake", n) / ("caught", m) / ("escape",)   capsule animation
    ("sound", name)          play a sound effect
"""
import math
import random

from ..config import XP_REWARDS
from ..data.items import ITEMS
from ..data.moves import MOVES, STAT_CAP, SHIELD_FACTOR, STAT_NAMES
from ..data.types import effectiveness, SAME_TYPE_BONUS
from .mintling import Mintling

RELAXED_DAMAGE = 0.75      # "Relaxed battles" option: opponents deal 25% less damage
ENEMY_ACCURACY = 0.85      # opponents' damaging moves miss 15% of the time (balance: playtested)
CATCH_CORRECT_BASE = 0.5
CATCH_WRONG_BASE = 0.1


def calc_damage(attacker, defender, move_id, rng, scale=1.0):
    """Returns (damage, type multiplier). `scale` < 1 softens opponents' hits (Relaxed battles)."""
    move = MOVES[move_id]
    level = attacker.level
    base = ((2 * level / 5 + 2) * move["power"] * attacker.effective("atk") / defender.effective("df")) / 50 + 2
    eff = effectiveness(move["type"], defender.type)
    dmg = base * eff * rng.uniform(0.85, 1.0)
    if move["type"] == attacker.type:
        dmg *= SAME_TYPE_BONUS
    if defender.shielded:
        dmg *= SHIELD_FACTOR
    return max(1, math.floor(dmg * scale)), eff


def catch_chance(hp_ratio, correct):
    """Befriending rule: a correct answer and lower HP both help."""
    missing = 1 - max(0.0, min(1.0, hp_ratio))
    if correct:
        return min(1.0, CATCH_CORRECT_BASE + 0.5 * missing)
    return CATCH_WRONG_BASE + 0.3 * missing


def item_problem(state, item_id, target, in_battle=False, wild=False):
    """Why an item can't be used on a target right now, or None if it can."""
    item = ITEMS[item_id]
    if state.inventory.get(item_id, 0) <= 0:
        return f"You don't have any {item['name']}s"
    if item["capsule"]:
        if not in_battle:
            return "Capsules are for wild encounters"
        return None if wild else "You can't befriend a trainer's Mintling"
    if item["revive"]:
        return None if target.fainted else "Hasn't fainted"
    if target.fainted:
        return "Fainted: use a Revive"
    if target.hp >= target.max_hp:
        return "HP is already full"
    return None


def use_item_outside_battle(state, item_id, target):
    """Use a healing item from the pause menu. Returns a message."""
    item = ITEMS[item_id]
    state.inventory[item_id] -= 1
    if item["revive"]:
        target.revive()
        return f"{target.name} was revived with {target.hp} HP."
    healed = target.heal(item["heal"])
    return f"{target.name} recovered {healed} HP and now has {target.hp}/{target.max_hp}."


def make_team(spec, full_moves=False):
    """spec: list of (species_id, level). Trainers' Mintlings may know task-taught moves."""
    return [Mintling(s, lvl, include_task_moves=full_moves) for s, lvl in spec]


class Battle:
    def __init__(self, state, enemies, trainer=None, rng=None, opponent_damage=1.0):
        self.state = state
        self.opponent_damage = opponent_damage
        self.party = state.party
        self.enemies = enemies
        self.trainer = trainer          # dict(name, reward, id, xp, topics...) or None for wild
        self.rng = rng or random.Random()
        self.outcome = None             # "win" | "lose" | "caught" | "fled"
        self.need_switch = False
        self.reward = 0
        self.enemy_idx = 0
        self.player_idx = next(i for i, m in enumerate(self.party) if not m.fainted)
        for m in self.party + self.enemies:
            m.reset_battle_state()
        self.participants = {self.player.uid}
        state.see(self.enemy.species_id)

    # ------------------------------------------------------------------ helpers
    @property
    def wild(self):
        return self.trainer is None

    @property
    def player(self):
        return self.party[self.player_idx]

    @property
    def enemy(self):
        return self.enemies[self.enemy_idx]

    @property
    def xp_kind(self):
        return "wild" if self.wild else self.trainer.get("xp", "trainer")

    def alive_party(self):
        return [i for i, m in enumerate(self.party) if not m.fainted]

    def question_level(self):
        """1 easy (wild, rival), 2 medium (route trainers), 3 hard (Penny)."""
        return (self.trainer or {}).get("level", 1)

    def question_topic(self, move_id):
        """Trainers can theme their questions (e.g. budgeting); otherwise the move decides."""
        topics = (self.trainer or {}).get("topics")
        if topics:
            return self.rng.choice(topics)
        return MOVES[move_id]["topic"]

    def opening_events(self):
        ev = []
        if self.wild:
            ev.append(("msg", f"A wild {self.enemy.name} appeared!"))
        else:
            ev.append(("msg", f"{self.trainer['name']} wants to battle!"))
            ev.append(("send", "enemy", self.enemy))
            ev.append(("msg", f"{self.trainer['name']} sent out {self.enemy.name}!"))
        ev.append(("send", "player", self.player))
        ev.append(("msg", f"Go, {self.player.name}!"))
        return ev

    def finish(self):
        for m in self.party + self.enemies:
            m.reset_battle_state()

    # ------------------------------------------------------------------ moves
    def _apply_move(self, attacker, defender, move_id, side):
        """side is the attacker's side."""
        move = MOVES[move_id]
        other = "enemy" if side == "player" else "player"
        kind = move["kind"]
        ev = []
        if kind == "damage":
            scale = self.opponent_damage if side == "enemy" else 1.0
            dmg, eff = calc_damage(attacker, defender, move_id, self.rng, scale)
            shielded = defender.shielded
            defender.shielded = False           # a shield expires after one damaging hit
            defender.hp = max(0, defender.hp - dmg)
            ev.append(("hit", other))
            ev.append(("hp", defender, defender.hp))
            if eff > 1:
                ev.append(("msg", f"It's super effective! {move['type']} is strong against {defender.type}: "
                                  "2x damage."))
            if shielded:
                ev.append(("msg", f"{defender.name}'s shield halved the damage, then wore off."))
            ev.append(("msg", f"{defender.name} took {dmg} damage."))
        elif kind == "heal":
            healed = attacker.heal(max(1, round(attacker.max_hp * move["amount"])))
            ev.append(("hp", attacker, attacker.hp))
            ev.append(("msg", f"{attacker.name} restored {healed} HP." if healed
                       else f"{attacker.name} is already at full HP."))
        elif kind == "shield":
            if attacker.shielded:
                ev.append(("msg", f"{attacker.name} already has a shield. Shields don't stack."))
            else:
                attacker.shielded = True
                ev.append(("msg", f"{attacker.name} is shielded! The next damaging hit will be halved."))
        elif kind in ("buff", "debuff"):
            target = attacker if kind == "buff" else defender
            stat = move["stat"]
            change = move["amount"] if kind == "buff" else -move["amount"]
            before = target.stages[stat]
            target.stages[stat] = max(-STAT_CAP, min(STAT_CAP, before + change))
            name = STAT_NAMES[stat]
            if target.stages[stat] == before:
                ev.append(("msg", f"{target.name}'s {name} won't go any {'higher' if change > 0 else 'lower'}!"))
            else:
                pct = round(abs(target.stages[stat] - before) * 100)
                ev.append(("msg", f"{target.name}'s {name} {'rose' if change > 0 else 'fell'} by {pct}%!"))
        return ev

    def player_move(self, move_id, correct):
        p = self.player
        move = MOVES[move_id]
        ev = [("msg", f"{p.name} used {move['name']}!")]
        if correct:
            ev += self._apply_move(p, self.enemy, move_id, "player")
        else:
            ev.append(("msg", "The answer wasn't right, so the move failed."))
        return ev + self._after_player_action()

    def _choose_enemy_move(self):
        """Opponents play fairly rather than perfectly: they heal when low, sometimes use a
        support move, and otherwise pick any damaging move (they don't hunt for your weakness).
        Tuned by simulation so the route stays beatable without grinding."""
        e = self.enemy
        support = [m for m in e.moves if MOVES[m]["kind"] != "damage"]
        damaging = [m for m in e.moves if MOVES[m]["kind"] == "damage"]
        heal = [m for m in support if MOVES[m]["kind"] == "heal"]
        if heal and e.hp < e.max_hp * 0.35 and self.rng.random() < 0.5:
            return heal[0]
        if support and (not damaging or self.rng.random() < 0.3):
            return self.rng.choice(support)
        return self.rng.choice(damaging)

    def _enemy_turn(self):
        e, p = self.enemy, self.player
        move_id = self._choose_enemy_move()
        owner = "The wild " if self.wild else "The opposing "
        ev = [("msg", f"{owner}{e.name} used {MOVES[move_id]['name']}!")]
        if MOVES[move_id]["kind"] == "damage" and self.rng.random() > ENEMY_ACCURACY:
            ev.append(("msg", "But it missed!"))
            return ev
        return ev + self._apply_move(e, p, move_id, "enemy")

    def _after_player_action(self):
        if self.enemy.fainted:
            return self._enemy_fainted()
        ev = self._enemy_turn()
        if self.player.fainted:
            ev += self._player_fainted()
        return ev

    def _player_fainted(self):
        ev = [("faint", "player"), ("msg", f"{self.player.name} fainted!")]
        if self.alive_party():
            self.need_switch = True
            ev.append(("msg", "Choose a Mintling to send out. Replacing a fainted Mintling is free."))
        else:
            self.outcome = "lose"
            ev.append(("msg", "You have no Mintlings left who can battle!"))
        return ev

    def award_xp(self, total):
        """Split XP equally between participating Mintlings that can still battle (rounded up)."""
        earners = [m for m in self.party if m.uid in self.participants and not m.fainted]
        if not earners:
            return []
        share = math.ceil(total / len(earners))
        ev = []
        for m in earners:
            ev.append(("msg", f"{m.name} gained {share} XP."))
            for event in m.gain_xp(share):
                if event[0] == "level":
                    _, level, (hp, atk, df) = event
                    ev.append(("sound", "level"))
                    ev.append(("hp", m, m.hp))
                    ev.append(("msg", f"{m.name} grew to level {level}! HP +{hp}, Attack +{atk}, Defence +{df}."))
                elif event[0] == "learned":
                    ev.append(("msg", f"{m.name} learned {MOVES[event[1]]['name']}!"))
        return ev

    def _enemy_fainted(self):
        e = self.enemy
        ev = [("faint", "enemy"), ("msg", f"{'The wild' if self.wild else 'The opposing'} {e.name} fainted!")]
        ev += self.award_xp(XP_REWARDS[self.xp_kind])
        if self.enemy_idx + 1 < len(self.enemies):
            self.enemy_idx += 1
            self.participants = {self.player.uid}
            self.state.see(self.enemy.species_id)
            ev.append(("send", "enemy", self.enemy))
            ev.append(("msg", f"{self.trainer['name']} sent out {self.enemy.name}!"))
        else:
            self.outcome = "win"
            self.state.stats["battles_won"] += 1
            if not self.wild:
                self.reward = self.trainer.get("reward", 0)
                ev.append(("msg", f"You defeated {self.trainer['name']}!"))
                if self.reward:
                    label = self.trainer.get("reward_label", f"Battle reward: {self.trainer['name']}")
                    self.state.account.earn(self.reward, label)
                    ev.append(("sound", "coin"))
                    ev.append(("msg", f"You received £{self.reward}. It was added to your money, "
                                      "not your credit."))
        return ev

    # ------------------------------------------------------------------ other actions
    def can_use_item(self, item_id, target):
        return item_problem(self.state, item_id, target, in_battle=True, wild=self.wild)

    def use_item(self, item_id, target):
        item = ITEMS[item_id]
        self.state.inventory[item_id] -= 1
        ev = [("msg", f"You used a {item['name']} on {target.name}.")]
        if item["revive"]:
            target.revive()
        else:
            target.heal(item["heal"])
        ev.append(("hp", target, target.hp))
        ev.append(("msg", f"{target.name} now has {target.hp}/{target.max_hp} HP."))
        return ev + self._after_player_action()

    def switch(self, index, forced=False):
        old = self.player
        self.player_idx = index
        self.participants.add(self.player.uid)
        ev = []
        if not forced:
            ev.append(("msg", f"Come back, {old.name}!"))
        ev.append(("send", "player", self.player))
        ev.append(("msg", f"Go, {self.player.name}!"))
        if forced:
            self.need_switch = False
            return ev
        return ev + self._after_player_action()

    def run(self):
        if not self.wild:
            return [("msg", "You can't run from a trainer battle!")]
        self.outcome = "fled"
        return [("msg", "You got away safely.")]

    def attempt_catch(self, correct):
        """Use a Mint Capsule. The capsule is used up whatever happens."""
        e = self.enemy
        self.state.inventory["capsule"] -= 1
        ev = [("msg", f"You threw a Mint Capsule at {e.name}!")]
        first = "first_catch" not in self.state.flags
        if correct and first:
            success = True
        else:
            success = self.rng.random() < catch_chance(e.hp / e.max_hp, correct)
        shakes = 3 if success else self.rng.randint(0, 2)
        for n in range(1, shakes + 1):
            ev.append(("shake", n))
        if success:
            self.outcome = "caught"
            self.state.flags.add("first_catch")
            e.reset_battle_state()
            where = self.state.add_mintling(e)
            self.state.stats["catches"] += 1
            ev.append(("caught", e))
            ev.append(("msg", f"You befriended {e.name}!"))
            if where == "storage":
                ev.append(("msg", f"Your party is full, so {e.name} went to storage at Mintwell Clinic."))
            else:
                ev.append(("msg", f"{e.name} joined your party."))
            ev += self.award_xp(XP_REWARDS["wild"])
            return ev
        ev.append(("escape",))
        ev.append(("msg", f"Oh no! {e.name} popped out of the capsule."))
        return ev + self._after_player_action()
