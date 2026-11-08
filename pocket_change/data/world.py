"""Copperleaf Town, Route 1 and the Copperleaf Gym, as one scrolling map.

Tiles:  .  grass      ,  meadow grass (wild)     ;  pondside grass (wild)
        =  path       T  tree      ~  water      f  flowers
        F  fence      S  sign      B  task board
Buildings are separate objects drawn over the ground.
Dialogue text may use {player} and {rival}.

Cast (eight characters, per the design document): Professor Penny, the rival,
the PoketMart shopkeeper, the banking guide, Trainer 1, the security guide,
Trainer 2 and the Mintwell Clinic caretaker.
"""

W, H = 32, 48

BLOCKING = set("T~FSB")
WILD_TILES = {",": "Meadow grass", ";": "Pondside grass"}


def _build_map():
    g = [["." for _ in range(W)] for _ in range(H)]

    def fill(ch, x0, y0, x1, y1):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                g[y][x] = ch

    # Border
    fill("T", 0, 0, W - 1, 0)
    fill("T", 0, H - 1, W - 1, H - 1)
    fill("T", 0, 0, 0, H - 1)
    fill("T", W - 1, 0, W - 1, H - 1)

    # Gym plaza (rows 1-9)
    fill("T", 1, 1, 8, 9)
    fill("T", 23, 1, 30, 9)
    fill("=", 15, 7, 16, 9)
    fill("=", 11, 8, 20, 8)
    fill("f", 9, 2, 10, 4)
    fill("f", 21, 2, 22, 4)

    # Route 1 (rows 10-26): Pondside grass up north, Meadow grass near town
    fill("T", 1, 10, 2, 26)
    fill("T", 29, 10, 30, 26)
    fill("=", 15, 10, 16, 27)
    fill("T", 3, 11, 10, 12)
    fill("f", 5, 14, 10, 15)
    fill(";", 19, 11, 24, 16)
    fill("~", 25, 11, 28, 16)
    fill("T", 3, 17, 5, 18)
    fill("T", 24, 18, 27, 18)
    fill(",", 4, 19, 12, 24)
    fill("f", 19, 21, 26, 23)
    fill("T", 9, 26, 12, 26)

    # Town boundary, with a gap for the path north
    fill("T", 1, 27, 13, 27)
    fill("T", 18, 27, 30, 27)

    # Copperleaf Town (rows 28-46)
    fill("=", 15, 28, 16, 46)
    fill("=", 3, 36, 28, 36)
    fill("=", 3, 43, 29, 43)
    fill("=", 7, 35, 7, 35)       # lab door
    fill("=", 23, 34, 23, 35)     # house door
    fill("=", 19, 42, 19, 42)     # clinic door
    fill("=", 26, 42, 26, 42)     # mart door
    fill("F", 3, 29, 11, 29)
    fill("F", 20, 29, 27, 29)
    fill("~", 5, 39, 8, 41)
    fill("f", 11, 33, 13, 34)
    fill("f", 26, 45, 29, 45)
    fill("f", 2, 45, 5, 45)
    fill("f", 10, 40, 13, 41)

    for x, y in SIGNS:
        g[y][x] = "S"
    g[TASK_BOARD[1]][TASK_BOARD[0]] = "B"
    return ["".join(row) for row in g]


MEADOW_SIGN = (14, 24)

SIGNS = {
    (13, 9): "Copperleaf Gym. Leader: Professor Penny. Preparation tips: battle both Route 1 trainers first, "
             "heal for free at Mintwell Clinic in town, and check your money and any borrowing in PocketBank. "
             "Choose a supplies basket you can afford.",
    (13, 26): "Route 1. North: Copperleaf Gym. Meadow grass and Pondside grass are home to wild Mintlings.",
    MEADOW_SIGN: "Meadow grass: wild Mintlings live here! To befriend one, lower its HP in battle, then choose "
                 "Items and use a Mint Capsule. A correct answer and low HP both help, and your first befriending "
                 "is certain with a right answer. Here's the type chart too.",
    (14, 44): "Welcome to Copperleaf Town, where every penny counts.",
    (28, 42): "PoketMart: Potions, Super Potions, Revives and Mint Capsules (£10 each). Check your money and your "
              "basket total before you pay. Available credit is borrowed money, not your own money.",
    (21, 42): "Mintwell Clinic: free healing for your whole party, as often as you like, even for fainted "
              "Mintlings. Extra Mintlings are kept safe in storage here.",
}

TASK_BOARD = (12, 37)

# Task Board jobs rotate, so two jobs in a row never look like a duplicate payment in PocketBank.
TASK_JOBS = [("sorting receipts", "PoketMart"), ("stocking shelves", "PoketMart"),
             ("delivering leaflets", "Copperleaf Town"), ("folding towels", "Mintwell Clinic"),
             ("tidying the lab", "Professor Penny's Lab")]


def next_task_job(account):
    """(job, place) for the next Task Board job, based on how many jobs have been paid so far."""
    done = sum(1 for t in account.transactions if t.kind == "earning")
    return TASK_JOBS[done % len(TASK_JOBS)]


def pay_task_job(account, amount):
    job, place = next_task_job(account)
    return account.earn(amount, f"Task Board job: {job}", kind="earning", detail=f"{job.capitalize()} at {place}.")

BUILDINGS = [
    dict(id="gym", label="GYM", x=12, y=2, w=8, h=5, doors=[(15, 6), (16, 6)],
         roof=(176, 64, 56), wall=(236, 222, 196)),
    dict(id="lab", label="LAB", x=4, y=30, w=7, h=5, doors=[(7, 34)],
         roof=(70, 110, 170), wall=(240, 236, 226)),
    dict(id="house", label="HOME", x=21, y=30, w=6, h=4, doors=[(23, 33)],
         roof=(190, 110, 60), wall=(242, 226, 200)),
    dict(id="clinic", label="CLINIC", x=17, y=38, w=6, h=4, doors=[(19, 41)],
         roof=(220, 90, 120), wall=(248, 238, 238)),
    dict(id="mart", label="POKETMART", x=24, y=38, w=6, h=4, doors=[(26, 41)],
         roof=(60, 150, 140), wall=(236, 242, 236)),
]

# Areas used for the location banner (y ranges).
AREAS = [(0, 9, "Copperleaf Gym"), (10, 26, "Route 1"), (27, 47, "Copperleaf Town")]

START_POS = (7, 35)          # outside Penny's lab after the intro
CLINIC_POS = (19, 42)        # where you return after all Mintlings faint

ENCOUNTER_RATE = 0.12
ENCOUNTERS = {
    ",": [("stashrew", 5, 6, 50), ("tabbit", 5, 6, 30), ("acornest", 5, 6, 20)],
    ";": [("acornest", 6, 7, 40), ("guardillo", 6, 7, 35), ("phishfin", 6, 7, 25)],
}

# look = (shirt colour, hair colour, skin tone)
NPCS = [
    dict(id="cora", name="Banking Guide Cora", x=21, y=35, facing="down", task="repayment",
         look=((50, 70, 130), (30, 30, 40), (200, 150, 110)),
         lines=["Hi {player}! I help people practise with PocketBank, the banking app on your phone.",
                "PocketBank keeps your money, the amount you owe and your available credit separate. "
                "Available credit is how much you could borrow. It isn't money you've earned."],
         task_intro=["Want to practise a real account task? We'll use PocketBank's Guided Mode together.",
                     "You'll check a purchase, see what you owe, choose a repayment and review it before "
                     "anything is paid. If you don't owe anything, that's fine too!"],
         task_done=["Nicely done! Checking what you owe and reviewing a payment first are great habits."]),
    dict(id="ollie", name="Security Guide Ollie", x=10, y=44, facing="up", task="security",
         look=((140, 120, 100), (220, 220, 220), (230, 190, 160)),
         lines=["Back in my day scammers sent letters. Now it's texts with dodgy links!",
                "Warning signs: pressure to act right now, prizes you never entered for, and anyone asking "
                "for your PIN or password. Your bank will never ask for your full PIN."],
         task_intro=["Let's see if you can spot a scam. I'll give you a situation and you tell me the safe choice."],
         task_done=["Sharp eyes! Slow down, check, and contact your bank directly if something feels off."]),
]

SHOPKEEPER = dict(id="sol", name="Shopkeeper Sol", task="budget",
                  lines=["Welcome to PoketMart! Compare before you buy: two Potions heal 40 HP for £40, "
                         "and one Super Potion heals 50 HP for the same £40.",
                         "If your basket costs more than your money, I'll always ask what you'd like to do. "
                         "I'll never put it on credit without asking."],
                  task_intro=["Fancy a quick budgeting task? Work out whether a shopping plan is affordable."],
                  task_done=["Spot on. Planning your essentials first makes every choice easier."])

TASK_TOPIC = {"budget": "budget", "repayment": "repayment", "security": "security"}

TRAINERS = [
    dict(id="sam", name="Saver Sam", x=14, y=19, facing="right", sight=3, reward=40,
         team=[("stashrew", 5)], topics=["budget"], xp="trainer", level=2,
         look=((220, 170, 50), (80, 50, 30), (230, 190, 160)),
         before=["Hey! Can you afford to battle me? Let's find out. My questions are all about budgeting!"],
         after=["Nicely done. You earned that reward. Will you save some of it?"]),
    dict(id="hana", name="Hiker Hana", x=17, y=13, facing="left", sight=3, reward=50,
         team=[("tabbit", 5), ("phishfin", 6)], topics=["repayment"], xp="trainer", level=2,
         look=((150, 90, 60), (40, 30, 30), (160, 110, 80)),
         before=["The trail to the gym is steep, like an unpaid bill! I've got two Mintlings, so think about "
                 "switching and items. My questions are about repayments."],
         after=["Whew! Remember: rewards add to your money. They don't pay off debt by themselves."]),
]

RIVAL_REWARD = 30
# The design document listed levels 8 and 9. Playtesting by simulation showed that was close to
# unbeatable for Coincub and Owlend players, so the team lowered it to 7 and 8.
GYM_TEAM = [("stashrew", 7), ("guardillo", 8)]
GYM_REWARD = 100

# Post-game rematch: the full-strength team from the original design, hard questions only,
# focused on the player's weakest topic. Each win pays a modest reward; no money is lost for losing.
REMATCH_TEAM = [("stashrew", 8), ("guardillo", 9)]
REMATCH_REWARD = 30

# --------------------------------------------------------------------------- story text
PENNY_INTRO = [
    "Hello there! Welcome to the world of Mintlings!",
    "My name is Penny. People call me Professor Penny, and I also run the Copperleaf Gym.",
    "Mintlings are friendly creatures that live alongside people and help with everyday life.",
    "This little one is Coincub. It's a Savings type, and it loves to tuck coins away.",
    "Out here, knowing about money helps you prepare, and it helps you make smart choices in battle.",
    "But first, tell me a little about yourself.",
]

PENNY_AFTER_NAME = ["So you're {player}! What a great name."]

RIVAL_INTRO = [
    "This is my grandchild. They've been waiting all morning to pick a Mintling too!",
    "Hmm... what was their name again?",
]

PENNY_AFTER_RIVAL = [
    "That's right, {rival}! Now then, {player}, it's time to choose your first Mintling.",
]

TYPE_LESSON = [
    "Before you two battle, let me show you how types work.",
]

TYPE_LESSON_AFTER = [
    "Each arrow means 'strong against'. A strong move does 2x damage.",
    "You can look at this chart any time in the Mintdex.",
]

FIRST_TURN_GUIDE = [
    "I'll guide your first turn. Choose Fight, then pick a move.",
    "Every move comes with a money question. Answer correctly and the move works. If the answer's wrong, "
    "the move fails, but you'll learn why.",
    "There's no timer, so take your time!",
]

PENNY_AFTER_RIVAL_BATTLE = [
    "What a battle! I've healed both your Mintlings.",
    "Take these 3 Mint Capsules too. Use them to befriend wild Mintlings in the grass on Route 1.",
    "I've also set up PocketBank on your phone. It shows your own money, what you owe and your credit "
    "separately.",
    "You have £{money} of your own money. There's also a tutorial credit account with a £100 limit. "
    "Borrowing is optional: it's money you'd have to pay back.",
    "Heal for free at Mintwell Clinic, shop at PoketMart, and talk to people in town. Some of them can "
    "teach your Mintlings new moves!",
    "When you're ready, head north up Route 1 to my gym. Press Esc any time to open the menu.",
]

PENNY_LESSONS = [
    ("Credit limit", ["Your credit limit is the most you're allowed to owe at once. In PocketBank it's £100.",
                      "It is not money you have. It's a ceiling on borrowing."]),
    ("Available credit", ["Available credit is your credit limit minus what you owe.",
                          "Borrow £20 from a £100 limit and you have £80 available. Repay it and it goes "
                          "back up to £100. It's borrowing capacity, not earnings."]),
    ("Interest", ["Interest is the extra cost of borrowing money.",
                  "Your tutorial agreement here has £0 interest, so £20 borrowed means £20 to repay.",
                  "Most real credit does charge interest, so always check the terms."]),
    ("Repayments", ["A repayment pays back what you owe. It lowers your money and your debt by the same amount.",
                    "Winning battles adds to your money, but it doesn't reduce your debt by itself.",
                    "You choose when to repay in PocketBank. Your payment is due after my gym challenge."]),
    ("Your money vs credit", ["Your money is what you've earned or been given.",
                              "Credit is borrowed. Never add the two together and think of it as all yours!"]),
]

PENNY_GYM_LOCKED = [
    "Battle the Route 1 trainers first, then come back for my challenge.",
]

PENNY_GYM_INTRO = [
    "{player}! You made it to the Copperleaf Gym.",
    "This challenge tests what you've learned: budgeting, borrowing, repaying and staying safe.",
    "Remember, there's no timer. Take your time with each question. Let's begin!",
]

PENNY_GYM_WIN = [
    "Wonderful! You've earned the Balance Badge!",
]

MAP = _build_map()
