"""The explorable world: Copperleaf Town, Route 1 and the gym plaza."""
import random

import pygame

from ..config import SCREEN_W, SCREEN_H, TILE, ART_TILE, CLINIC_NAME
from ..core.battle import make_team
from ..core.mintling import Mintling
from ..data import world
from ..game import Scene
from ..ui import sprites
from ..ui.widgets import action_of, is_click, draw_text, draw_hints
from .common import TypeChartScene
from .tasks import run_npc_task

DIRS = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}
MOVE_TIME = 0.17
PLAYER_HAT = (214, 64, 56)

DEMO_TASKS = {
    "repay": "Demo task: Esc > PocketBank > Guided Mode. Check what you owe and repay it.",
    "battle": "Demo task: walk north (Up) to battle Saver Sam.",
    "scam": "Demo task: take a step. Your phone is about to buzz...",
    "done": "Demo complete! Explore freely. Options > Return to title resets the demo.",
}


class Overworld(Scene):
    def __init__(self, game):
        super().__init__(game)
        self.st = game.state
        self.rng = random.Random()
        self.door_at = {d: b for b in world.BUILDINGS for d in b["doors"]}
        self.building_tiles = set()
        for b in world.BUILDINGS:
            for y in range(b["y"], b["y"] + b["h"]):
                for x in range(b["x"], b["x"] + b["w"]):
                    if (x, y) not in self.door_at:
                        self.building_tiles.add((x, y))
        self.ground = self._render_ground()
        self.tall_overlay = self._tall_overlay()
        x, y = self.st.pos
        self.px, self.py = x * TILE, y * TILE
        self.moving = None
        self.steps = 0
        self.busy = False
        self.alert = None
        self.npc_facing = {}
        self.area = self._area_name(y)
        self.banner_t = 2.5
        self.bump_cd = 0
        self.menu_rect = None
        self.wild_enabled = True

    # ------------------------------------------------------------------ setup/render
    def _render_ground(self):
        art = pygame.Surface((world.W * ART_TILE, world.H * ART_TILE))
        for y, row in enumerate(world.MAP):
            for x, ch in enumerate(row):
                art.blit(sprites.draw_tile(ch, x, y), (x * ART_TILE, y * ART_TILE))
        for b in world.BUILDINGS:
            art.blit(sprites.building(b), (b["x"] * ART_TILE, b["y"] * ART_TILE))
        big = pygame.transform.scale(art, (world.W * TILE, world.H * TILE))
        font = self.game.fonts.get("small", scaled=False)
        for b in world.BUILDINGS:
            dx = sum(d[0] for d in b["doors"]) / len(b["doors"])
            cx = int((dx + 0.5) * TILE)
            cy = int((b["y"] + b["h"] * 0.48) * TILE) + 6
            img = font.render(b["label"], True, (255, 255, 255))
            r = img.get_rect(midtop=(cx, cy)).inflate(14, 6)
            pygame.draw.rect(big, (44, 50, 78), r, border_radius=4)
            pygame.draw.rect(big, (240, 210, 120), r, 2, border_radius=4)
            big.blit(img, img.get_rect(center=r.center))
        return big

    @staticmethod
    def _tall_overlay():
        out = {}
        for ch in world.WILD_TILES:
            t = pygame.transform.scale(sprites.draw_tile(ch, 0, 0), (TILE, TILE))
            out[ch] = t.subsurface((0, TILE // 2, TILE, TILE // 2)).copy()
        return out

    @staticmethod
    def _area_name(y):
        for y0, y1, name in world.AREAS:
            if y0 <= y <= y1:
                return name
        return ""

    # ------------------------------------------------------------------ world queries
    def visible_trainers(self):
        return list(world.TRAINERS)

    def actors(self):
        return [("npc", n) for n in world.NPCS] + [("trainer", t) for t in self.visible_trainers()]

    def actor_at(self, x, y):
        for kind, a in self.actors():
            if a["x"] == x and a["y"] == y:
                return kind, a
        return None

    def tile(self, x, y):
        if 0 <= x < world.W and 0 <= y < world.H:
            return world.MAP[y][x]
        return "T"

    def solid(self, x, y):
        return (self.tile(x, y) in world.BLOCKING or (x, y) in self.building_tiles
                or self.actor_at(x, y) is not None)

    def trainer_defeated(self, t):
        return f"trainer:{t['id']}" in self.st.flags

    @staticmethod
    def trainer_name(t):
        return t["name"]

    # ------------------------------------------------------------------ input
    def handle(self, event):
        if self.busy or self.moving:
            return
        act = action_of(event)
        if act in ("back", "menu") or (is_click(event) and self.menu_rect and self.menu_rect.collidepoint(event.pos)):
            from .menus import PauseMenu
            self.game.audio.play("select")
            self.game.push(PauseMenu(self.game))
        elif act == "confirm":
            self.interact()

    def speech_text(self):
        a = self.st.account
        here = self.tile(*self.st.pos)
        area = self.area + (f", {world.WILD_TILES[here]}" if here in world.WILD_TILES else "")
        text = (f"{area}. Your money: £{a.money}. Amount you owe: £{a.owed}. "
                f"Facing {self.st.facing}.")
        if self.st.demo and self.st.demo_task:
            text = DEMO_TASKS[self.st.demo_task] + " " + text
        return text

    # ------------------------------------------------------------------ movement
    def update(self, dt):
        self.banner_t = max(0, self.banner_t - dt)
        self.bump_cd = max(0, self.bump_cd - dt)
        if self.alert:
            self.alert[1] -= dt
            if self.alert[1] <= 0:
                t = self.alert[0]
                self.alert = None
                self.start_trainer(t)
            return
        if self.moving:
            fx, fy, tx, ty, t = self.moving
            t += dt / MOVE_TIME
            if t >= 1:
                self.moving = None
                self.px, self.py = tx * TILE, ty * TILE
                self.arrive(tx, ty)
            else:
                self.moving = (fx, fy, tx, ty, t)
                self.px = (fx + (tx - fx) * t) * TILE
                self.py = (fy + (ty - fy) * t) * TILE
            return
        if self.busy or self.game.top is not self:
            return
        keys = pygame.key.get_pressed()
        direction = None
        for d, ks in (("up", (pygame.K_UP, pygame.K_w)), ("down", (pygame.K_DOWN, pygame.K_s)),
                      ("left", (pygame.K_LEFT, pygame.K_a)), ("right", (pygame.K_RIGHT, pygame.K_d))):
            if any(keys[k] for k in ks):
                direction = d
                break
        if direction:
            self.try_move(direction)

    def try_move(self, direction):
        self.st.facing = direction
        x, y = self.st.pos
        dx, dy = DIRS[direction]
        nx, ny = x + dx, y + dy
        if self.solid(nx, ny):
            if self.bump_cd <= 0:
                self.game.audio.play("bump")
                self.bump_cd = 0.35
            return
        self.moving = (x, y, nx, ny, 0.0)
        self.steps += 1

    def arrive(self, x, y):
        self.st.pos = [x, y]
        area = self._area_name(y)
        if area != self.area:
            self.area = area
            self.banner_t = 2.5
            self.game.announce(area)
            if self.maybe_reminder(area):
                return
        if (x, y) in self.door_at:
            self.enter_building(self.door_at[(x, y)])
            return
        if self.check_trainers():
            return
        if self.maybe_scam_event():
            return
        tile = self.tile(x, y)
        if tile in world.WILD_TILES and self.st.has_able_mintling() and self.rng.random() < world.ENCOUNTER_RATE:
            self.start_wild(tile)

    # ------------------------------------------------------------------ interactions
    def front(self):
        x, y = self.st.pos
        dx, dy = DIRS[self.st.facing]
        return x + dx, y + dy

    def interact(self):
        fx, fy = self.front()
        found = self.actor_at(fx, fy)
        if found:
            kind, a = found
            self.npc_facing[a.get("id")] = OPPOSITE[self.st.facing]
            self.busy = True

            def done(*_):
                self.npc_facing.pop(a.get("id"), None)
                self.busy = False

            if kind == "trainer":
                if self.trainer_defeated(a):
                    self.game.say(a["after"], speaker=a["name"], then=done)
                else:
                    self.start_trainer(a)
            elif a.get("task"):
                run_npc_task(self.game, a, done)
            else:
                self.game.say(a["lines"], speaker=a["name"], then=done)
            return
        ch = self.tile(fx, fy)
        if ch == "S":
            if (fx, fy) == world.MEADOW_SIGN:
                self.game.say([world.SIGNS[(fx, fy)]], speaker="Sign",
                              then=lambda: self.game.push(TypeChartScene(self.game)))
            else:
                self.game.say([world.SIGNS[(fx, fy)]], speaker="Sign")
        elif ch == "B":
            from .buildings import task_board
            task_board(self.game)
        elif (fx, fy) in self.building_tiles:
            self.game.say(["The door is round the front."])

    def gym_ready(self):
        return "trainer:sam" in self.st.flags and "trainer:hana" in self.st.flags

    def enter_building(self, b):
        door = tuple(self.st.pos) if tuple(self.st.pos) in b["doors"] else b["doors"][0]

        def leave():
            self.st.pos = [door[0], door[1] + 1]
            self.st.facing = "down"
            self.px, self.py = door[0] * TILE, (door[1] + 1) * TILE
            self.busy = False

        self.busy = True
        if b["id"] == "house":
            self.game.say(["Home sweet home. Everyone's out, and you've got an adventure to get on with!",
                           f"Remember: {CLINIC_NAME} heals your Mintlings for free."], then=leave)
            return
        from .buildings import InteriorScene
        self.game.push(InteriorScene(self.game, b, leave, self))

    # ------------------------------------------------------------------ battles
    def check_trainers(self):
        x, y = self.st.pos
        for t in self.visible_trainers():
            if self.trainer_defeated(t):
                continue
            dx, dy = DIRS[t["facing"]]
            for i in range(1, t["sight"] + 1):
                tx, ty = t["x"] + dx * i, t["y"] + dy * i
                if (tx, ty) == (x, y):
                    self.busy = True
                    self.st.facing = OPPOSITE[t["facing"]]
                    self.alert = [t, 0.8]
                    self.game.audio.play("alert")
                    return True
                if self.tile(tx, ty) in world.BLOCKING or self.actor_at(tx, ty):
                    break
        return False

    def start_trainer(self, t):
        from .battle_scene import BattleScene
        self.busy = True
        if not self.st.has_able_mintling():
            self.game.say([f"Your Mintlings need a rest first. Healing at {CLINIC_NAME} is free!"],
                          then=self.finish_event)
            return
        trainer = {"name": t["name"], "reward": t["reward"], "id": t["id"], "xp": t.get("xp", "trainer"),
                   "topics": t.get("topics"), "level": t.get("level", 1)}

        def go():
            battle = self.game.new_battle(make_team(t["team"]), trainer, rng=self.rng)
            self.game.push(BattleScene(self.game, battle, lambda outcome: self.after_trainer(t, outcome)))

        self.game.say(t["before"], speaker=t["name"], then=go)

    def after_trainer(self, t, outcome):
        if outcome == "win":
            self.st.flags.add(f"trainer:{t['id']}")
            if self.st.demo and t["id"] == "sam":
                self.st.demo_task = "scam"
            self.game.say(t["after"], speaker=t["name"], then=self.finish_event)
        else:
            self.blackout()

    def start_wild(self, tile):
        from .battle_scene import BattleScene
        table = world.ENCOUNTERS[tile]
        sp, lo, hi, _ = self.rng.choices(table, [e[3] for e in table])[0]
        mon = Mintling(sp, self.rng.randint(lo, hi))
        self.busy = True
        battle = self.game.new_battle([mon], rng=self.rng)

        def end(outcome):
            if outcome == "lose":
                self.blackout()
            else:
                self.finish_event()

        self.game.push(BattleScene(self.game, battle, end))

    def blackout(self, penalty=True):
        """All Mintlings fainted: return to Mintwell Clinic, healed. A normal loss costs 10% of your
        money (max £20). It never creates borrowing or increases debt."""
        self.st.heal_party()
        x, y = world.CLINIC_POS
        self.st.pos = [x, y]
        self.st.facing = "down"
        self.px, self.py = x * TILE, y * TILE
        self.area = self._area_name(y)
        self.busy = True
        tx = self.st.account.apply_battle_loss() if penalty else None
        lines = [f"You hurried back to {CLINIC_NAME}. Your Mintlings are fully healed, free of charge."]
        if tx:
            lines.append(f"Losing that battle cost £{-tx.money_change}, 10% of your money (never more than £20). "
                         f"Your money is now £{self.st.account.money}. What you owe hasn't changed.")
        else:
            lines.append("You didn't have any money to lose, and losing never adds to what you owe.")
        self.game.say(lines, speaker=CLINIC_NAME, then=self.finish_event)

    def finish_event(self, *_):
        self.busy = False

    def maybe_reminder(self, area):
        """The payment reminder the player chose to set, shown before the gym (a story deadline, no timer)."""
        from .bank import reminder_text, BankScene
        a = self.st.account
        if area != "Copperleaf Gym" or not a.reminder_on or a.owed == 0:
            return False
        self.busy = True
        self.game.audio.play("alert")

        def answer(open_bank):
            if open_bank:
                self.game.push(BankScene(self.game, start="repay", on_close=self.finish_event))
            else:
                self.finish_event()

        self.game.ask(reminder_text(a), [("Open PocketBank to repay", True), ("Remind me later", False)],
                      answer, speaker="PocketBank")
        return True

    def maybe_scam_event(self):
        """After Saver Sam, the player's phone buzzes: an unrecognised payment and a fake text."""
        from .security import scam_ready, start_scam_event
        if not scam_ready(self.st):
            return False
        self.busy = True
        start_scam_event(self.game, on_done=self.finish_event)
        return True

    def on_resume(self):
        if self.st.demo and self.st.demo_task == "repay" and self.st.account.owed == 0:
            self.st.demo_task = "battle"
            self.game.toast("Repayment done! Next: walk north to battle Saver Sam.", 4)
            self.game.announce(DEMO_TASKS["battle"])

    def start_demo_intro(self):
        self.busy = True
        a = self.st.account
        self.game.say([
            "Judge Demo. This uses the same game systems as a normal adventure, starting from a prepared point.",
            f"{self.st.player_name} bought a Potion, a Super Potion and a Revive for £120 with only £100, "
            "so £20 was borrowed on PocketBank's interest-free tutorial credit.",
            f"Since then they've earned some money. Now: your money £{a.money}, amount you owe £{a.owed}.",
            "Task: press Esc, open PocketBank and choose Guided Mode. Check what you owe, review a repayment "
            "and confirm it, using only the keyboard.",
            "Try Options for larger text, high contrast and read aloud (R reads the screen, T stops).",
        ], speaker="Judge Demo", then=self.finish_event)

    # ------------------------------------------------------------------ drawing
    def camera(self):
        cx = self.px + TILE / 2 - SCREEN_W / 2
        cy = self.py + TILE / 2 - SCREEN_H / 2
        cx = max(0, min(cx, world.W * TILE - SCREEN_W))
        cy = max(0, min(cy, world.H * TILE - SCREEN_H))
        return int(cx), int(cy)

    def draw(self, surf):
        cam_x, cam_y = self.camera()
        surf.blit(self.ground, (0, 0), pygame.Rect(cam_x, cam_y, SCREEN_W, SCREEN_H))
        drawables = []
        for kind, a in self.actors():
            facing = self.npc_facing.get(a.get("id"), a["facing"])
            img = sprites.person(a["look"], facing, 0)
            drawables.append((a["y"] * TILE, a["x"] * TILE, a["y"] * TILE - 10, img, None))
        step = 0
        if self.moving:
            step = 1 + (self.steps % 2) if self.moving[4] < 0.6 else 0
        pimg = sprites.person(sprites.PLAYER_LOOK, self.st.facing, step, hat=PLAYER_HAT)
        drawables.append((self.py + 1, self.px, self.py - 10, pimg, "player"))
        for _, x, y, img, tag in sorted(drawables, key=lambda d: d[0]):
            surf.blit(img, (x - cam_x, y - cam_y))
            if tag == "player" and not self.moving:
                tx, ty = self.st.pos
                if self.tile(tx, ty) in world.WILD_TILES:
                    surf.blit(self.tall_overlay[self.tile(tx, ty)], (tx * TILE - cam_x, ty * TILE + TILE // 2 - cam_y))
        if self.alert:
            t = self.alert[0]
            ax, ay = t["x"] * TILE - cam_x + TILE // 2, t["y"] * TILE - cam_y - 24
            bubble = pygame.Rect(0, 0, 30, 34)
            bubble.center = (ax, ay)
            pygame.draw.rect(surf, (255, 255, 255), bubble, border_radius=8)
            pygame.draw.rect(surf, (30, 30, 40), bubble, 2, border_radius=8)
            draw_text(surf, "!", self.game.fonts.get("heading", scaled=False), (200, 40, 40), bubble.center, "center")
        self.draw_hud(surf)

    def draw_hud(self, surf):
        theme = self.game.theme
        hc = self.game.settings.high_contrast
        small = self.game.fonts.get("small")
        a = self.st.account
        x = SCREEN_W - 10
        chips = [("Menu (Esc)", None), (f"You owe £{a.owed}", "owe"), (f"Your money £{a.money}", "money")]
        y = 10
        self.menu_rect = None
        for text, kind in chips:
            img = small.render(text, True, (255, 255, 255))
            r = img.get_rect(topright=(x, y)).inflate(18, 10)
            r.right = x
            fill = (20, 24, 40) if not hc else (0, 0, 0)
            pygame.draw.rect(surf, fill, r, border_radius=8)
            border = (240, 200, 90) if kind == "money" else (230, 120, 120) if kind == "owe" else (180, 190, 220)
            pygame.draw.rect(surf, (255, 255, 255) if hc else border, r, 2, border_radius=8)
            surf.blit(img, img.get_rect(center=r.center))
            if kind is None:
                self.menu_rect = r
            x = r.left - 8
        if True:  # location label is always shown
            font = self.game.fonts.get("small")
            here = self.tile(*self.st.pos)
            label = self.area + (f" - {world.WILD_TILES[here]}" if here in world.WILD_TILES else "")
            img = font.render(label, True, (255, 255, 255))
            r = img.get_rect(topleft=(10, 10)).inflate(20, 10)
            r.topleft = (10, 10)
            pygame.draw.rect(surf, (20, 24, 40) if not hc else (0, 0, 0), r, border_radius=8)
            pygame.draw.rect(surf, theme["accent"], r, 2, border_radius=8)
            surf.blit(img, img.get_rect(center=r.center))
        if self.st.demo and self.st.demo_task:
            text = DEMO_TASKS[self.st.demo_task]
            img = small.render(text, True, (20, 20, 30))
            r = img.get_rect(midtop=(SCREEN_W // 2, 52)).inflate(24, 12)
            r.top = 52
            pygame.draw.rect(surf, (255, 226, 120) if not hc else (255, 230, 0), r, border_radius=10)
            pygame.draw.rect(surf, (30, 30, 40), r, 2, border_radius=10)
            surf.blit(img, img.get_rect(center=r.center))
        draw_hints(surf, self.game, [("Arrows/WASD", "Walk"), ("Enter", "Talk"), ("Esc", "Menu")])
