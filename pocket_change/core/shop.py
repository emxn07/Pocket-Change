"""Shop basket logic. Checkout never silently puts a purchase on credit."""
from ..data.items import ITEMS, SHOP_ORDER

MAX_QTY = 9


class Basket:
    def __init__(self):
        self.qty = {item: 0 for item in SHOP_ORDER}

    def add(self, item, n=1):
        self.qty[item] = max(0, min(MAX_QTY, self.qty[item] + n))

    def clear(self):
        for k in self.qty:
            self.qty[k] = 0

    @property
    def total(self):
        return sum(ITEMS[k]["price"] * n for k, n in self.qty.items())

    @property
    def empty(self):
        return self.total == 0

    def describe(self):
        parts = [f"{n} {ITEMS[k]['name']}{'s' if n > 1 else ''}" for k, n in self.qty.items() if n]
        return ", ".join(parts) + "." if parts else "Nothing."


def checkout(state, basket, allow_borrow=False):
    """Pay for the basket and add the items to the inventory. Returns the transaction."""
    tx = state.account.purchase(basket.total, "PoketMart purchase", basket.describe(), allow_borrow)
    for k, n in basket.qty.items():
        state.inventory[k] = state.inventory.get(k, 0) + n
    basket.clear()
    return tx
