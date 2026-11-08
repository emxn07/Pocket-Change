"""Shared UI building blocks: theme, fonts, text, panels, menus and input mapping.

Every interactive list is a Menu, so every screen gets the same keyboard
focus, mouse hover/click and read-aloud behaviour.
"""
import pygame

from ..data.types import TYPE_COLOURS

# --------------------------------------------------------------------------- theme
NORMAL_THEME = dict(
    bg=(28, 34, 54), panel=(250, 246, 232), panel_alt=(238, 232, 212), border=(44, 50, 78),
    text=(32, 36, 58), muted=(92, 96, 118), accent=(214, 160, 30), focus=(226, 130, 20),
    focus_bg=(255, 232, 170), good=(28, 128, 64), bad=(186, 44, 44), disabled=(150, 150, 150),
    on_dark=(246, 246, 250), title=(252, 210, 80), hp_bg=(70, 70, 80), shadow=(0, 0, 0, 90),
    dim=(10, 12, 24, 150),
)
CONTRAST_THEME = dict(
    bg=(0, 0, 0), panel=(0, 0, 0), panel_alt=(24, 24, 24), border=(255, 255, 255),
    text=(255, 255, 255), muted=(235, 235, 235), accent=(255, 230, 0), focus=(255, 230, 0),
    focus_bg=(70, 60, 0), good=(120, 255, 150), bad=(255, 150, 150), disabled=(190, 190, 190),
    on_dark=(255, 255, 255), title=(255, 230, 0), hp_bg=(60, 60, 60), shadow=(0, 0, 0, 0),
    dim=(0, 0, 0, 200),
)

FONT_SIZES = {"tiny": 20, "small": 24, "body": 28, "heading": 36, "title": 54, "big": 92}


class Fonts:
    def __init__(self, settings):
        self.settings = settings
        self._cache = {}

    def get(self, role, scaled=True):
        scale = self.settings.text_scale if scaled else 1.0
        size = int(FONT_SIZES[role] * scale)
        if size not in self._cache:
            self._cache[size] = pygame.font.Font(None, size)
        return self._cache[size]


# --------------------------------------------------------------------------- input
def action_of(event):
    """Map a pygame event to a game action name (keyboard)."""
    if event.type != pygame.KEYDOWN:
        return None
    k = event.key
    if k in (pygame.K_UP, pygame.K_w):
        return "up"
    if k in (pygame.K_DOWN, pygame.K_s):
        return "down"
    if k in (pygame.K_LEFT, pygame.K_a):
        return "left"
    if k in (pygame.K_RIGHT, pygame.K_d):
        return "right"
    if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE, pygame.K_z):
        return "confirm"
    if k in (pygame.K_ESCAPE, pygame.K_x, pygame.K_BACKSPACE):
        return "back"
    if k == pygame.K_g:
        return "terms"
    if k in (pygame.K_TAB, pygame.K_p):
        return "menu"
    return None


def is_click(event):
    return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1


def is_right_click(event):
    return event.type == pygame.MOUSEBUTTONDOWN and event.button == 3


# --------------------------------------------------------------------------- text
def wrap(text, font, width):
    lines = []
    for para in str(text).split("\n"):
        words = para.split(" ")
        line = ""
        for word in words:
            test = word if not line else line + " " + word
            if font.size(test)[0] <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                while font.size(word)[0] > width and len(word) > 1:   # hard-break very long words
                    cut = len(word)
                    while cut > 1 and font.size(word[:cut])[0] > width:
                        cut -= 1
                    lines.append(word[:cut])
                    word = word[cut:]
                line = word
        lines.append(line)
    return lines


def draw_text(surf, text, font, colour, pos, anchor="topleft"):
    img = font.render(str(text), True, colour)
    rect = img.get_rect(**{anchor: pos})
    surf.blit(img, rect)
    return rect


def draw_wrapped(surf, text, font, colour, rect, line_gap=4):
    """Draw wrapped text inside rect (x, y, width used). Returns the height used."""
    rect = pygame.Rect(rect)
    y = rect.y
    for line in wrap(text, font, rect.w):
        surf.blit(font.render(line, True, colour), (rect.x, y))
        y += font.get_linesize() + line_gap
    return y - rect.y


def text_height(text, font, width, line_gap=4):
    return len(wrap(text, font, width)) * (font.get_linesize() + line_gap)


# --------------------------------------------------------------------------- drawing
def draw_panel(surf, rect, theme, fill=None, border=None, radius=12, width=3):
    rect = pygame.Rect(rect)
    if theme["shadow"][3]:
        shadow = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(shadow, theme["shadow"], shadow.get_rect(), border_radius=radius)
        surf.blit(shadow, (rect.x + 4, rect.y + 5))
    pygame.draw.rect(surf, fill or theme["panel"], rect, border_radius=radius)
    pygame.draw.rect(surf, border or theme["border"], rect, width, border_radius=radius)
    return rect


def dim(surf, theme):
    shade = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    shade.fill(theme["dim"])
    surf.blit(shade, (0, 0))


def draw_marker(surf, colour, x, cy, size=9):
    """A right-pointing triangle: focus is never shown by colour alone."""
    pygame.draw.polygon(surf, colour, [(x, cy - size), (x + size, cy), (x, cy + size)])


def draw_hp_bar(surf, rect, hp, max_hp, theme, font=None, show_numbers=True):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surf, theme["hp_bg"], rect, border_radius=4)
    frac = 0 if max_hp <= 0 else max(0.0, min(1.0, hp / max_hp))
    if frac > 0.5:
        colour = (60, 190, 90)
    elif frac > 0.2:
        colour = (240, 190, 40)
    else:
        colour = (220, 60, 50)
    inner = rect.inflate(-4, -4)
    inner.w = int(inner.w * frac)
    if inner.w > 0:
        pygame.draw.rect(surf, colour, inner, border_radius=3)
    pygame.draw.rect(surf, theme["border"], rect, 2, border_radius=4)
    if show_numbers and font:
        draw_text(surf, f"HP {int(round(hp))}/{max_hp}", font, theme["text"], (rect.right, rect.bottom + 2), "topright")


def draw_type_badge(surf, mtype, font, pos, anchor="topleft"):
    """Type badges show the type name in text as well as colour."""
    label = mtype or "No type"
    img = font.render(label.upper(), True, (255, 255, 255))
    rect = img.get_rect()
    rect.inflate_ip(16, 8)
    setattr(rect, anchor, pos)
    pygame.draw.rect(surf, TYPE_COLOURS.get(mtype, TYPE_COLOURS[None]), rect, border_radius=8)
    pygame.draw.rect(surf, (20, 20, 30), rect, 2, border_radius=8)
    surf.blit(img, img.get_rect(center=rect.center))
    return rect


def draw_hints(surf, game, hints):
    """Bottom bar with key hints, e.g. [("Enter", "Select"), ("Esc", "Back")]."""
    theme = game.theme
    font = game.fonts.get("tiny", scaled=False)
    bar = pygame.Rect(0, surf.get_height() - 30, surf.get_width(), 30)
    pygame.draw.rect(surf, (12, 14, 26) if not game.settings.high_contrast else (0, 0, 0), bar)
    pygame.draw.line(surf, theme["accent"], bar.topleft, bar.topright, 2)
    x = 12
    for key, label in hints + [("R", "Read aloud"), ("T", "Stop")]:
        kimg = font.render(key, True, (20, 20, 30))
        krect = kimg.get_rect().inflate(10, 4)
        krect.topleft = (x, bar.y + 6)
        pygame.draw.rect(surf, (240, 220, 150), krect, border_radius=4)
        surf.blit(kimg, kimg.get_rect(center=krect.center))
        x = krect.right + 6
        limg = font.render(label, True, (240, 240, 245))
        surf.blit(limg, (x, bar.y + 8))
        x += limg.get_width() + 18
        if x > bar.right - 60:
            break


# --------------------------------------------------------------------------- menu
_UNSET = object()


class MenuItem:
    def __init__(self, label, value=_UNSET, enabled=True, note=None, speech=None):
        self.label = label
        # None is a real value (e.g. "Don't learn"); only a missing value falls back to the label.
        self.value = label if value is _UNSET else value
        self.enabled = enabled
        self.note = note            # shown after the label (e.g. why it's unavailable)
        self.speech = speech


class Menu:
    """A keyboard + mouse list. handle() returns ("select", value), ("back", None) or None."""

    def __init__(self, game, items, columns=1, font_role="body", cancel=True, on_focus=None,
                 announce=True, horizontal=False):
        self.game = game
        self.items = [i if isinstance(i, MenuItem) else MenuItem(*i) if isinstance(i, tuple) else MenuItem(i)
                      for i in items]
        self.columns = len(self.items) if horizontal else columns
        self.font_role = font_role
        self.cancel = cancel
        self.on_focus = on_focus
        self.announce_focus = announce
        self.focus = 0
        self.scroll = 0
        self.rects = []
        self._first = True
        if self.items and not self.items[0].enabled:
            enabled = [i for i, it in enumerate(self.items) if it.enabled]
            if enabled:
                self.focus = enabled[0]

    @property
    def current(self):
        return self.items[self.focus] if self.items else None

    def set_focus(self, i, sound=True):
        if not self.items:
            return
        i = max(0, min(len(self.items) - 1, i))
        if i != self.focus:
            self.focus = i
            if sound:
                self.game.audio.play("move")
            item = self.items[i]
            if self.announce_focus:
                self.game.announce(self.item_speech(item))
            if self.on_focus:
                self.on_focus(item)

    @staticmethod
    def item_speech(item):
        text = item.speech or item.label
        if item.note:
            text += ". " + item.note
        if not item.enabled:
            text += ". Unavailable."
        return text

    def item_height(self):
        font = self.game.fonts.get(self.font_role)
        return font.get_linesize() + 18

    def handle(self, event):
        act = action_of(event)
        n = len(self.items)
        if act and n:
            cols = self.columns
            if act == "up":
                self.set_focus(self.focus - cols if self.focus - cols >= 0 else self.focus)
            elif act == "down":
                self.set_focus(self.focus + cols if self.focus + cols < n else self.focus)
            elif act == "left" and cols > 1:
                self.set_focus(self.focus - 1)
            elif act == "right" and cols > 1:
                self.set_focus(self.focus + 1)
            elif act == "confirm":
                return self._select()
            elif act == "back" and self.cancel:
                self.game.audio.play("back")
                return ("back", None)
        elif event.type == pygame.MOUSEMOTION:
            for i, r in self.rects:
                if r.collidepoint(event.pos):
                    self.set_focus(i, sound=i != self.focus)
        elif is_click(event):
            for i, r in self.rects:
                if r.collidepoint(event.pos):
                    self.set_focus(i, sound=False)
                    return self._select()
        elif is_right_click(event) and self.cancel:
            return ("back", None)
        elif event.type == pygame.MOUSEWHEEL:
            self.set_focus(self.focus - event.y)
        return None

    def _select(self):
        item = self.current
        if item is None:
            return None
        if not item.enabled:
            self.game.audio.play("bump")
            self.game.announce(self.item_speech(item))
            return None
        self.game.audio.play("select")
        return ("select", item.value)

    def draw(self, surf, rect, theme=None):
        theme = theme or self.game.theme
        rect = pygame.Rect(rect)
        font = self.game.fonts.get(self.font_role)
        small = self.game.fonts.get("small")
        cols = self.columns
        gap = 8
        col_w = (rect.w - gap * (cols - 1)) // cols
        h = self.item_height()
        rows_visible = max(1, (rect.h + gap) // (h + gap))
        row = self.focus // cols
        if row < self.scroll:
            self.scroll = row
        elif row >= self.scroll + rows_visible:
            self.scroll = row - rows_visible + 1
        total_rows = (len(self.items) + cols - 1) // cols
        self.scroll = max(0, min(self.scroll, max(0, total_rows - rows_visible)))
        self.rects = []
        for i, item in enumerate(self.items):
            r_i, c_i = divmod(i, cols)
            if not (self.scroll <= r_i < self.scroll + rows_visible):
                continue
            r = pygame.Rect(rect.x + c_i * (col_w + gap), rect.y + (r_i - self.scroll) * (h + gap), col_w, h)
            self.rects.append((i, r))
            focused = i == self.focus
            pygame.draw.rect(surf, theme["focus_bg"] if focused else theme["panel_alt"], r, border_radius=8)
            pygame.draw.rect(surf, theme["focus"] if focused else theme["border"], r, 4 if focused else 1,
                             border_radius=8)
            colour = theme["text"] if item.enabled else theme["disabled"]
            tx = r.x + 14
            if focused:
                draw_marker(surf, theme["focus"] if not self.game.settings.high_contrast else theme["text"],
                            r.x + 8, r.centery, 7)
                tx = r.x + 24
            label = item.label
            avail = r.w - (tx - r.x) - 10
            note_img = None
            if item.note:
                # the label always wins: the note is only shown if both fit
                note_img = small.render(item.note, True, theme["muted"] if item.enabled else theme["disabled"])
                if font.size(label)[0] + note_img.get_width() + 16 > avail:
                    note_img = None
            if note_img:
                avail -= note_img.get_width() + 10
            if font.size(label)[0] > avail:
                while font.size(label + "...")[0] > avail and len(label) > 1:
                    label = label[:-1]
                label = label.rstrip() + "..."
            img = font.render(label, True, colour)
            surf.blit(img, (tx, r.centery - img.get_height() // 2))
            if not item.enabled:
                y = r.centery
                pygame.draw.line(surf, theme["disabled"], (tx, y), (tx + img.get_width(), y), 2)
            if note_img:
                surf.blit(note_img, (r.right - note_img.get_width() - 12, r.centery - note_img.get_height() // 2))
        # scroll indicators (text, not colour)
        if self.scroll > 0:
            draw_text(surf, "More above", small, theme["muted"], (rect.right, rect.y - 2), "bottomright")
        if self.scroll + rows_visible < total_rows:
            draw_text(surf, "More below", small, theme["muted"], (rect.right, rect.bottom + 2), "topright")

    def needed_height(self, rows=None):
        rows = rows if rows is not None else (len(self.items) + self.columns - 1) // self.columns
        return rows * (self.item_height() + 8) - 8


class WrapList(Menu):
    """A single-column Menu whose items wrap onto several lines (used for answers)."""

    def __init__(self, game, items, **kw):
        super().__init__(game, items, columns=1, **kw)

    def _heights(self, width):
        font = self.game.fonts.get(self.font_role)
        return [len(wrap(it.label, font, width - 40)) * font.get_linesize() + 18 for it in self.items]

    def needed_height(self, width=600):
        return sum(self._heights(width)) + 8 * (len(self.items) - 1)

    def draw(self, surf, rect, theme=None, marks=None):
        """marks: optional {index: ("good"|"bad", label)} drawn after answering."""
        theme = theme or self.game.theme
        rect = pygame.Rect(rect)
        font = self.game.fonts.get(self.font_role)
        small = self.game.fonts.get("small")
        heights = self._heights(rect.w)
        # scroll so the focused item is visible
        self.scroll = min(self.scroll, self.focus)
        while sum(heights[self.scroll:self.focus + 1]) + 8 * (self.focus - self.scroll) > rect.h \
                and self.scroll < self.focus:
            self.scroll += 1
        self.rects = []
        y = rect.y
        for i in range(self.scroll, len(self.items)):
            item, h = self.items[i], heights[i]
            if y + h > rect.bottom + 1 and i != self.scroll:
                draw_text(surf, "More below", small, theme["muted"], (rect.right, rect.bottom + 2), "topright")
                break
            r = pygame.Rect(rect.x, y, rect.w, h)
            self.rects.append((i, r))
            focused = i == self.focus
            fill = theme["focus_bg"] if focused else theme["panel_alt"]
            border = theme["focus"] if focused else theme["border"]
            mark = (marks or {}).get(i)
            if mark:
                border = theme[mark[0]]
            pygame.draw.rect(surf, fill, r, border_radius=8)
            pygame.draw.rect(surf, border, r, 4 if (focused or mark) else 1, border_radius=8)
            if focused:
                draw_marker(surf, theme["focus"] if not self.game.settings.high_contrast else theme["text"],
                            r.x + 8, r.y + 9 + font.get_linesize() // 2, 7)
            colour = theme["text"] if item.enabled else theme["disabled"]
            ty = r.y + 9
            text_w = r.w - 40 - (small.size(mark[1])[0] + 16 if mark else 0)
            for line in wrap(item.label, font, text_w):
                surf.blit(font.render(line, True, colour), (r.x + 28, ty))
                ty += font.get_linesize()
            if mark:
                draw_text(surf, mark[1], small, theme[mark[0]], (r.right - 12, r.centery), "midright")
            y += h + 8
        if self.scroll > 0:
            draw_text(surf, "More above", small, theme["muted"], (rect.right, rect.y - 2), "bottomright")


def draw_header(surf, game, title, subtitle=None):
    """Full-screen backdrop with a title bar, used by menu screens."""
    theme = game.theme
    surf.fill(theme["bg"])
    if not game.settings.high_contrast:
        for i in range(0, surf.get_width(), 40):
            pygame.draw.line(surf, (34, 42, 66), (i, 0), (i - 200, surf.get_height()), 14)
    font = game.fonts.get("heading")
    bar = pygame.Rect(0, 0, surf.get_width(), font.get_linesize() + 24)
    pygame.draw.rect(surf, (18, 22, 38) if not game.settings.high_contrast else (0, 0, 0), bar)
    pygame.draw.line(surf, theme["accent"], bar.bottomleft, bar.bottomright, 3)
    draw_text(surf, title, font, theme["title"], (20, bar.centery), "midleft")
    if subtitle:
        draw_text(surf, subtitle, game.fonts.get("small"), theme["on_dark"], (surf.get_width() - 20, bar.centery),
                  "midright")
    return bar.bottom
