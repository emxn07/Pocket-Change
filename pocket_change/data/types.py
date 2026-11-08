"""The five-type framework from the design document.

Starter triangle: Savings beats Debt, Debt beats Growth, Growth beats Savings.
The chart is deliberately asymmetric and there are no resistances: an
advantage doubles damage, everything else is normal damage.
"""
from ..config import ADVANTAGE_MULTIPLIER

TYPES = ["Savings", "Debt", "Growth", "Scam", "Security"]

STRONG_AGAINST = {
    "Savings": ["Debt"],
    "Debt": ["Growth"],
    "Growth": ["Savings"],
    "Scam": ["Savings", "Growth"],
    "Security": ["Scam", "Security"],
}

RATIONALE = {
    "Savings": "Saved resources help repay borrowing.",
    "Debt": "Repayment costs can put pressure on growth.",
    "Growth": "Growth means taking opportunities beyond holding cash.",
    "Scam": "Fraud threatens both saved money and investments.",
    "Security": "Protection counters scams; mirror matches reward strategy.",
}

SAME_TYPE_BONUS = 1.5   # a move that matches its user's type

# Colour is always paired with the type name so it is never the only cue.
TYPE_COLOURS = {
    "Savings": (222, 170, 40),
    "Debt": (150, 80, 170),
    "Growth": (70, 160, 80),
    "Scam": (205, 70, 70),
    "Security": (60, 120, 200),
    None: (130, 130, 130),
}


def effectiveness(move_type, target_type):
    """Return the damage multiplier for a move type hitting a target type."""
    if move_type and target_type in STRONG_AGAINST.get(move_type, ()):
        return ADVANTAGE_MULTIPLIER
    return 1.0


def chart_lines():
    """The type chart as plain sentences (for reading aloud and text display)."""
    return [f"{t} is strong against {' and '.join(STRONG_AGAINST[t])}: 2x damage." for t in TYPES]
