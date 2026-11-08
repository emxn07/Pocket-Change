"""Global constants for Pocket Change."""
import os

TITLE = "Pocket Change"
SCREEN_W, SCREEN_H = 960, 640
FPS = 60

# World art is drawn at 16px and scaled up for a crisp retro look.
ART_TILE = 16
SCALE = 3
TILE = ART_TILE * SCALE  # 48px on screen

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_DIR = os.path.join(ROOT, "saves")
SAVE_PATH = os.path.join(SAVE_DIR, "save.json")
SETTINGS_PATH = os.path.join(SAVE_DIR, "settings.json")

# Rules locked in the design document.
START_MONEY = 100
CREDIT_LIMIT = 100
PARTY_MAX = 3
MAX_MOVES = 3
FREE_CAPSULES = 3
ADVANTAGE_MULTIPLIER = 2.0

# XP for each opposing Mintling defeated (split between participating Mintlings).
XP_REWARDS = {"wild": 15, "rival": 30, "trainer": 30, "gym": 50}

# A normal battle loss costs 10% of your own money, capped at £20 (rounded down).
LOSS_FRACTION = 0.10
LOSS_CAP = 20

TOWN_NAME = "Copperleaf Town"
SHOP_NAME = "PoketMart"
CLINIC_NAME = "Mintwell Clinic"
BADGE_NAME = "Balance Badge"
GYM_NAME = "Copperleaf Gym"
PAYMENT_MILESTONE = "After the Copperleaf Gym challenge"
