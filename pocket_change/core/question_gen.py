"""Question templates with fresh numbers every time, for the medium and hard fights.

Each template builds a scenario from random amounts, works out the right answer
itself, and offers wrong answers based on common mistakes (forgetting a cost,
adding instead of subtracting, counting credit as money). The explanation shows
the working, so a wrong answer still teaches the method.
Like the hand-written bank: the first choice is the correct one.
"""


def _money(n):
    return f"£{n}"


def _choices(correct, wrongs, fmt=_money, spread=(5, 10, 15, 20)):
    """The correct answer first, then three distinct, sensible wrong answers."""
    out = [correct]
    for w in wrongs:
        if w not in out and w >= 0:
            out.append(w)
    for step in spread:
        for w in (correct + step, correct - step):
            if len(out) >= 4:
                break
            if w not in out and w >= 0:
                out.append(w)
    return [fmt(v) for v in out[:4]]


def _q(text, choices, explain, terms, level):
    return {"text": text, "choices": choices, "explain": explain, "terms": list(terms), "level": level}


# ----------------------------------------------------------------------------- budgeting
def budget_shortfall(rng, level=2):
    while True:
        money = rng.randrange(80, 160, 10)
        ess = rng.randrange(40, money, 5)
        rep = rng.randrange(20, 65, 5)
        if ess + rep > money:
            break
    short = ess + rep - money
    return _q(f"You have £{money}. Essentials cost £{ess} and a £{rep} repayment is due. How much are you short?",
              _choices(short, [money - ess, ess + rep, rep]),
              f"£{ess} + £{rep} = £{ess + rep}. That's £{ess + rep} − £{money} = £{short} more than you have.",
              ["shortfall", "essentials"], level)


def budget_how_many(rng, level=2):
    price = rng.choice([15, 20, 25, 30])
    money = rng.randrange(price * 2 + 5, price * 6, 5)
    n = money // price
    left = money - n * price
    return _q(f"Potions cost £{price} each and you have £{money}. How many can you buy without borrowing?",
              _choices(n, [n + 1, n - 1, n + 2], fmt=str, spread=(3, 4)),
              f"{n} × £{price} = £{n * price}, leaving £{left}. One more would cost £{(n + 1) * price}, "
              f"which is more than £{money}.",
              [], level)


def budget_month(rng, level=3):
    rent, food, travel = rng.randrange(40, 75, 5), rng.randrange(25, 55, 5), rng.randrange(10, 35, 5)
    save = rng.randrange(10, 30, 5)
    left = rng.randrange(5, 40, 5)
    income = rent + food + travel + save + left
    return _q(f"You get £{income} this month. Rent share is £{rent}, food £{food} and travel £{travel}, "
              f"and you plan to save £{save}. How much is left for fun?",
              _choices(left, [left + save, left + travel, income - rent - food]),
              f"Planned spending and saving: £{rent} + £{food} + £{travel} + £{save} = £{income - left}. "
              f"£{income} − £{income - left} = £{left} left.",
              ["budget", "essentials"], level)


def budget_value(rng, level=3):
    a_each, b_each = rng.sample([4, 5, 6, 7, 8], 2)
    a_n, b_n = rng.choice([3, 4, 5]), rng.choice([6, 8, 10])
    a_total, b_total = a_each * a_n, b_each * b_n
    cheaper = "Pack B" if b_each < a_each else "Pack A"
    best, other = min(a_each, b_each), max(a_each, b_each)
    return _q(f"Pack A has {a_n} capsules for £{a_total}. Pack B has {b_n} capsules for £{b_total}. "
              "Which is better value per capsule?",
              [f"{cheaper}: £{best} each", f"{'Pack A' if cheaper == 'Pack B' else 'Pack B'}: £{other} each",
               "They're the same value", "The bigger pack, always"],
              f"Divide the price by how many you get: Pack A £{a_total} ÷ {a_n} = £{a_each} each; "
              f"Pack B £{b_total} ÷ {b_n} = £{b_each} each. Bigger packs aren't always cheaper per item.",
              [], level)


# ----------------------------------------------------------------------------- saving
def saving_weeks_total(rng, level=2):
    s, w = rng.choice([4, 5, 6, 8, 10, 12]), rng.choice([5, 6, 8, 10])
    return _q(f"You save £{s} every week. How much have you saved after {w} weeks?",
              _choices(s * w, [s + w, s * (w - 1), s * (w + 1)]),
              f"{w} × £{s} = £{s * w}. Small regular amounts add up.", [], level)


def saving_per_week(rng, level=3):
    k, w, have = rng.choice([5, 6, 8, 10, 12, 15]), rng.choice([4, 5, 6, 8]), rng.randrange(10, 60, 5)
    goal = have + k * w
    return _q(f"You need £{goal} in {w} weeks and have £{have} saved already. How much must you save each week?",
              _choices(k, [goal // w, k + 5, (goal + have) // w], spread=(2, 3, 4)),
              f"You still need £{goal} − £{have} = £{k * w}. Spread over {w} weeks: £{k * w} ÷ {w} = £{k} a week.",
              [], level)


def saving_with_spending(rng, level=3):
    s, w, every = rng.choice([6, 8, 10]), rng.choice([8, 9, 12]), rng.choice([3, 4])
    spend = rng.choice([5, 10, 12, 15])
    times = w // every
    total = s * w - spend * times
    return _q(f"You save £{s} every week, but every {every} weeks you spend £{spend} of it. "
              f"How much have you saved after {w} weeks?",
              _choices(total, [s * w, s * w - spend, total - spend]),
              f"Saved: {w} × £{s} = £{s * w}. You spend £{spend} in {times} of those weeks: "
              f"{times} × £{spend} = £{spend * times}. £{s * w} − £{spend * times} = £{total}.",
              [], level)


# ----------------------------------------------------------------------------- borrowing
def borrowing_available(rng, level=2):
    limit, owed = 100, rng.randrange(10, 95, 5)
    return _q(f"Your credit limit is £{limit} and you owe £{owed}. What is your available credit?",
              _choices(limit - owed, [owed, limit + owed, limit]),
              f"Available credit = credit limit − amount owed: £{limit} − £{owed} = £{limit - owed}.",
              ["credit limit", "available credit"], level)


def borrowing_shortfall(rng, level=2):
    money = rng.randrange(20, 100, 10)
    total = money + rng.randrange(10, 60, 10)
    return _q(f"A basket costs £{total} and you have £{money}. If you borrow the rest, how much do you borrow?",
              _choices(total - money, [total, money, total + money]),
              f"Use your own £{money} first, then borrow the shortfall: £{total} − £{money} = £{total - money}.",
              ["shortfall", "credit"], level)


def borrowing_sequence(rng, level=3):
    while True:
        owed, borrow, repay = rng.randrange(10, 60, 5), rng.randrange(10, 45, 5), rng.randrange(5, 40, 5)
        new_owed = owed + borrow - repay
        if 0 <= new_owed <= 100 and repay <= owed + borrow:
            break
    avail = 100 - new_owed
    return _q(f"Your credit limit is £100 and you owe £{owed}. You borrow £{borrow} more, then repay £{repay}. "
              "What is your available credit now?",
              _choices(avail, [new_owed, 100 - (owed + borrow), 100 - owed]),
              f"What you owe: £{owed} + £{borrow} − £{repay} = £{new_owed}. "
              f"Available credit = £100 − £{new_owed} = £{avail}.",
              ["credit limit", "available credit"], level)


def borrowing_instalments(rng, level=3):
    price = rng.randrange(60, 150, 10)
    months = rng.choice([6, 10, 12])
    monthly = -(-price // months) + rng.choice([1, 2, 3])
    extra = monthly * months - price
    return _q(f"A bike costs £{price} if you pay today, or £{monthly} a month for {months} months. "
              "Which costs more in total, and by how much?",
              [f"Paying monthly, by £{extra}", f"Paying today, by £{extra}", "They cost the same",
               f"Paying monthly, by £{monthly * months}"],
              f"Monthly adds up to {months} × £{monthly} = £{monthly * months}. "
              f"£{monthly * months} − £{price} = £{extra} extra. Paying over time often costs more, "
              "which works like interest.",
              ["interest"], level)


# ----------------------------------------------------------------------------- repayment
def repay_money_left(rng, level=2):
    owed = rng.randrange(10, 60, 5)
    money = owed + rng.randrange(5, 60, 5)
    return _q(f"You have £{money} and owe £{owed}. After repaying everything you owe, how much money do you have?",
              _choices(money - owed, [money + owed, owed, money]),
              f"A repayment comes out of your money: £{money} − £{owed} = £{money - owed}, and you owe £0.",
              ["repayment"], level)


def repay_partial(rng, level=2):
    owed = rng.randrange(30, 90, 10)
    paid = rng.randrange(10, owed, 5)
    return _q(f"You owe £{owed} and repay £{paid} today. How much do you still owe?",
              _choices(owed - paid, [owed + paid, paid, owed]),
              f"£{owed} − £{paid} = £{owed - paid} still to repay. Every repayment counts.",
              ["repayment"], level)


def repay_weeks(rng, level=3):
    weekly = rng.choice([10, 15, 20])
    owed = rng.randrange(50, 110, 10)
    lump = rng.choice([10, 15, 20, 25])
    remaining, week, steps = owed, 0, []
    while remaining > 0:
        week += 1
        pay = weekly + (lump if week == 2 else 0)
        remaining = max(0, remaining - pay)
        steps.append(f"week {week}: £{remaining}")
    plain = -(-owed // weekly)
    unit = lambda n: f"{n} week{'s' if n != 1 else ''}"
    return _q(f"You owe £{owed} and repay £{weekly} every week. In week 2 you also put an extra £{lump} towards it. "
              "After how many weeks do you owe nothing?",
              _choices(week, [plain, week + 1, week - 1], fmt=unit, spread=(2, 3)),
              "Owed after " + ", ".join(steps) + f". So it's paid off in week {week}.",
              ["repayment"], level)


def repay_after_reward(rng, level=3):
    money, owed = rng.randrange(0, 40, 5), rng.randrange(20, 60, 5)
    reward = rng.randrange(30, 70, 10)
    pay = min(owed, money + reward)
    m2, o2 = money + reward - pay, owed - pay
    return _q(f"You have £{money} and owe £{owed}. You win £{reward} in a battle, then repay as much as you can. "
              "How much money do you have left?",
              _choices(m2, [money + reward, money - owed if money >= owed else reward, m2 + owed]),
              f"After the reward you have £{money} + £{reward} = £{money + reward}. You repay £{pay}, leaving "
              f"£{m2}, and you owe £{o2}. The reward didn't reduce the debt until you chose to repay.",
              ["repayment"], level)


# ----------------------------------------------------------------------------- account information
def account_balance(rng, level=3):
    while True:   # every running balance stays at £0 or more, as in a real account
        start = rng.randrange(20, 60, 5)
        a, b, c, d = (rng.randrange(20, 60, 10), rng.randrange(10, 40, 5), rng.randrange(5, 30, 5),
                      rng.randrange(5, 20, 5))
        if start + a - b - c >= 0:
            break
    end = start + a - b - c + d
    return _q(f"You started with £{start}. Your history then shows: +£{a} battle reward, −£{b} shop, "
              f"−£{c} repayment, +£{d} Task Board job. What's your money now?",
              _choices(end, [start + a + b + c + d, end + 2 * c, end - 2 * d]),
              f"In order: £{start} + £{a} = £{start + a}, − £{b} = £{start + a - b}, − £{c} = "
              f"£{start + a - b - c}, + £{d} = £{end}.",
              ["transaction"], level)


def account_spend_power(rng, level=3):
    money, owed = rng.randrange(20, 80, 5), rng.randrange(10, 80, 5)
    avail = 100 - owed
    return _q(f"Your limit is £100, you owe £{owed} and you have £{money} of your own money. "
              f"A friend says you 'have £{money + avail} to spend'. What's wrong with that?",
              [f"Only £{money} is yours; the £{avail} of available credit is borrowing",
               f"Nothing, £{money + avail} is right", f"You actually have £{money + 100}",
               "You can't spend anything until you've repaid"],
              f"You have £{money} of your own. Available credit is £100 − £{owed} = £{avail}, but it's borrowed "
              "money you'd have to repay. Never add credit to your money.",
              ["available credit", "your money"], level)


TEMPLATES = {
    ("budget", 2): [budget_shortfall, budget_how_many],
    ("budget", 3): [budget_month, budget_value, budget_shortfall],
    ("saving", 2): [saving_weeks_total],
    ("saving", 3): [saving_per_week, saving_with_spending],
    ("borrowing", 2): [borrowing_available, borrowing_shortfall],
    ("borrowing", 3): [borrowing_sequence, borrowing_instalments],
    ("repayment", 2): [repay_money_left, repay_partial],
    ("repayment", 3): [repay_weeks, repay_after_reward],
    ("account", 2): [borrowing_available],
    ("account", 3): [account_balance, account_spend_power],
}


def has_templates(topic, level):
    return (topic, level) in TEMPLATES


def generate(topic, level, rng, avoid=None):
    """A fresh question for (topic, level), avoiding the template named `avoid` when possible."""
    options = TEMPLATES[(topic, level)]
    if avoid and len(options) > 1:
        options = [t for t in options if t.__name__ != avoid] or options
    template = rng.choice(options)
    raw = template(rng, level=level)
    raw["level"] = level
    return template.__name__, raw
