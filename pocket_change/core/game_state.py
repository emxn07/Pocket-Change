"""Everything that makes up a saved adventure."""
import json
import os

from .. import config
from ..config import PARTY_MAX, FREE_CAPSULES, START_MONEY, BADGE_NAME
from ..data.species import DEX_ORDER
from ..data.world import pay_task_job
from .account import Account
from .mintling import Mintling

SAVE_VERSION = 2


class GameState:
    def __init__(self):
        self.player_name = "Alex"
        self.rival_name = "Finn"
        self.starter = None
        self.rival_species = None
        self.party = []
        self.storage = []           # extra Mintlings kept at Mintwell Clinic
        self.inventory = {"potion": 0, "super_potion": 0, "revive": 0, "capsule": 0}
        self.account = Account(money=0)
        self.flags = set()
        self.dex = {}               # species_id -> "seen" | "caught"
        self.pos = [7, 35]
        self.facing = "down"
        self.stats = {"questions": 0, "correct": 0, "battles_won": 0, "catches": 0,
                      "topics": {}}     # topic -> [correct, asked], for the Money Skills Report
        self.demo = False
        self.demo_task = None
        self.practice = False

    # ------------------------------------------------------------------ setup
    @classmethod
    def new_game(cls):
        s = cls()
        s.account.earn(START_MONEY, "Starting money", kind="gift", detail="Your own money to begin the adventure.")
        return s

    @classmethod
    def new_demo(cls):
        """The prepared Judge Demo state. The demo script needs "check £20 owed,
        pay from £50, review £30 left": start £100 -> buy three healing items for
        £120 (borrowing £20) -> win £30 from the rival -> two £10 Task Board jobs."""
        s = cls()
        s.demo = True
        s.player_name, s.rival_name = "Alex", "Finn"
        s.starter, s.rival_species = "coincub", "owlend"
        s.account.earn(START_MONEY, "Starting money", kind="gift", detail="Your own money to begin the adventure.")
        s.account.purchase(120, "PoketMart purchase", "1 Potion, 1 Super Potion, 1 Revive.", allow_borrow=True)
        s.account.earn(30, "Battle reward: Finn")
        pay_task_job(s.account, 10)      # sorting receipts
        pay_task_job(s.account, 10)      # stocking shelves
        s.inventory.update(potion=1, super_potion=1, revive=1, capsule=FREE_CAPSULES)
        s.party = [Mintling("coincub", 6), Mintling("stashrew", 5)]
        s.party[0].xp = 10
        s.flags |= {"intro_done", "got_starter", "rival_done", "trainer:rival", "first_catch", "capsules_given"}
        for sp in ("coincub", "stashrew"):
            s.dex[sp] = "caught"
        for sp in ("owlend", "tabbit"):
            s.dex[sp] = "seen"
        s.pos = [15, 23]
        s.facing = "up"
        s.demo_task = "repay"
        return s

    @classmethod
    def new_practice(cls):
        """PocketBank practice from the title screen: the demo's account (owe £20, have £50), no adventure.
        Like the demo, it is never saved."""
        s = cls.new_demo()
        s.demo_task = None
        s.practice = True
        return s

    # ------------------------------------------------------------------ party
    def add_mintling(self, mon):
        self.dex[mon.species_id] = "caught"
        if len(self.party) < PARTY_MAX:
            self.party.append(mon)
            return "party"
        self.storage.append(mon)
        return "storage"

    def record_answer(self, correct, topic=None, level=1):
        self.stats["questions"] += 1
        self.stats["correct"] += int(correct)
        if level == 3:
            hard = self.stats.setdefault("hard", [0, 0])
            hard[0] += int(correct)
            hard[1] += 1
        if topic:
            entry = self.stats["topics"].setdefault(topic, [0, 0])
            entry[0] += int(correct)
            entry[1] += 1

    def see(self, species_id):
        if self.dex.get(species_id) != "caught":
            self.dex[species_id] = "seen"

    def heal_party(self):
        for m in self.party:
            m.full_heal()

    def has_able_mintling(self):
        return any(not m.fainted for m in self.party)

    @property
    def gym_beaten(self):
        return "gym_beaten" in self.flags

    @property
    def badge_name(self):
        if "gold_badge" in self.flags:
            return f"Gold {BADGE_NAME}"
        return BADGE_NAME if self.gym_beaten else None

    # ------------------------------------------------------------------ save/load
    def to_dict(self):
        return {
            "version": SAVE_VERSION,
            "player_name": self.player_name, "rival_name": self.rival_name,
            "starter": self.starter, "rival_species": self.rival_species,
            "party": [m.to_dict() for m in self.party],
            "storage": [m.to_dict() for m in self.storage],
            "inventory": dict(self.inventory),
            "account": self.account.to_dict(),
            "flags": sorted(self.flags),
            "dex": dict(self.dex),
            "pos": list(self.pos), "facing": self.facing,
            "stats": dict(self.stats),
        }

    @classmethod
    def from_dict(cls, d):
        if d.get("version") != SAVE_VERSION:
            raise ValueError("This save is from an older version of Pocket Change. Please start a New Game.")
        s = cls()
        s.player_name, s.rival_name = d["player_name"], d["rival_name"]
        s.starter, s.rival_species = d.get("starter"), d.get("rival_species")
        s.party = [Mintling.from_dict(m) for m in d["party"]]
        s.storage = [Mintling.from_dict(m) for m in d.get("storage", [])]
        s.inventory.update(d["inventory"])
        s.account = Account.from_dict(d["account"])
        s.flags = set(d["flags"])
        s.dex = {k: v for k, v in d["dex"].items() if k in DEX_ORDER}
        s.pos, s.facing = list(d["pos"]), d["facing"]
        s.stats.update(d.get("stats", {}))
        s.stats.setdefault("topics", {})
        return s

    def save(self, path=None):
        path = path or config.SAVE_PATH
        if self.demo:
            raise RuntimeError("Judge Demo progress is never saved.")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path=None):
        path = path or config.SAVE_PATH
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    @staticmethod
    def save_exists(path=None):
        return os.path.exists(path or config.SAVE_PATH)
