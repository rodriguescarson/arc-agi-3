from __future__ import annotations

import random

from arcengine import GameAction, GameState


class RandomAgent:
    """Uniform over the game's available actions; RESET after a game over."""

    def __init__(self, seed: int = 0) -> None:
        self.rng = random.Random(seed)
        self.actions: list[GameAction] = []

    def reset(self, game_id: str, available_actions: list[int]) -> None:
        self.actions = [GameAction.from_id(a) for a in available_actions if a != GameAction.RESET.value]

    def act(self, frame):
        if frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            return GameAction.RESET, None
        actions = [GameAction.from_id(a) for a in frame.available_actions if a != GameAction.RESET.value] or self.actions
        action = self.rng.choice(actions)
        if action is GameAction.ACTION6:
            return action, {"x": self.rng.randint(0, 63), "y": self.rng.randint(0, 63)}
        return action, None
