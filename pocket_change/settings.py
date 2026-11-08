"""Accessibility and audio settings, kept between sessions (separate from save files)."""
import json
import os

from . import config

TEXT_SIZES = ["Normal", "Large", "Extra large"]
TEXT_SCALES = [1.0, 1.22, 1.45]

DEFAULTS = {
    "text_size": 0,
    "high_contrast": False,
    "auto_read": False,
    "sound": True,
    "relaxed_battles": False,
    "reduce_motion": False,
    "speech_rate": 1,           # 0 slow, 1 normal, 2 fast
}

SPEECH_RATES = ["Slow", "Normal", "Fast"]


class Settings:
    def __init__(self, data=None, path=None):
        self.path = path or config.SETTINGS_PATH
        self.data = dict(DEFAULTS)
        if data:
            self.data.update({k: v for k, v in data.items() if k in DEFAULTS})

    def __getattr__(self, key):
        data = self.__dict__.get("data", {})
        if key in data:
            return data[key]
        raise AttributeError(key)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    @property
    def text_scale(self):
        return TEXT_SCALES[self.data["text_size"]]

    @classmethod
    def load(cls, path=None):
        path = path or config.SETTINGS_PATH
        try:
            with open(path, encoding="utf-8") as f:
                return cls(json.load(f), path)
        except (OSError, ValueError):
            return cls(path=path)

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except OSError:
            pass
