from __future__ import annotations

import random
from typing import Optional

TAUNTS_NEUTRAL = [
    "Your move looks... interesting.",
    "I've seen better, but let's see where this goes.",
    "Is that the best you've got?",
    "Maybe try a different opening next time.",
]

TAUNTS_AI_GOOD = [
    "Checkmate is inevitable.",
    "I'm just warming up.",
    "Stockfish approves of itself.",
]

TAUNTS_PLAYER_GOOD = [
    "Wait, that's actually a good move!",
    "Did you let someone else play for you?",
    "I might need to think harder...",
]


class TauntManager:
    def __init__(self) -> None:
        self._last_taunt = random.choice(TAUNTS_NEUTRAL)

    def choose(self, evaluation: Optional[float] = None) -> str:
        # evaluation > 1 roughly means white advantage, < -1 black advantage
        collection = TAUNTS_NEUTRAL
        if evaluation is not None:
            if evaluation > 1:
                collection = TAUNTS_PLAYER_GOOD
            elif evaluation < -1:
                collection = TAUNTS_AI_GOOD
        self._last_taunt = random.choice(collection)
        return self._last_taunt

    @property
    def last(self) -> str:
        return self._last_taunt
