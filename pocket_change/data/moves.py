"""Move definitions, from the design document's moveset table.

kind:
  damage  power-based attack (uses the damage formula)
  heal    restores `amount` of max HP (never above max HP)
  buff    raises the user's `stat` by `amount` for the battle
  debuff  lowers the target's `stat` by `amount` for the battle
  shield  halves the next damaging hit, then expires (shields don't stack)
Support moves never use damage multipliers. Every move needs a correct
answer to work; the question is drawn from the move's `topic`.
"""


def dmg(name, mtype, power, topic, desc):
    return dict(name=name, type=mtype, kind="damage", power=power, topic=topic, desc=desc)


def support(name, mtype, kind, topic, desc, stat=None, amount=0.0):
    return dict(name=name, type=mtype, kind=kind, power=0, stat=stat, amount=amount, topic=topic, desc=desc)


MOVES = {
    # Coincub (Savings)
    "coin_toss": dmg("Coin Toss", "Savings", 40, "saving", "Flicks a shiny coin at the target."),
    "budget_guard": support("Budget Guard", "Savings", "buff", "budget",
                            "Plans ahead. Raises Defence by 25% for this battle.", "df", 0.25),
    "rainy_day": support("Rainy Day", "Savings", "heal", "budget",
                         "Dips into savings to restore 25% of max HP.", amount=0.25),
    # Owlend (Debt)
    "iou_peck": dmg("IOU Peck", "Debt", 50, "borrowing", "A sharp peck with a folded IOU."),
    "balance_books": support("Balance Books", "Debt", "heal", "account",
                             "Gets the numbers straight to restore 15% of max HP.", amount=0.15),
    "repayment_strike": dmg("Repayment Strike", "Debt", 60, "repayment", "Pays back every hit in full."),
    # Sproutlet (Growth)
    "seed_fund": dmg("Seed Fund", "Growth", 50, "saving", "Scatters seeds that sprout on impact."),
    "compound_focus": support("Compound Focus", "Growth", "buff", "borrowing",
                              "Builds momentum. Raises Attack by 25% for this battle.", "atk", 0.25),
    "reinvest": dmg("Reinvest", "Growth", 60, "budget", "Puts everything it has gained back into one big hit."),
    # Stashrew (Savings)
    "penny_pounce": dmg("Penny Pounce", "Savings", 50, "saving", "A quick pounce, cheeks jingling."),
    "stash_away": support("Stash Away", "Savings", "shield", "saving",
                          "Tucks itself away. Halves the next damaging hit."),
    "nest_egg": support("Nest Egg", "Savings", "buff", "saving",
                        "Builds a cushion. Raises Defence by 25% for this battle.", "df", 0.25),
    # Tabbit (Debt)
    "overdraft_kick": dmg("Overdraft Kick", "Debt", 50, "borrowing", "A kick that goes further than planned."),
    "small_print": support("Small Print", "Debt", "debuff", "account",
                           "Points out the fine print. Lowers the target's Defence by 25%.", "df", 0.25),
    "due_date": dmg("Due Date", "Debt", 60, "repayment", "Arrives right on time, every time."),
    # Acornest (Growth)
    "root_tap": dmg("Root Tap", "Growth", 40, "saving", "Taps the ground with its root feet."),
    "root_reserve": support("Root Reserve", "Growth", "heal", "budget",
                            "Draws on stored energy to restore 25% of max HP.", amount=0.25),
    "bark_armour": support("Bark Armour", "Growth", "buff", "security",
                           "Hardens its shell. Raises Defence by 25% for this battle.", "df", 0.25),
    # Guardillo (Security)
    "secure_strike": dmg("Secure Strike", "Security", 40, "security", "A sturdy tackle with a click like a lock."),
    "fraud_shield": support("Fraud Shield", "Security", "shield", "security",
                            "Curls up tight. Halves the next damaging hit."),
    "lockdown": support("Lockdown", "Security", "debuff", "security",
                        "Locks things down. Lowers the target's Attack by 25%.", "atk", 0.25),
    # Phishfin (Scam): its questions teach recognising scams
    "bait_bite": dmg("Bait Bite", "Scam", 50, "security", "Lures the target in, then bites."),
    "false_promise": support("False Promise", "Scam", "debuff", "security",
                             "Promises something too good to be true. Lowers the target's Defence by 25%.",
                             "df", 0.25),
    "hook_line": dmg("Hook Line", "Scam", 60, "security", "Reels the target in with a shiny lure."),
}

STAT_CAP = 0.5          # stat changes are capped at +50% / -50% of the original stat
SHIELD_FACTOR = 0.5
STAT_NAMES = {"atk": "Attack", "df": "Defence"}
