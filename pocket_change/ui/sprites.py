"""Procedural pixel art. Everything is drawn small and scaled up with nearest
neighbour for a crisp handheld-RPG look. All creatures and characters are original."""
import math

import pygame

from ..config import ART_TILE, SCALE

OUTLINE = (34, 26, 44)
_cache = {}


def _canvas(w, h):
    return pygame.Surface((w, h), pygame.SRCALPHA)


def _outline(surf, colour=OUTLINE):
    mask = pygame.mask.from_surface(surf)
    sil = mask.to_surface(setcolor=colour, unsetcolor=(0, 0, 0, 0))
    out = _canvas(*surf.get_size())
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        out.blit(sil, (dx, dy))
    out.blit(surf, (0, 0))
    return out


def _scale(surf, factor):
    w, h = surf.get_size()
    return pygame.transform.scale(surf, (int(w * factor), int(h * factor)))


def _eye(s, x, y, white=False):
    if white:
        pygame.draw.rect(s, (255, 255, 255), (x - 1, y - 1, 4, 4))
    pygame.draw.rect(s, (25, 20, 30), (x, y, 2, 2))
    s.set_at((x, y), (255, 255, 255))


# =========================================================================== Mintlings (32x32)
def _coincub():
    s = _canvas(32, 32)
    gold, shade, cream = (236, 184, 52), (200, 142, 32), (255, 232, 170)
    pygame.draw.ellipse(s, shade, (8, 27, 7, 4))
    pygame.draw.ellipse(s, shade, (17, 27, 7, 4))
    pygame.draw.ellipse(s, gold, (7, 15, 18, 15))
    pygame.draw.circle(s, gold, (9, 7), 4)
    pygame.draw.circle(s, gold, (23, 7), 4)
    pygame.draw.circle(s, shade, (9, 7), 2)
    pygame.draw.circle(s, shade, (23, 7), 2)
    pygame.draw.ellipse(s, gold, (5, 4, 22, 16))
    pygame.draw.ellipse(s, cream, (11, 11, 10, 7))
    _eye(s, 10, 9)
    _eye(s, 20, 9)
    pygame.draw.rect(s, (60, 40, 30), (15, 12, 3, 2))
    pygame.draw.line(s, (120, 70, 40), (15, 15), (17, 15))
    pygame.draw.circle(s, (255, 214, 90), (16, 23), 5)
    pygame.draw.circle(s, shade, (16, 23), 5, 1)
    pygame.draw.circle(s, shade, (16, 23), 3, 1)
    pygame.draw.rect(s, (255, 250, 220), (14, 20, 1, 2))
    pygame.draw.circle(s, (255, 170, 150), (8, 14), 1)
    pygame.draw.circle(s, (255, 170, 150), (24, 14), 1)
    return s


def _sproutlet():
    s = _canvas(32, 32)
    green, dark, light = (112, 196, 92), (64, 140, 64), (176, 230, 150)
    pygame.draw.line(s, dark, (16, 13), (16, 8), 2)
    pygame.draw.polygon(s, (90, 180, 80), [(16, 8), (6, 2), (5, 6), (11, 10)])
    pygame.draw.polygon(s, (90, 180, 80), [(16, 8), (27, 1), (28, 5), (21, 10)])
    pygame.draw.line(s, dark, (16, 8), (8, 4))
    pygame.draw.line(s, dark, (16, 8), (25, 3))
    pygame.draw.ellipse(s, dark, (9, 27, 6, 4))
    pygame.draw.ellipse(s, dark, (17, 27, 6, 4))
    pygame.draw.ellipse(s, green, (6, 11, 20, 19))
    pygame.draw.ellipse(s, light, (11, 19, 10, 9))
    _eye(s, 11, 16)
    _eye(s, 19, 16)
    pygame.draw.circle(s, (250, 150, 160), (9, 20), 1)
    pygame.draw.circle(s, (250, 150, 160), (23, 20), 1)
    pygame.draw.arc(s, (40, 80, 40), (13, 17, 6, 5), math.pi * 1.1, math.pi * 1.9)
    return s


def _guardillo():
    s = _canvas(32, 32)
    shell, dark, skin = (110, 140, 180), (70, 92, 130), (214, 190, 160)
    pygame.draw.rect(s, (150, 120, 100), (8, 25, 4, 4))
    pygame.draw.rect(s, (150, 120, 100), (18, 25, 4, 4))
    pygame.draw.polygon(s, skin, [(4, 22), (0, 25), (5, 24)])
    pygame.draw.ellipse(s, shell, (3, 8, 24, 20))
    for x in (9, 14, 19):
        pygame.draw.arc(s, dark, (x - 6, 8, 12, 22), -0.6, 0.6, 1)
    pygame.draw.line(s, dark, (6, 23), (24, 23))
    pygame.draw.ellipse(s, (160, 190, 220), (8, 10, 10, 5))
    pygame.draw.circle(s, (40, 44, 70), (14, 16), 2)           # keyhole marking
    pygame.draw.polygon(s, (40, 44, 70), [(13, 17), (15, 17), (16, 21), (12, 21)])
    pygame.draw.circle(s, skin, (25, 19), 6)
    pygame.draw.polygon(s, skin, [(23, 13), (25, 8), (27, 13)])
    pygame.draw.rect(s, (200, 150, 140), (29, 19, 2, 2))
    _eye(s, 25, 17)
    return s


def _owlend():
    s = _canvas(32, 32)
    body, dark, belly = (128, 92, 150), (88, 60, 110), (226, 210, 236)
    pygame.draw.polygon(s, dark, [(7, 6), (9, 0), (12, 5)])
    pygame.draw.polygon(s, dark, [(25, 6), (23, 0), (20, 5)])
    pygame.draw.ellipse(s, body, (6, 3, 20, 26))
    pygame.draw.ellipse(s, dark, (3, 12, 7, 13))
    pygame.draw.ellipse(s, dark, (22, 12, 7, 13))
    pygame.draw.ellipse(s, belly, (10, 14, 12, 13))
    for ex in (12, 20):
        pygame.draw.circle(s, (244, 170, 50), (ex, 9), 4)
        pygame.draw.circle(s, (255, 255, 255), (ex, 9), 3)
        pygame.draw.rect(s, (25, 20, 30), (ex - 1, 8, 2, 3))
    pygame.draw.polygon(s, (244, 160, 40), [(15, 12), (17, 12), (16, 15)])
    pygame.draw.circle(s, (240, 190, 50), (16, 19), 3)          # coin marking
    pygame.draw.circle(s, (180, 130, 30), (16, 19), 3, 1)
    pygame.draw.rect(s, (252, 250, 240), (17, 22, 10, 7))       # folded IOU
    pygame.draw.line(s, (180, 180, 190), (22, 22), (22, 28))
    pygame.draw.line(s, (200, 60, 60), (18, 24), (21, 24))
    pygame.draw.line(s, (120, 120, 140), (23, 24), (26, 24))
    pygame.draw.line(s, (120, 120, 140), (18, 26), (21, 26))
    pygame.draw.line(s, (244, 160, 40), (12, 29), (12, 31))
    pygame.draw.line(s, (244, 160, 40), (19, 29), (19, 31))
    return s


def _stashrew():
    s = _canvas(32, 32)
    fur, dark, light = (150, 120, 100), (104, 80, 66), (214, 196, 176)
    pygame.draw.line(s, dark, (5, 24), (0, 19), 2)              # thin tail
    pygame.draw.ellipse(s, fur, (4, 15, 20, 13))
    pygame.draw.ellipse(s, light, (9, 20, 12, 7))
    pygame.draw.ellipse(s, fur, (13, 7, 15, 14))
    pygame.draw.polygon(s, fur, [(26, 12), (31, 15), (26, 17)])  # pointy snout
    pygame.draw.circle(s, (230, 120, 130), (31, 15), 1)
    pygame.draw.circle(s, fur, (16, 8), 3)
    pygame.draw.circle(s, (220, 150, 150), (16, 8), 1)
    pygame.draw.circle(s, (246, 200, 70), (21, 17), 4)          # coin-stuffed cheek pouch
    pygame.draw.circle(s, (190, 140, 30), (21, 17), 4, 1)
    pygame.draw.circle(s, (255, 236, 150), (20, 16), 1)
    _eye(s, 22, 11)
    pygame.draw.ellipse(s, dark, (7, 26, 5, 3))
    pygame.draw.ellipse(s, dark, (16, 26, 5, 3))
    return s


def _tabbit():
    s = _canvas(32, 32)
    fur, shade, paper = (238, 234, 226), (196, 188, 178), (252, 252, 246)
    for ex in (10, 18):                                         # receipt-like ears
        pygame.draw.rect(s, paper, (ex, 0, 5, 13))
        for zx in range(ex, ex + 5, 2):
            s.set_at((zx, 0), (0, 0, 0, 0))
        for ly in (3, 6, 9):
            pygame.draw.line(s, (150, 150, 165), (ex + 1, ly), (ex + 3, ly))
    pygame.draw.ellipse(s, fur, (7, 10, 18, 14))
    pygame.draw.ellipse(s, fur, (6, 18, 20, 13))
    pygame.draw.ellipse(s, shade, (6, 27, 8, 4))
    pygame.draw.ellipse(s, shade, (18, 27, 8, 4))
    _eye(s, 11, 15)
    _eye(s, 19, 15)
    pygame.draw.rect(s, (230, 140, 150), (15, 18, 2, 1))
    pygame.draw.line(s, (120, 80, 50), (8, 20), (23, 25))       # pouch strap
    pygame.draw.rect(s, (70, 130, 90), (17, 22, 8, 7))          # ledger pouch
    pygame.draw.line(s, (220, 230, 210), (19, 24), (23, 24))
    pygame.draw.line(s, (220, 230, 210), (19, 26), (23, 26))
    return s


def _acornest():
    s = _canvas(32, 32)
    shell, dark, cap = (190, 130, 70), (140, 92, 48), (110, 76, 46)
    for fx in (11, 19):                                         # root feet
        pygame.draw.line(s, (120, 84, 50), (fx, 25), (fx - 2, 30), 2)
        pygame.draw.line(s, (120, 84, 50), (fx, 25), (fx + 2, 30), 2)
    pygame.draw.ellipse(s, shell, (8, 9, 16, 19))
    pygame.draw.ellipse(s, dark, (8, 20, 16, 8))
    pygame.draw.ellipse(s, shell, (9, 9, 14, 16))
    pygame.draw.ellipse(s, cap, (6, 4, 20, 10))
    for cx in range(8, 25, 3):
        pygame.draw.line(s, (80, 56, 34), (cx, 6), (cx + 2, 12))
    pygame.draw.line(s, (90, 64, 40), (16, 4), (17, 0), 2)
    pygame.draw.polygon(s, (90, 176, 80), [(8, 17), (1, 13), (3, 20)])   # leafy arms
    pygame.draw.polygon(s, (90, 176, 80), [(24, 17), (31, 13), (29, 20)])
    _eye(s, 12, 16)
    _eye(s, 19, 16)
    pygame.draw.arc(s, (80, 50, 30), (13, 18, 6, 4), math.pi * 1.1, math.pi * 1.9, 1)
    return s


def _phishfin():
    s = _canvas(32, 32)
    body, dark, belly = (60, 120, 160), (36, 80, 116), (150, 200, 220)
    pygame.draw.polygon(s, dark, [(6, 19), (0, 12), (1, 26)])
    pygame.draw.polygon(s, dark, [(11, 12), (15, 7), (18, 12)])
    pygame.draw.ellipse(s, body, (4, 11, 23, 16))
    pygame.draw.ellipse(s, belly, (9, 20, 15, 6))
    pygame.draw.polygon(s, dark, [(14, 22), (11, 28), (17, 24)])
    pygame.draw.line(s, (90, 80, 70), (21, 12), (22, 5))        # lure stalk
    pygame.draw.line(s, (90, 80, 70), (22, 5), (27, 4))
    pygame.draw.circle(s, (250, 210, 60), (28, 6), 3)           # shiny coin-like lure
    pygame.draw.circle(s, (190, 140, 30), (28, 6), 3, 1)
    s.set_at((27, 5), (255, 255, 230))
    pygame.draw.rect(s, (255, 255, 255), (20, 15, 4, 3))
    pygame.draw.rect(s, (25, 20, 30), (21, 15, 2, 2))
    pygame.draw.line(s, (20, 30, 40), (21, 22), (27, 20))       # wide mouth
    for tx in (22, 24, 26):
        s.set_at((tx, 21), (255, 255, 255))
    return s


_MINTLING_ART = {
    "coincub": _coincub, "owlend": _owlend, "sproutlet": _sproutlet, "stashrew": _stashrew,
    "tabbit": _tabbit, "acornest": _acornest, "guardillo": _guardillo, "phishfin": _phishfin,
}


def mintling(species_id, size=128, flip=False, silhouette=False):
    key = ("m", species_id, size, flip, silhouette)
    if key not in _cache:
        base = _outline(_MINTLING_ART[species_id]())
        if silhouette:
            mask = pygame.mask.from_surface(base)
            base = mask.to_surface(setcolor=(60, 60, 80), unsetcolor=(0, 0, 0, 0))
        img = _scale(base, size / 32)
        if flip:
            img = pygame.transform.flip(img, True, False)
        _cache[key] = img
    return _cache[key]


# =========================================================================== people (16x16)
PLAYER_LOOK = ((214, 64, 56), (70, 44, 30), (238, 196, 160))
PENNY_LOOK = ((245, 245, 245), (176, 84, 40), (240, 204, 170))


def person(look, facing="down", step=0, hat=None):
    key = ("p", look, facing, step, hat)
    if key in _cache:
        return _cache[key]
    shirt, hair, skin = look
    s = _canvas(16, 16)
    pygame.draw.ellipse(s, (0, 0, 0, 60), (3, 13, 10, 3))
    legs = (52, 56, 80)
    if step == 0:
        pygame.draw.rect(s, legs, (5, 11, 2, 3))
        pygame.draw.rect(s, legs, (9, 11, 2, 3))
    else:
        pygame.draw.rect(s, legs, (5, 11, 2, 2 if step == 1 else 3))
        pygame.draw.rect(s, legs, (9, 11, 2, 3 if step == 1 else 2))
    pygame.draw.rect(s, shirt, (4, 7, 8, 5), border_radius=1)
    if facing in ("down", "up"):
        pygame.draw.rect(s, skin, (3, 8, 1, 3))
        pygame.draw.rect(s, skin, (12, 8, 1, 3))
    pygame.draw.rect(s, skin, (4, 1, 8, 7), border_radius=2)
    if facing == "down":
        pygame.draw.rect(s, hair, (4, 1, 8, 2))
        pygame.draw.rect(s, hair, (4, 3, 1, 2))
        pygame.draw.rect(s, hair, (11, 3, 1, 2))
        s.set_at((6, 5), (30, 25, 35))
        s.set_at((9, 5), (30, 25, 35))
    elif facing == "up":
        pygame.draw.rect(s, hair, (4, 1, 8, 6), border_radius=2)
    elif facing == "left":
        pygame.draw.rect(s, hair, (4, 1, 8, 2))
        pygame.draw.rect(s, hair, (8, 3, 4, 4))
        s.set_at((5, 5), (30, 25, 35))
    else:
        pygame.draw.rect(s, hair, (4, 1, 8, 2))
        pygame.draw.rect(s, hair, (4, 3, 4, 4))
        s.set_at((10, 5), (30, 25, 35))
    if hat:
        pygame.draw.rect(s, hat, (3, 0, 10, 2))
        if facing == "down":
            pygame.draw.rect(s, hat, (4, 2, 8, 1))
        elif facing == "left":
            pygame.draw.rect(s, hat, (2, 2, 4, 1))
        elif facing == "right":
            pygame.draw.rect(s, hat, (10, 2, 4, 1))
    img = _scale(_outline(s), SCALE)
    _cache[key] = img
    return img


def portrait(kind, size=192):
    """Large character art for dialogue and the intro (48x64 canvas)."""
    key = ("portrait", kind, size)
    if key in _cache:
        return _cache[key]
    s = _canvas(48, 64)
    if kind == "penny":
        skin, hair, coat, shirt = (240, 204, 170), (176, 84, 40), (248, 248, 248), (60, 150, 140)
    elif kind == "rival":
        skin, hair, coat, shirt = (240, 200, 170), (200, 80, 40), (60, 90, 200), (240, 240, 240)
    else:
        skin, hair, coat, shirt = PLAYER_LOOK[2], PLAYER_LOOK[1], PLAYER_LOOK[0], (240, 240, 240)
    pygame.draw.rect(s, coat, (8, 34, 32, 30), border_radius=6)
    pygame.draw.polygon(s, shirt, [(19, 34), (29, 34), (24, 46)])
    pygame.draw.rect(s, skin, (20, 28, 8, 8))
    pygame.draw.ellipse(s, skin, (12, 8, 24, 26))
    if kind == "penny":
        pygame.draw.circle(s, hair, (24, 5), 6)
        pygame.draw.ellipse(s, hair, (10, 6, 28, 12))
        pygame.draw.rect(s, hair, (10, 10, 4, 14))
        pygame.draw.rect(s, hair, (34, 10, 4, 14))
        pygame.draw.circle(s, (60, 60, 70), (19, 20), 4, 1)
        pygame.draw.circle(s, (60, 60, 70), (29, 20), 4, 1)
        pygame.draw.line(s, (60, 60, 70), (23, 20), (25, 20))
        pygame.draw.circle(s, (230, 170, 60), (14, 44), 3)   # coin pin
        for x in (14, 34):
            pygame.draw.line(s, (210, 210, 215), (x, 36), (x, 62))
    elif kind == "rival":
        pygame.draw.polygon(s, hair, [(10, 16), (14, 4), (20, 9), (25, 2), (30, 9), (36, 4), (38, 16)])
    else:
        pygame.draw.ellipse(s, hair, (11, 6, 26, 12))
        pygame.draw.rect(s, (214, 64, 56), (10, 6, 28, 6), border_radius=3)
        pygame.draw.rect(s, (214, 64, 56), (24, 10, 14, 3))
    for x in (19, 29):
        pygame.draw.rect(s, (30, 25, 35), (x - 1, 19, 3, 3))
        s.set_at((x - 1, 19), (255, 255, 255))
    pygame.draw.arc(s, (150, 70, 60), (20, 23, 8, 5), math.pi * 1.1, math.pi * 1.9, 1)
    pygame.draw.circle(s, (250, 160, 150), (16, 25), 2)
    pygame.draw.circle(s, (250, 160, 150), (32, 25), 2)
    img = _scale(_outline(s), size / 64)
    _cache[key] = img
    return img


# =========================================================================== tiles (16x16)
def _tile_rng(x, y, n):
    return (x * 73856093 ^ y * 19349663) % n


def _grass(s, x, y):
    s.fill((124, 192, 92))
    for i in range(3):
        px = (_tile_rng(x, y + i * 7, 13) + i * 5) % 14 + 1
        py = (_tile_rng(x + i * 3, y, 11) + i * 4) % 13 + 2
        s.set_at((px, py), (96, 164, 72))
        s.set_at((px + 1, py - 1), (96, 164, 72))


def draw_tile(ch, x, y):
    s = _canvas(ART_TILE, ART_TILE)
    if ch == "=":
        s.fill((226, 204, 152))
        for i in range(4):
            s.set_at(((_tile_rng(x, y + i, 15) + i * 4) % 16, (_tile_rng(x + i, y, 15) + i * 3) % 16),
                     (200, 176, 124))
    elif ch in ",;":
        pond = ch == ";"          # pondside grass is a little bluer than meadow grass
        s.fill((72, 156, 110) if pond else (88, 164, 72))
        blade = (38, 112, 88) if pond else (52, 122, 52)
        tip = (150, 220, 190) if pond else (150, 210, 110)
        for bx in range(1, 16, 4):
            off = (bx + y) % 2
            pygame.draw.polygon(s, blade, [(bx, 15), (bx + 1, 6 + off), (bx + 3, 15)])
            pygame.draw.polygon(s, blade, [(bx + 1, 9), (bx + 2, 1 + off), (bx + 3, 9)])
            s.set_at((bx + 1, 6 + off), tip)
            s.set_at((bx + 2, 1 + off), tip)
    elif ch == "~":
        s.fill((72, 140, 214))
        for wy in (4, 11):
            ox = (x * 5 + wy) % 6
            pygame.draw.line(s, (150, 200, 240), (ox, wy), (ox + 4, wy))
            pygame.draw.line(s, (150, 200, 240), (ox + 8, wy + 2), (ox + 11, wy + 2))
    else:
        _grass(s, x, y)
        if ch == "T":
            pygame.draw.rect(s, (110, 72, 40), (6, 10, 4, 6))
            pygame.draw.circle(s, (34, 104, 56), (8, 7), 7)
            pygame.draw.circle(s, (54, 140, 70), (6, 5), 4)
            pygame.draw.circle(s, (80, 170, 90), (5, 4), 1)
            pygame.draw.circle(s, (22, 80, 44), (8, 7), 7, 1)
        elif ch == "f":
            colours = [(240, 90, 100), (250, 220, 80), (250, 250, 250), (180, 120, 230)]
            for i in range(3):
                fx = (_tile_rng(x, y + i, 12) + i * 4) % 12 + 2
                fy = (_tile_rng(x + i, y, 12) + i * 5) % 12 + 2
                c = colours[(x + y + i) % 4]
                for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
                    s.set_at((fx + dx, fy + dy), c)
                s.set_at((fx, fy), (250, 200, 60))
        elif ch == "F":
            pygame.draw.rect(s, (176, 124, 76), (0, 6, 16, 2))
            pygame.draw.rect(s, (176, 124, 76), (0, 10, 16, 2))
            for px in (2, 12):
                pygame.draw.rect(s, (140, 92, 52), (px, 4, 3, 10))
        elif ch == "S":
            pygame.draw.rect(s, (120, 80, 50), (7, 9, 2, 6))
            pygame.draw.rect(s, (196, 146, 86), (2, 2, 12, 8), border_radius=1)
            pygame.draw.rect(s, (120, 80, 50), (2, 2, 12, 8), 1, border_radius=1)
            for ly in (4, 6):
                pygame.draw.line(s, (120, 80, 50), (4, ly), (11, ly))
        elif ch == "B":
            pygame.draw.rect(s, (120, 80, 50), (2, 9, 2, 6))
            pygame.draw.rect(s, (120, 80, 50), (12, 9, 2, 6))
            pygame.draw.rect(s, (150, 104, 64), (1, 1, 14, 10))
            pygame.draw.rect(s, (250, 250, 240), (3, 3, 4, 5))
            pygame.draw.rect(s, (250, 240, 170), (8, 2, 5, 4))
            pygame.draw.rect(s, (220, 60, 60), (10, 7, 3, 3))
    return s


def building(b):
    """Render a building at art scale (unscaled)."""
    w, h = b["w"] * ART_TILE, b["h"] * ART_TILE
    s = _canvas(w, h)
    roof_h = int(h * 0.48)
    wall = b["wall"]
    roof = b["roof"]
    dark_roof = tuple(max(0, c - 50) for c in roof)
    pygame.draw.rect(s, wall, (2, roof_h - 2, w - 4, h - roof_h + 2))
    pygame.draw.rect(s, tuple(max(0, c - 40) for c in wall), (2, h - 3, w - 4, 3))
    pygame.draw.polygon(s, roof, [(0, roof_h), (6, 2), (w - 6, 2), (w, roof_h)])
    for yy in range(6, roof_h, 5):
        pygame.draw.line(s, dark_roof, (3, yy), (w - 3, yy))
    pygame.draw.polygon(s, OUTLINE, [(0, roof_h), (6, 2), (w - 6, 2), (w, roof_h)], 1)
    # windows
    for wx in range(8, w - 12, 20):
        door_cols = [(dx - b["x"]) * ART_TILE for dx, _ in b["doors"]]
        if any(abs(wx + 4 - (c + 8)) < 14 for c in door_cols):
            continue
        pygame.draw.rect(s, (130, 190, 230), (wx, roof_h + 5, 9, 8))
        pygame.draw.rect(s, (90, 70, 60), (wx, roof_h + 5, 9, 8), 1)
        pygame.draw.line(s, (90, 70, 60), (wx + 4, roof_h + 5), (wx + 4, roof_h + 12))
    for dx, dy in b["doors"]:
        px = (dx - b["x"]) * ART_TILE
        py = (dy - b["y"]) * ART_TILE
        pygame.draw.rect(s, (100, 64, 40), (px + 3, py + 3, 10, 13))
        pygame.draw.rect(s, (60, 40, 30), (px + 3, py + 3, 10, 13), 1)
        s.set_at((px + 10, py + 10), (240, 200, 80))
    pygame.draw.rect(s, OUTLINE, (2, roof_h - 2, w - 4, h - roof_h + 2), 1)
    return s


# =========================================================================== items and misc
def item_icon(item_id, size=48):
    key = ("item", item_id, size)
    if key in _cache:
        return _cache[key]
    s = _canvas(16, 16)
    if item_id in ("potion", "super_potion"):
        liquid = (240, 110, 150) if item_id == "potion" else (150, 100, 230)
        pygame.draw.rect(s, (200, 200, 210), (6, 1, 4, 3))
        pygame.draw.rect(s, (230, 240, 250), (4, 4, 8, 11), border_radius=3)
        pygame.draw.rect(s, liquid, (5, 8, 6, 6), border_radius=2)
        s.set_at((6, 6), (255, 255, 255))
    elif item_id == "revive":
        pygame.draw.polygon(s, (250, 210, 60), [(8, 1), (14, 8), (8, 15), (2, 8)])
        pygame.draw.polygon(s, (255, 245, 180), [(8, 4), (11, 8), (8, 12), (5, 8)])
    else:
        capsule(s)
    img = _scale(_outline(s), size / 16)
    _cache[key] = img
    return img


def capsule(s=None, size=None):
    if s is None:
        key = ("capsule", size)
        if key in _cache:
            return _cache[key]
        s = _canvas(16, 16)
        capsule(s)
        img = _scale(_outline(s), (size or 48) / 16)
        _cache[key] = img
        return img
    # A pill-shaped capsule: mint half, cream half, with a little leaf.
    pygame.draw.rect(s, (252, 248, 236), (1, 6, 14, 8), border_radius=4)
    pygame.draw.rect(s, (90, 206, 160), (1, 6, 7, 8), border_top_left_radius=4, border_bottom_left_radius=4)
    pygame.draw.line(s, (40, 120, 90), (8, 6), (8, 13))
    pygame.draw.line(s, (180, 240, 210), (3, 8), (5, 8))
    pygame.draw.ellipse(s, (70, 170, 80), (8, 1, 6, 4))
    pygame.draw.line(s, (40, 110, 50), (8, 5), (12, 2))
    return s


def coin(radius):
    key = ("coin", radius)
    if key in _cache:
        return _cache[key]
    d = radius * 2 + 4
    s = _canvas(d, d)
    c = (radius + 2, radius + 2)
    pygame.draw.circle(s, (150, 100, 20), c, radius + 2)
    pygame.draw.circle(s, (240, 190, 50), c, radius)
    pygame.draw.circle(s, (200, 145, 30), c, int(radius * 0.72), max(2, radius // 8))
    pygame.draw.circle(s, (255, 230, 130), (c[0] - radius // 3, c[1] - radius // 3), max(2, radius // 6))
    _cache[key] = s
    return s
