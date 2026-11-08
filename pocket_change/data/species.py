"""The eight Mintlings, from the design document.

`base` values are the actual Level 5 stats (HP, Attack, Defence), not
base-stat inputs. `growth` is what each level adds. Each species starts
with two moves and unlocks a third, either at a level or through an NPC task.
"""


def sp(name, mtype, base, growth, attack, support, third, unlock, desc, role):
    return dict(name=name, type=mtype, base=base, growth=growth, moves=[attack, support],
                third=third, unlock=unlock, desc=desc, role=role)


SPECIES = {
    "coincub": sp("Coincub", "Savings", (50, 12, 18), (4, 1, 2), "coin_toss", "budget_guard",
                  "rainy_day", ("task", "budget"),
                  "A golden bear cub with a coin motif. The coin on its tummy glows brighter the more it saves.",
                  "Tough defender"),
    "owlend": sp("Owlend", "Debt", (45, 15, 15), (3, 2, 2), "iou_peck", "balance_books",
                 "repayment_strike", ("level", 7),
                 "A little owl holding a folded IOU, with a coin marking on its chest. It never forgets what is owed.",
                 "Balanced"),
    "sproutlet": sp("Sproutlet", "Growth", (40, 19, 11), (3, 3, 1), "seed_fund", "compound_focus",
                    "reinvest", ("level", 8),
                    "A small plant creature with a fresh sprout. It grows a little every day.",
                    "Strong attacker"),
    "stashrew": sp("Stashrew", "Savings", (48, 15, 12), (4, 2, 1), "penny_pounce", "stash_away",
                   "nest_egg", ("level", 7),
                   "A tiny shrew with coin-filled cheek pouches. It always has a little something put aside.",
                   "Sturdy attacker"),
    "tabbit": sp("Tabbit", "Debt", (36, 20, 10), (2, 3, 1), "overdraft_kick", "small_print",
                 "due_date", ("task", "repayment"),
                 "A rabbit with receipt-like ears and a ledger pouch. It reads every line of the small print.",
                 "Fragile heavy hitter"),
    "acornest": sp("Acornest", "Growth", (44, 11, 20), (3, 1, 3), "root_tap", "root_reserve",
                   "bark_armour", ("level", 6),
                   "An acorn creature with root feet and leafy arms. Slow to act, but very hard to knock over.",
                   "Defensive specialist"),
    "guardillo": sp("Guardillo", "Security", (46, 10, 21), (3, 1, 3), "secure_strike", "fraud_shield",
                    "lockdown", ("task", "security"),
                    "An armadillo with a shield-shaped shell and a keyhole marking. It rolls up at the first "
                    "sign of a suspicious message.",
                    "Defensive support"),
    "phishfin": sp("Phishfin", "Scam", (34, 21, 10), (2, 3, 1), "bait_bite", "false_promise",
                   "hook_line", ("level", 7),
                   "A sneaky anglerfish with a shiny coin-like lure. If an offer looks too good to be true, "
                   "it probably is.",
                   "High damage, fragile"),
}

DEX_ORDER = ["coincub", "owlend", "sproutlet", "stashrew", "tabbit", "acornest", "guardillo", "phishfin"]
STARTERS = ["coincub", "owlend", "sproutlet"]   # exclusive to starter selection

# The rival takes the starter that is weak to the player's choice.
RIVAL_PICK = {"coincub": "owlend", "owlend": "sproutlet", "sproutlet": "coincub"}

# NPC tasks that unlock a species' third move.
TASK_NAMES = {"budget": "budgeting task", "repayment": "repayment task", "security": "security task"}
