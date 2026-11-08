"""A single Mintling: stats, level, experience and moves.

Stats come straight from the design document: Level 5 values plus a fixed
gain per level. There are no IVs or EVs.
"""
import itertools

from ..config import MAX_MOVES
from ..data.species import SPECIES
from ..data.moves import MOVES

_uid = itertools.count(1)


def xp_to_next(level):
    """XP needed for the next level: 5->6 is 30, 6->7 is 40 ... 9->10 is 70. Spare XP carries over."""
    return max(30, 10 * level - 20)


def starting_moves(species_id, level, include_task_moves=False):
    sp = SPECIES[species_id]
    moves = list(sp["moves"])
    kind, value = sp["unlock"]
    if (kind == "level" and level >= value) or (kind == "task" and include_task_moves):
        moves.append(sp["third"])
    return moves[:MAX_MOVES]


class Mintling:
    def __init__(self, species_id, level, moves=None, xp=0, hp=None, nickname=None, include_task_moves=False):
        if species_id not in SPECIES:
            raise KeyError(species_id)
        self.uid = next(_uid)
        self.species_id = species_id
        self.level = level
        self.xp = xp
        self.moves = list(moves) if moves else starting_moves(species_id, level, include_task_moves)
        self.nickname = nickname
        self.hp = self.max_hp if hp is None else hp
        # battle-only state
        self.shielded = False
        self.stages = {"atk": 0.0, "df": 0.0}

    # ---------------------------------------------------------------- identity
    @property
    def species(self):
        return SPECIES[self.species_id]

    @property
    def name(self):
        return self.nickname or self.species["name"]

    @property
    def type(self):
        return self.species["type"]

    # ---------------------------------------------------------------- stats
    def _stat(self, i):
        sp = self.species
        return max(1, sp["base"][i] + sp["growth"][i] * (self.level - 5))

    @property
    def max_hp(self):
        return self._stat(0)

    @property
    def atk(self):
        return self._stat(1)

    @property
    def df(self):
        return self._stat(2)

    def effective(self, stat):
        """A stat including this battle's raises and drops (capped at +/-50%)."""
        base = self.atk if stat == "atk" else self.df
        return max(1, round(base * (1 + self.stages[stat])))

    def reset_battle_state(self):
        self.shielded = False
        self.stages = {"atk": 0.0, "df": 0.0}

    @property
    def fainted(self):
        return self.hp <= 0

    def heal(self, amount):
        """Restore HP (not to fainted Mintlings), never above max. Returns HP actually restored."""
        if self.fainted:
            return 0
        before = self.hp
        self.hp = min(self.max_hp, self.hp + amount)
        return self.hp - before

    def revive(self):
        if not self.fainted:
            return 0
        self.hp = max(1, self.max_hp // 2)
        return self.hp

    def full_heal(self):
        self.hp = self.max_hp
        self.reset_battle_state()

    # ---------------------------------------------------------------- progression
    def gain_xp(self, amount):
        """Add experience. Returns events: ("level", new_level, (hp, atk, df) gains) and ("learned", move_id).
        Levelling adds the HP gain to both max and current HP; it doesn't fully heal."""
        events = []
        self.xp += amount
        while self.xp >= xp_to_next(self.level):
            self.xp -= xp_to_next(self.level)
            self.level += 1
            gains = self.species["growth"]
            if not self.fainted:
                self.hp = min(self.max_hp, self.hp + gains[0])
            events.append(("level", self.level, gains))
            kind, value = self.species["unlock"]
            if kind == "level" and value == self.level:
                result = self.offer_move(self.species["third"])
                if result[0] == "learned":
                    events.append(result)
        return events

    def offer_move(self, move_id):
        if move_id in self.moves:
            return ("known", move_id)
        if len(self.moves) < MAX_MOVES:
            self.moves.append(move_id)
            return ("learned", move_id)
        return ("learn_full", move_id)

    def replace_move(self, old_move, new_move):
        self.moves[self.moves.index(old_move)] = new_move

    def move_data(self, move_id):
        return MOVES[move_id]

    # ---------------------------------------------------------------- save/load
    def to_dict(self):
        return {"species": self.species_id, "level": self.level, "xp": self.xp,
                "hp": self.hp, "moves": list(self.moves), "nickname": self.nickname}

    @classmethod
    def from_dict(cls, d):
        return cls(d["species"], d["level"], d["moves"], d["xp"], d["hp"], d.get("nickname"))
