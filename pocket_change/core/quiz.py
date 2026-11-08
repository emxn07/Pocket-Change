"""Draws questions without immediate repeats and shuffles answer order."""
import random

from ..data.questions import QUESTIONS, GLOSSARY
from . import question_gen

GENERATED_SHARE = 0.5     # medium and hard fights: about half the questions use fresh numbers


class Question:
    def __init__(self, raw, topic, rng):
        self.text = raw["text"]
        self.explain = raw["explain"]
        self.terms = [t for t in raw["terms"] if t in GLOSSARY]
        self.topic = topic
        self.level = raw.get("level", 1)
        correct = raw["choices"][0]
        self.choices = list(raw["choices"])
        rng.shuffle(self.choices)
        self.correct_index = self.choices.index(correct)

    @property
    def correct_text(self):
        return self.choices[self.correct_index]

    def is_correct(self, index):
        return index == self.correct_index


class QuizDeck:
    def __init__(self, rng=None):
        self.rng = rng or random.Random()
        self._decks = {}
        self._last_template = {}

    def draw(self, topic=None, level=None):
        """A question on `topic` (random topic if None) at difficulty `level` (any if None).
        Questions don't repeat until that topic and level's pile has been used up."""
        if topic not in QUESTIONS:
            topic = self.rng.choice(list(QUESTIONS))
        if level in (2, 3) and question_gen.has_templates(topic, level) and self.rng.random() < GENERATED_SHARE:
            name, raw = question_gen.generate(topic, level, self.rng, avoid=self._last_template.get((topic, level)))
            self._last_template[(topic, level)] = name
            return Question(raw, topic, self.rng)
        pool = [q for q in QUESTIONS[topic] if level is None or q.get("level", 1) == level]
        if not pool:
            pool, level = list(QUESTIONS[topic]), None
        key = (topic, level)
        deck = self._decks.get(key)
        if not deck:
            deck = list(pool)
            self.rng.shuffle(deck)
            self._decks[key] = deck
        return Question(deck.pop(), topic, self.rng)
