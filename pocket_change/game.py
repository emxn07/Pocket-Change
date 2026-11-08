"""Main loop and scene stack."""
import pygame

from .config import SCREEN_W, SCREEN_H, FPS, TITLE
from .core.game_state import GameState
from .core.quiz import QuizDeck
from .settings import Settings
from .ui.audio import Audio
from .ui.tts import Speaker
from .ui.widgets import Fonts, NORMAL_THEME, CONTRAST_THEME


class Scene:
    overlay = False         # draw the scene below this one first
    text_input = False      # letters are typed, so R/T are not read-aloud shortcuts

    def __init__(self, game):
        self.game = game

    def handle(self, event):
        pass

    def update(self, dt):
        pass

    def draw(self, surf):
        pass

    def speech_text(self):
        return ""

    def on_resume(self):
        pass


class Game:
    def __init__(self):
        pygame.init()
        self.settings = Settings.load()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.SCALED | pygame.RESIZABLE)
        pygame.display.set_caption(TITLE)
        pygame.key.set_repeat(350, 60)
        self.clock = pygame.time.Clock()
        self.fonts = Fonts(self.settings)
        self.audio = Audio(self.settings)
        self.speaker = Speaker()
        self.quiz = QuizDeck()
        self.state = None
        self.scenes = []
        self.toasts = []
        self.running = True
        self.time = 0.0

    # ------------------------------------------------------------------ theme/text
    @property
    def motion(self):
        """False when the player has turned on Reduce motion."""
        return not self.settings.reduce_motion

    @property
    def anim_time(self):
        """The clock for decorative animation (bobbing, spinning, blinking). Frozen with Reduce motion."""
        return self.time if self.motion else 0.0

    @property
    def theme(self):
        return CONTRAST_THEME if self.settings.high_contrast else NORMAL_THEME

    def fmt(self, text):
        if self.state:
            text = text.replace("{player}", self.state.player_name).replace("{rival}", self.state.rival_name)
        return text

    # ------------------------------------------------------------------ scenes
    @property
    def top(self):
        return self.scenes[-1] if self.scenes else None

    def push(self, scene):
        self.scenes.append(scene)
        return scene

    def pop(self, scene=None):
        if scene is not None:
            if scene in self.scenes:
                self.scenes.remove(scene)
        elif self.scenes:
            self.scenes.pop()
        if self.top:
            self.top.on_resume()

    def replace(self, scene):
        if self.scenes:
            self.scenes.pop()
        self.scenes.append(scene)
        return scene

    def reset(self, scene):
        self.speaker.stop()
        self.scenes = [scene]
        return scene

    # ------------------------------------------------------------------ helpers used everywhere
    def say(self, pages, then=None, speaker=None, choices=None, portrait=None):
        from .scenes.common import Dialogue
        return self.push(Dialogue(self, pages, then=then, speaker=speaker, choices=choices, portrait=portrait))

    def ask(self, text, options, then, speaker=None):
        """Yes/No style question. then(value) is called with the chosen value (None if cancelled)."""
        return self.say([text], speaker=speaker, choices=options, then=then)

    def toast(self, text, seconds=2.6):
        self.toasts.append([text, seconds])

    def read(self, text):
        """Read aloud on request (R key or a Read button)."""
        if not text:
            return
        if not self.speaker.available:
            self.toast("Read aloud needs a speech engine. See Options.")
            return
        self.speaker.speak(text, self.settings.speech_rate)

    def announce(self, text):
        """Read automatically, only when the player has turned on auto read-aloud."""
        if self.settings.auto_read and self.speaker.available and text:
            self.speaker.speak(text, self.settings.speech_rate)

    def record_answer(self, correct, topic=None, level=1):
        if self.state:
            self.state.record_answer(correct, topic, level)

    def new_battle(self, enemies, trainer=None, rng=None):
        """Every battle is made here, so the Relaxed battles option applies everywhere."""
        from .core.battle import Battle, RELAXED_DAMAGE
        scale = RELAXED_DAMAGE if self.settings.relaxed_battles else 1.0
        return Battle(self.state, enemies, trainer, rng=rng, opponent_damage=scale)

    # ------------------------------------------------------------------ starting play
    def start_title(self):
        from .scenes.title import TitleScene
        self.state = None
        self.reset(TitleScene(self))

    def start_new_game(self):
        from .scenes.intro import GuideScene
        self.state = GameState.new_game()
        self.reset(GuideScene(self))

    def start_demo(self):
        from .scenes.overworld import Overworld
        self.state = GameState.new_demo()
        world = self.reset(Overworld(self))
        world.start_demo_intro()

    def start_practice(self):
        """PocketBank practice: the account tasks on their own, with a fresh pretend account."""
        from .scenes.practice import PracticeHubScene
        self.state = GameState.new_practice()
        self.reset(PracticeHubScene(self))

    def continue_game(self):
        from .scenes.overworld import Overworld
        try:
            self.state = GameState.load()
        except ValueError as e:
            self.toast(str(e), 6)
            return
        except (OSError, KeyError) as e:
            self.toast(f"Could not load the save file ({e.__class__.__name__}).", 6)
            return
        self.reset(Overworld(self))

    def save(self):
        if self.state.demo:
            return False, "Judge Demo progress is never saved, so the demo starts fresh every time."
        try:
            self.state.save()
        except OSError as e:
            return False, f"Saving failed: {e}"
        return True, "Your adventure has been saved."

    # ------------------------------------------------------------------ loop
    def run(self):
        self.start_title()
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000, 0.05)
            self.time += dt
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    break
                if self._global_key(event):
                    continue
                if self.top:
                    self.top.handle(event)
            if self.top:
                self.top.update(dt)
            self.draw()
        self.speaker.stop()
        pygame.quit()

    def _global_key(self, event):
        if event.type != pygame.KEYDOWN:
            return False
        typing = self.top is not None and self.top.text_input
        if event.key == pygame.K_F5 or (event.key == pygame.K_r and not typing):
            self.read(self.top.speech_text() if self.top else "")
            return True
        if event.key == pygame.K_F6 or (event.key == pygame.K_t and not typing):
            self.speaker.stop()
            return True
        if event.key == pygame.K_F11:
            pygame.display.toggle_fullscreen()
            return True
        return False

    def draw(self):
        surf = self.screen
        start = len(self.scenes) - 1
        while start > 0 and self.scenes[start].overlay:
            start -= 1
        for scene in self.scenes[max(0, start):]:
            scene.draw(surf)
        self._draw_toasts(surf)
        pygame.display.flip()

    def _draw_toasts(self, surf):
        if not self.toasts:
            return
        dt = self.clock.get_time() / 1000
        font = self.fonts.get("small")
        y = SCREEN_H - 44
        for t in reversed(self.toasts):
            t[1] -= dt
            img = font.render(t[0], True, (255, 255, 255))
            r = img.get_rect(midbottom=(SCREEN_W // 2, y)).inflate(24, 14)
            r.bottom = y
            pygame.draw.rect(surf, (20, 22, 36), r, border_radius=10)
            pygame.draw.rect(surf, self.theme["accent"], r, 2, border_radius=10)
            surf.blit(img, img.get_rect(center=r.center))
            y = r.top - 6
        self.toasts = [t for t in self.toasts if t[1] > 0]

