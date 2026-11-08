# Pocket Change

**WHack 2026 · Capital One challenge: "Make Credit Accessible"**

Pocket Change is an accessible credit-account practice simulator inside a short creature-battling adventure. You befriend and train original creatures called **Mintlings**, earn money in battles, shop at **PoketMart**, and manage a fictional credit account in **PocketBank**, the banking app on your trainer's phone. **PocketBank Guided Mode** breaks account tasks into clear steps, explains the effect of a payment before you confirm it, and supports independent practice with large text, high contrast, read-aloud and full keyboard control. Every battle move is unlocked by answering a money question. There is never a timer.

Want just the banking part? Choose **PocketBank practice** on the title screen to go straight to the accessible account tasks, with no adventure.

The adventure covers Copperleaf Town, Route 1 and the first gym. It ends with a payment reminder, a chance to repay, and an ending screen.

> Pocket Change is practice with fictional money. It is not financial advice and does not replace a real, accessible banking service.

---

## Running the game

You need **Python 3.10+**.

```bash
git clone https://github.com/emxn07/Pocket-Change.git
cd Pocket-Change
python -m venv .venv
```

Install and run:

| OS | Install (once) | Run |
|---|---|---|
| Windows | `.venv\Scripts\pip install -r requirements.txt` | `.venv\Scripts\python main.py` |
| macOS / Linux (bash, zsh, fish) | `.venv/bin/pip install -r requirements.txt` | `.venv/bin/python main.py` |

In PyCharm, set the interpreter to the project's `.venv` and run `main.py`.

The game uses [`pygame-ce`](https://pyga.me/), the community edition of Pygame. You still write `import pygame`, and it has wheels for current Python versions.

**Read aloud** uses the operating system's speech engine:

| OS | What's needed |
|---|---|
| Windows | Nothing. Uses built-in Windows speech (System.Speech) through PowerShell |
| macOS | Nothing. Uses the built-in `say` command |
| Linux | Install `espeak-ng` (e.g. `sudo pacman -S espeak-ng` or `sudo apt install espeak-ng`) |

Options → *Test read aloud* checks it. Check it on the presentation laptop before judging.

### Running the tests

```bash
.venv/bin/python -m unittest discover tests        # Windows: .venv\Scripts\python -m unittest discover tests
```

- `tests/test_logic.py`: checks the design doc's numbers directly. This covers Level 5 stats and growth, the XP table, the damage formula (same-type, advantage, shield), shields expiring, the ±50% stat cap, healing caps, the XP split, catching, storage, the loss penalty, the account's worked examples, and the demo state (owe £20, have £50). It also covers card freezing and refunds, Relaxed battles, and the Money Skills Report.
- `tests/test_playthrough.py`: headless end-to-end runs through the real screens using simulated key presses.
  - **The full adventure:** names with Yes/No, starter, Penny's type chart, the rival battle with her first-turn guidance, an NPC task, shopping with borrowing, both trainers, the gym (retrying after a loss), the payment reminder, repayment and the ending.
  - **The Judge Demo:** Guided Mode at Extra-large text with high contrast, keyboard only, including a rejected over-payment and a confirmation that nothing is paid before you confirm. Then a battle with one wrong and one right answer, the phone-scam security check, and a check that the demo never saves.
  - **The £0-debt case**, and the banking guide's task teaching Tabbit *Due Date*.
  - **PocketBank practice**, keyboard only: Guided Mode, the security check and the payment reminder, then a fresh account. Also checks that the reminder fires at the gym and repays from PocketBank.
  - **After the ending:** Penny's rematch with hard questions, won for the Gold Balance Badge and £30. The demo test also runs with **Reduce motion** on.

  Set `POCKET_SHOTS=some/folder` to save screenshots.

---

## Controls

| Key | Action |
|---|---|
| Arrow keys / WASD | Walk; move between options |
| Enter / Space / Z | Talk, select, confirm |
| Esc / X / Backspace | Back. While exploring, opens the menu |
| **R** (or F5) | Read the current screen aloud. Press again to replay |
| **T** (or F6) | Stop reading aloud |
| G | Explain the terms in a question |
| F11 | Full screen |
| Mouse | Hover to focus, left-click to choose, right-click to go back, wheel to scroll |

A key-hint bar at the bottom of every screen shows the keys for that screen. While you're typing a name or amount, use F5/F6 to read aloud, because R and T are letters.

---

## Judge Demo (3 minutes)

Choose **Judge Demo** on the title screen. It runs on the same battle, shop and banking systems as New Game, from a prepared point, and resets every time. It never saves and never overwrites normal progress.

To show only the accessible banking, choose **PocketBank practice** instead. It opens the same account (owe £20, have £50) with Guided Mode, the security check and the payment reminder on one menu, with no adventure.

Prepared state: started with £100 → bought a Potion, Super Potion and Revive for £120 (so **£20 was borrowed** on interest-free tutorial credit) → won £30 from the rival and £20 from Task Board jobs. **Your money £50, amount you owe £20, available credit £80.**

| Time | What to show |
|---|---|
| 0:00–0:25 | The account accessibility problem and who the prototype helps |
| 0:25–0:45 | Pocket Change and the coin title animation |
| 0:45–1:25 | **Guided Mode, keyboard only.** Optionally Options → Extra large + High contrast first. Then **Esc → PocketBank → Guided Mode**: check the purchase, see "You owe £20 / Your money £50 / Available credit £80" (press **R** to hear it), choose £20, review "You will pay £20. You will have £30 left and owe £0.", **Confirm**, then the receipt |
| 1:25–2:00 | Walk north (Up) into **Saver Sam**. Choose Fight → a move → answer a budgeting question. Show a wrong answer (the move fails and the lesson is explained) and a right one |
| Bonus, if time | Take one step after the battle: the phone buzzes with a **£15 payment you didn't make** and a fake "PockettBank" text. Ignore the text, then spot the payment, **freeze the card** and report it for a refund |
| 2:00–2:30 | Connect the practical task and accessibility features to the sponsor brief |
| 2:30–3:00 | The Pygame build, each team member's contribution, close |

Options → **Return to title** resets the demo.

---

## What's in the build

### Story and world
- **Opening:** the title animation (a coin drops in as the **O** in POCKET, then a euro-style **E** in CHANGE), three guide pages, then Professor Penny's introduction with Coincub.
- **Name entry** for the player and the rival (default **Finn**): typing, Backspace, and "So your name is …?" Yes/No. *No* returns to editing.
- **Starters:** **Coincub** (Savings), **Owlend** (Debt) or **Sproutlet** (Growth). The rival takes the starter weak to yours.
- **Introductory rival battle**, straight away. Penny shows the **type chart** (labelled arrows meaning "strong against, 2×", plus a text version), then guides your first turn. This battle never costs money.
- **Copperleaf Town:**
  - Penny's Lab (money lessons)
  - **PoketMart** (shop plus the shopkeeper's budgeting task)
  - **Mintwell Clinic**, right beside it: free, unlimited healing for the whole party, plus Mintling storage
  - The Task Board
  - Signs outside the shop, clinic and gym
- **Route 1:**
  - **Meadow grass** and **Pondside grass**
  - A meadow sign with catching instructions and the type chart
  - **Saver Sam** (Trainer 1: one Mintling, budgeting questions) and **Hiker Hana** (Trainer 2: two Mintlings, repayment questions)
- **"Something's not right":** after beating Saver Sam, your phone gets a real PocketBank notification of a £15 card payment you didn't make, then a fake "PockettBank" text asking you to tap a link and enter your PIN. The safe choice is to ignore it and open the real app. PocketBank's **Security check** then has you spot the unrecognised payment, **freeze your card** and **report it** for a full refund. It never touches the credit account, and you can leave and resume it from PocketBank. While the card is frozen, PoketMart asks before unfreezing it.
- **Copperleaf Gym:** Professor Penny (Stashrew Lv 7, Guardillo Lv 8). The reward is £100 and the **Balance Badge**.
- **Payment reminder:** turn it on in PocketBank, or say yes when PoketMart offers it after you borrow. If you still owe money when you reach the Copperleaf Gym, PocketBank reminds you and offers to open the repayment screen. It's a story milestone, not a countdown.
- **Penny's rematch (after the gym):** her full-strength team (Lv 8/9) with **hard questions only**, focused on your weakest topic from the report. Your first win turns the badge into the **Gold Balance Badge**, and every win pays £30. Losing a rematch costs nothing.
- **Ending: the Money Skills Report.** It shows your score per question topic with bars, your strongest topic, and what to practise next and where. It also covers how you used credit (praising both "didn't need to borrow" and "borrowed and repaid on time") and how you handled the scam.
- **Cast:** eight characters, as the doc specifies. Penny, the rival, the shopkeeper, Banking Guide Cora, Saver Sam, Security Guide Ollie, Hiker Hana and the Mintwell Clinic caretaker.

### Mintlings and battles
| Mintling | Type | HP / Atk / Def at Lv 5 | Gain per level | Starting moves | Third move |
|---|---|---|---|---|---|
| Coincub | Savings | 50 / 12 / 18 | +4 / +1 / +2 | Coin Toss (40), Budget Guard (Def +25%) | Rainy Day (heal 25%): shopkeeper's budgeting task |
| Owlend | Debt | 45 / 15 / 15 | +3 / +2 / +2 | IOU Peck (50), Balance Books (heal 15%) | Repayment Strike (60): Lv 7 |
| Sproutlet | Growth | 40 / 19 / 11 | +3 / +3 / +1 | Seed Fund (50), Compound Focus (Atk +25%) | Reinvest (60): Lv 8 |
| Stashrew | Savings | 48 / 15 / 12 | +4 / +2 / +1 | Penny Pounce (50), Stash Away (halve next hit) | Nest Egg (Def +25%): Lv 7 |
| Tabbit | Debt | 36 / 20 / 10 | +2 / +3 / +1 | Overdraft Kick (50), Small Print (enemy Def −25%) | Due Date (60): banking guide's task |
| Acornest | Growth | 44 / 11 / 20 | +3 / +1 / +3 | Root Tap (40), Root Reserve (heal 25%) | Bark Armour (Def +25%): Lv 6 |
| Guardillo | Security | 46 / 10 / 21 | +3 / +1 / +3 | Secure Strike (40), Fraud Shield (halve next hit) | Lockdown (enemy Atk −25%): security guide's task |
| Phishfin | Scam | 34 / 21 / 10 | +2 / +3 / +1 | Bait Bite (50), False Promise (enemy Def −25%) | Hook Line (60): Lv 7 |

- **Types:** Savings > Debt > Growth > Savings; Scam > Savings and Growth; Security > Scam and Security. 2× for an advantage, with no resistances.
- **Damage:** `(((2 × Level / 5 + 2) × Power × Attack / Defence) / 50) + 2`, then ×1.5 for a same-type move, ×2 for an advantage, ×0.85–1.00 random and ×0.5 for an active shield. Rounded down, minimum 1.
- **Support moves** don't use multipliers. Stat changes last for the battle and are capped at ±50%. Shields don't stack and wear off after one damaging hit. Healing never exceeds max HP.
- **Turn loop:** choose a move → answer a related question → result plus a one-sentence explanation → opponent's turn. A wrong answer fails the move. Switching or using an item takes your turn; replacing a fainted Mintling is free. Esc backs out of a question before you answer.
- **XP:** 30 / 40 / 50 / 60 / 70 to go from level 5→6 up to 9→10, with spare XP carrying over. Each defeated opposing Mintling gives 15 (wild, or a successful catch), 30 (rival or trainer) or 50 (gym), split equally between the Mintlings that took part. Levelling adds the HP gain to current HP (it isn't a full heal) and shows the stat increases.
- **Questions:** 65 hand-written questions plus 17 templates that generate fresh numbers every time, across budgeting, saving, borrowing, repayments, account information and security, in three levels. In medium and hard fights about half the questions are generated, so number problems don't repeat word for word. Wild Mintlings and the rival ask **easy** questions, Saver Sam and Hiker Hana **medium**, and Professor Penny **hard**: multi-step sums, comparing offers, planning repayments and subtler scams, each explained step by step. Every question has on-demand definitions of terms (G). Phishfin's questions teach recognising scams.

### Money, credit and PocketBank
- Start with **£100** of your own money, **£0** owed, a **£100** tutorial credit limit and **3 free Mint Capsules**. The HUD always shows *Your money* and *You owe* as **separate** figures.
- **PoketMart:** the basket total and your money are always visible. If the basket costs more than you have, you choose: *Remove some items*, *Earn money and come back later*, or *Borrow the shortfall*. Borrowing is greyed out, with the reason, if the shortfall exceeds available credit. Borrowing shows a credit agreement before you confirm: the split between your money and credit, "Interest £0 for this tutorial agreement", the payment due and before/after figures. A purchase is **never** silently put on credit.
- **PocketBank Guided Mode** (recommended): one task at a time, with a clear next action and a way back. The steps are:
  1. Check the purchase.
  2. See what you owe, your money and your available credit, kept separate and explained ("borrowing capacity, not earnings").
  3. Choose an amount (with an explanation of what it does).
  4. Review it ("You will pay £20. You will have £30 left and owe £0.").
  5. Confirm and get a receipt ("Payment complete: £20 paid. Your money: £30. Amount owed: £0.").

  Cancelling never changes balances. Amounts over your money or your debt get a clear explanation. £0 debt is handled without ever suggesting borrowing.
- **PocketBank** also has an overview with plain-language explanations beside every figure, the full transaction history, a standard repayment flow, freezing and unfreezing your card, a Security check when there's an alert, and a glossary.
- **Losing a battle** costs 10% of your own money (rounded down, maximum £20; nothing at £0) and returns you to Mintwell Clinic, healed. It never creates borrowing or increases debt. The introductory rival battle has no penalty.
- **Repeatable earning:** the Task Board pays £10 per correct answer, as often as you like.

### Pause menu (Esc)
Mintlings (stats, moves, how to unlock the third move, party order) · PocketBank · Items · Mintdex (Unseen / Seen / Caught shown in **text and icons**, plus the **type chart**) · Save · Options.

### Accessibility (what actually works in this build)
- **Text size:** Normal / Large / Extra large, with wrapping, scrolling lists and paged dialogue.
- **High contrast:** white on black with thick yellow focus outlines.
- **Not colour alone:** focus uses a ▶ marker and a thicker border; unavailable options are struck through; right/wrong answers, types, shields and stat changes all have text labels; Guided Mode progress is shown as "Step x of y" as well as dots.
- **Keyboard only:** every account action and confirmation can be reached without a mouse.
- **Mouse:** large clickable buttons; hover focuses, click selects.
- **Read aloud:** R reads the current screen (balances, Guided Mode steps, questions and answers, menus, dialogue), T stops, and R again replays. Optional auto read-aloud. This is an in-game feature, **not** screen-reader compatibility.
- **Speech speed:** Slow, Normal or Fast read aloud.
- **Reduce motion:** stops bobbing, spinning, flashing and sliding effects, shows text instantly and skips the title animation.
- **No time pressure:** no timers anywhere. The payment deadline is a story milestone, and there are no late fees.
- **Relaxed battles** (Options): opponents deal 25% less damage. Questions, money and rewards work the same.

---

## Decisions for items the design doc left open

| Open item | Decision in this build |
|---|---|
| Catch probability | Correct answer: 50% + up to 50% more as HP falls. Wrong answer: 10% + up to 30% more. The **first catch is guaranteed** after a correct answer |
| Capsule on a failed attempt | Used up (one capsule per attempt) |
| Rounding | Loss penalty rounded down; split XP rounded up |
| Trainer rewards | Rival £30, Saver Sam £40, Hiker Hana £50 |
| Route trainer teams | Sam: Stashrew Lv 5. Hana: Tabbit Lv 5, Phishfin Lv 6 |
| Opponent behaviour | Opponents heal when low, sometimes use support moves, otherwise pick any damaging move (they don't hunt for your weakness). Damaging moves hit 85% of the time |
| Unpaid balance at the end | You can still finish. The ending states what's owed, explains that real missed payments can mean fees and make borrowing harder, and suggests contacting the lender early |
| Read aloud / save format | OS speech engine in a separate process; JSON in `saves/` (settings saved separately) |

### Gym difficulty (changed from the doc after playtesting)

The doc listed Penny at Lv 8/9. A simulation of 200 runs per case showed that was close to unbeatable for Coincub and Owlend players. The simulated player always uses the strongest attack and carries a Potion and a Super Potion. The team lowered Penny to Lv 7/8 and added the Relaxed battles option:

| Gym win rate at 75% correct answers | Penny Lv 8/9 | Penny Lv 7/8 | Lv 7/8 + Relaxed battles |
|---|---|---|---|
| Coincub + one caught Mintling | ~15% | ~59% | ~97% |
| Owlend + one caught Mintling | ~12% | ~34% | ~80% |
| Sproutlet + one caught Mintling | ~90% | ~98% | ~100% |

`GYM_TEAM` is in `pocket_change/data/world.py`.

---

## Project structure

```
main.py                     entry point
pocket_change/
  config.py                 locked rules (£100 start, £100 limit, party of 3, XP rewards, loss penalty...)
  settings.py               accessibility settings (persisted)
  game.py                   main loop, scene stack, read-aloud and helpers
  core/                     pure game logic, no drawing (unit-tested)
    account.py              PocketBank: money, credit, transactions, repayments, loss penalty
    battle.py               damage formula, support effects, XP split, catching, items, opponent AI
    report.py               the Money Skills Report (and the weakest topic for Penny's rematch)
    mintling.py             Level 5 stats + growth, XP table, move unlocks
    quiz.py                 question decks and answer shuffling
    shop.py                 basket and checkout
    game_state.py           save/load and the Judge Demo state
  data/                     content, separate from screen code
    species.py moves.py types.py items.py questions.py world.py
  ui/                       widgets (Menu, text wrapping, theme), procedural pixel art, sound, TTS
  scenes/                   title, intro, overworld, battle, bank (incl. Guided Mode), shop,
                            buildings, tasks (NPC move unlocks), security (scam event), practice
                            (PocketBank practice), menus, ending
tests/                      unit tests and headless playthroughs
```

All art and sound are generated in code (`ui/sprites.py`, `ui/audio.py`), so there are no asset files to manage. Every creature and character is original. To swap in hand-drawn sprites, replace the functions in `ui/sprites.py`.

### Adding content
- **A question:** add it to `data/questions.py`. The first choice listed is the correct one; choices are shuffled in game.
- **Changing balance:** stats and moves live in `data/species.py` and `data/moves.py`; trainers, Penny's team and encounters in `data/world.py`; rewards and penalties in `config.py`.

---

## Before presenting (checklist from the design doc)

- [ ] Names and Yes/No confirmations
- [ ] One correct and one incorrect battle turn
- [ ] Buy with cash only, and with optional credit
- [ ] Guided Mode repayment: check £20 owed, pay from £50, review £30 left, confirm by keyboard
- [ ] Scam security check: ignore the fake text, spot the payment, freeze the card, report it
- [ ] PocketBank practice from the title screen, with Speech speed and Reduce motion
- [ ] Keyboard-only use and Extra-large text
- [ ] Read aloud works on the presentation laptop
- [ ] Reset the demo (Options → Return to title)
- [ ] Informal user test: someone outside the team finds what they owe, pays, and finds the receipt without coaching
- [ ] Record a short backup video in case the live demo fails
