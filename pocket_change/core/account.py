"""PocketBank: the player's own money and a separate tutorial credit account.

Rules from the design document:
* Battle rewards increase your money, never your credit limit.
* Borrowing increases debt and reduces available credit.
* Repayment reduces your money and debt by the same amount.
* Cash and credit are never combined into one "money" figure.
* The tutorial agreement is interest-free.
"""
from dataclasses import dataclass, asdict

from ..config import START_MONEY, CREDIT_LIMIT, PAYMENT_MILESTONE, LOSS_FRACTION, LOSS_CAP


class AccountError(ValueError):
    """Raised when an account action is not allowed. The message is player-facing."""


@dataclass
class Transaction:
    seq: int
    kind: str           # gift | reward | earning | purchase | repayment
    label: str
    money_change: int   # change to your own money
    debt_change: int    # change to the amount you owe
    money_after: int
    owed_after: int
    detail: str = ""


@dataclass
class PurchasePlan:
    total: int
    from_money: int
    borrow: int
    allowed: bool
    reason: str = ""

    @property
    def needs_borrowing(self):
        return self.borrow > 0


class Account:
    def __init__(self, money=START_MONEY, owed=0, limit=CREDIT_LIMIT):
        self.money = money
        self.owed = owed
        self.limit = limit
        self.transactions = []
        self.total_borrowed = 0
        self.total_repaid = 0
        self.card_frozen = False
        self.reminder_on = False      # remind me before my payment is due

    # ------------------------------------------------------------------ figures
    @property
    def available_credit(self):
        return self.limit - self.owed

    @property
    def payment_due_text(self):
        return "No payment due" if self.owed == 0 else PAYMENT_MILESTONE

    # ------------------------------------------------------------------ records
    def _record(self, kind, label, money_change, debt_change, detail=""):
        tx = Transaction(len(self.transactions) + 1, kind, label, money_change, debt_change,
                         self.money, self.owed, detail)
        self.transactions.append(tx)
        return tx

    # ------------------------------------------------------------------ earning
    def earn(self, amount, label, kind="reward", detail=""):
        if amount <= 0:
            raise AccountError("Amount must be more than £0.")
        self.money += amount
        return self._record(kind, label, amount, 0, detail)

    def battle_loss_penalty(self):
        """A normal battle loss costs 10% of your own money, capped at £20, rounded down.
        At £0 nothing is lost. Losing never creates borrowing or increases debt."""
        return min(LOSS_CAP, int(self.money * LOSS_FRACTION))

    def apply_battle_loss(self):
        amount = self.battle_loss_penalty()
        if amount <= 0:
            return None
        self.money -= amount
        return self._record("loss", "Lost a battle (10% of your money)", -amount, 0,
                            "Losing never adds to what you owe.")

    # ------------------------------------------------------------------ card security
    def unauthorised_payment(self, amount, merchant):
        """A card payment the player didn't make (the Phishfin scam event). Taken from your own
        money only: it never creates borrowing."""
        amount = min(amount, self.money)
        if amount <= 0:
            return None
        self.money -= amount
        return self._record("card", f"Card payment: {merchant}", -amount, 0)

    def report_payment(self, tx):
        """Report a payment you didn't make. The bank refunds it in full."""
        if tx.kind != "card" or any(t.kind == "refund" and t.detail == f"#{tx.seq}" for t in self.transactions):
            raise AccountError("That payment can't be reported.")
        self.money += -tx.money_change
        return self._record("refund", f"Refund: reported payment to {tx.label.split(': ', 1)[-1]}",
                            -tx.money_change, 0, f"#{tx.seq}")

    def set_card_frozen(self, frozen):
        self.card_frozen = frozen

    # ------------------------------------------------------------------ spending
    def plan_purchase(self, total):
        """Work out how a basket would be paid for. Own money is always used first."""
        if total <= 0:
            return PurchasePlan(total, 0, 0, False, "Your basket is empty.")
        from_money = min(self.money, total)
        borrow = total - from_money
        if borrow > self.available_credit:
            return PurchasePlan(
                total, from_money, borrow, False,
                f"The shortfall of £{borrow} is more than your available credit of £{self.available_credit}.")
        return PurchasePlan(total, from_money, borrow, True)

    def purchase(self, total, label, detail="", allow_borrow=False):
        """Pay for something. Borrowing only happens when explicitly allowed:
        a purchase is never silently put on credit."""
        plan = self.plan_purchase(total)
        if not plan.allowed:
            raise AccountError(plan.reason)
        if self.card_frozen:
            raise AccountError("Your card is frozen. Unfreeze it in PocketBank to pay.")
        if plan.needs_borrowing and not allow_borrow:
            raise AccountError(f"You need £{plan.borrow} more. Choose whether to borrow it first.")
        self.money -= plan.from_money
        self.owed += plan.borrow
        self.total_borrowed += plan.borrow
        if plan.borrow:
            detail = (detail + " " if detail else "") + (
                f"£{plan.from_money} from your money, £{plan.borrow} borrowed (interest £0).")
        return self._record("purchase", label, -plan.from_money, plan.borrow, detail)

    # ------------------------------------------------------------------ repaying
    def check_repayment(self, amount):
        """Return a player-facing problem with a repayment amount, or None if it is fine."""
        if self.owed == 0:
            return "You do not owe anything, so there is nothing to repay."
        if amount <= 0:
            return "Enter an amount of at least £1."
        if amount > self.owed:
            return f"You only owe £{self.owed}. You cannot repay more than you owe."
        if amount > self.money:
            return f"You only have £{self.money}. You can only repay money you actually have."
        return None

    def max_repayment(self):
        return min(self.money, self.owed)

    def repay(self, amount):
        problem = self.check_repayment(amount)
        if problem:
            raise AccountError(problem)
        self.money -= amount
        self.owed -= amount
        self.total_repaid += amount
        return self._record("repayment", "Repayment to PocketBank credit", -amount, -amount)

    # ------------------------------------------------------------------ save/load
    def to_dict(self):
        return {
            "money": self.money, "owed": self.owed, "limit": self.limit,
            "total_borrowed": self.total_borrowed, "total_repaid": self.total_repaid,
            "card_frozen": self.card_frozen, "reminder_on": self.reminder_on,
            "transactions": [asdict(t) for t in self.transactions],
        }

    @classmethod
    def from_dict(cls, d):
        acc = cls(d["money"], d["owed"], d["limit"])
        acc.total_borrowed = d.get("total_borrowed", 0)
        acc.total_repaid = d.get("total_repaid", 0)
        acc.card_frozen = d.get("card_frozen", False)
        acc.reminder_on = d.get("reminder_on", False)
        acc.transactions = [Transaction(**t) for t in d.get("transactions", [])]
        return acc
