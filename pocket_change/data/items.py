"""Shop items. Prices are locked in the design document."""

ITEMS = {
    "potion": dict(name="Potion", price=20, heal=20, revive=False, capsule=False,
                   desc="Restores 20 HP to one Mintling."),
    "super_potion": dict(name="Super Potion", price=40, heal=50, revive=False, capsule=False,
                         desc="Restores 50 HP to one Mintling."),
    "revive": dict(name="Revive", price=60, heal=0, revive=True, capsule=False,
                   desc="Revives a fainted Mintling with half its HP."),
    "capsule": dict(name="Mint Capsule", price=10, heal=0, revive=False, capsule=True,
                    desc="Used in wild encounters to befriend a Mintling."),
}

SHOP_ORDER = ["potion", "super_potion", "revive", "capsule"]
