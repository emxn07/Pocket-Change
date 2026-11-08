"""The Money Skills Report shown at the end of the adventure.

Built only from what the game already tracks: answers per question topic,
how the credit account was used, and the scam event. It praises responsible
borrowing as much as not borrowing (the design doc warns against teaching
that borrowing is bad).
"""
from ..config import BADGE_NAME
from ..data.questions import TOPIC_NAMES
from ..data.species import DEX_ORDER

PRACTISE_WITH = {
    "budget": "Shopkeeper Sol's budgeting task at PoketMart, or the Task Board",
    "saving": "Professor Penny's lessons in her lab",
    "borrowing": "Professor Penny's lessons on credit limits and interest",
    "repayment": "Banking Guide Cora's Guided Mode task",
    "account": "the Explain terms page in PocketBank",
    "security": "Security Guide Ollie's scam task",
}


def weakest_topic(state):
    """The topic with the lowest share right (None if every answer so far was right)."""
    scores = topic_scores(state)
    if not scores:
        return None
    worst = min(scores, key=lambda s: (s[2] / s[3], -s[3]))
    return worst[0] if worst[2] < worst[3] else None


def topic_scores(state):
    """[(topic, name, correct, asked)] in a fixed order, only topics that came up."""
    topics = state.stats.get("topics", {})
    return [(t, name, topics[t][0], topics[t][1]) for t, name in TOPIC_NAMES.items()
            if t in topics and topics[t][1] > 0]


def credit_verdict(state):
    a = state.account
    if a.total_borrowed == 0:
        return "You didn't need to borrow. Credit is optional, and you managed without it."
    if a.owed == 0 and "missed_deadline" not in state.flags:
        return (f"You borrowed £{a.total_borrowed} and repaid it all by the deadline. "
                "That's using credit responsibly.")
    if a.owed == 0:
        return (f"You borrowed £{a.total_borrowed} and repaid it all after the deadline. With real credit, "
                "paying late can mean fees, so set a reminder next time.")
    return (f"You borrowed £{a.total_borrowed} and still owe £{a.owed}. There are no late fees here, but with "
            "real credit, missed payments can mean fees and make borrowing harder. Talk to your lender early "
            "if you're struggling, and repay in PocketBank when you can.")


def security_lines(state):
    f = state.flags
    if "scam_started" not in f:
        return ["Scam check: your phone never buzzed this time."]
    lines = []
    if "scam_text_safe" in f:
        lines.append("Fake text: you ignored it and checked the real app. That's exactly right.")
    elif "scam_text_unsafe" in f:
        lines.append("Fake text: next time, ignore links in messages and open your bank's app yourself.")
    steps = [label for flag, label in (("scam_spotted", "spotted the payment"), ("scam_frozen", "froze your card"),
                                       ("scam_reported", "reported it for a refund")) if flag in f]
    if steps:
        lines.append("Unrecognised payment: you " + ", ".join(steps[:-1]) +
                     (" and " if len(steps) > 1 else "") + steps[-1] + ".")
    if "scam_reported" not in f:
        lines.append("There's still an unrecognised payment to check: PocketBank > Security check.")
    return lines


def build_report(state):
    """Returns [(kind, text)]. kind is 'summary', 'topic', 'advice', 'credit' or 'security'."""
    out = []
    caught = sum(1 for v in state.dex.values() if v == "caught")
    out.append(("summary", f"{state.badge_name or BADGE_NAME} earned. Mintdex: {len(state.dex)} seen, "
                           f"{caught} caught, of {len(DEX_ORDER)}."))
    q, c = state.stats["questions"], state.stats["correct"]
    if q:
        out.append(("summary", f"Questions: {c} of {q} right ({round(100 * c / q)}%)."))
    hard_right, hard_asked = state.stats.get("hard", [0, 0])
    if hard_asked:
        out.append(("summary", f"Hard questions (Professor Penny): {hard_right} of {hard_asked} right."))
    scores = topic_scores(state)
    for _, name, right, asked in scores:
        out.append(("topic", f"{name}: {right} of {asked} right"))
    if scores:
        ranked = sorted(scores, key=lambda s: (s[2] / s[3], s[3]))
        weakest, strongest = ranked[0], ranked[-1]
        out.append(("advice", f"Strongest topic: {strongest[1]}."))
        if weakest[2] < weakest[3] and weakest is not strongest:
            out.append(("advice", f"Practise next: {weakest[1]}. Try {PRACTISE_WITH[weakest[0]]}."))
    out.append(("credit", credit_verdict(state)))
    if "reminder_set" in state.flags:
        out.append(("credit", "You set a payment reminder. That's a great habit with real credit too."))
    out += [("security", line) for line in security_lines(state)]
    return out
