"""Tiny procedurally generated sound effects (no audio files needed)."""
import array
import math

import pygame

NOTES = {
    "move": [(880, 22)],
    "select": [(660, 40), (990, 60)],
    "back": [(520, 40), (390, 60)],
    "bump": [(140, 50)],
    "hit": [(220, 40), (150, 70)],
    "coin": [(988, 60), (1319, 140)],
    "correct": [(523, 80), (659, 80), (784, 140)],
    "wrong": [(311, 120), (233, 180)],
    "heal": [(523, 60), (659, 60), (784, 60), (1047, 120)],
    "level": [(659, 80), (784, 80), (988, 80), (1319, 200)],
    "shake": [(330, 60)],
    "catch": [(784, 90), (988, 90), (1175, 90), (1568, 260)],
    "alert": [(1175, 70), (1568, 120)],
    "encounter": [(392, 60), (523, 60), (392, 60), (523, 60), (659, 120)],
}


class Audio:
    def __init__(self, settings):
        self.settings = settings
        self.sounds = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(22050, -16, 1, 512)
            freq, _, channels = pygame.mixer.get_init()
            for name, notes in NOTES.items():
                self.sounds[name] = self._make(notes, freq, channels)
        except (pygame.error, TypeError):
            self.sounds = {}

    @staticmethod
    def _make(notes, rate, channels):
        samples = array.array("h")
        for freq, ms in notes:
            n = int(rate * ms / 1000)
            for i in range(n):
                env = min(1.0, i / 200) * min(1.0, (n - i) / 400)
                v = 1 if math.sin(2 * math.pi * freq * i / rate) >= 0 else -1
                s = int(v * 3200 * env)
                for _ in range(channels):
                    samples.append(s)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    def play(self, name):
        if self.settings.sound and name in self.sounds:
            self.sounds[name].play()
