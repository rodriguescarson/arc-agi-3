"""A three-level toy game on the real arcengine, so the RESET tests need no downloaded games.

ACTION1 advances and the third one on a level completes it; ACTION2 does nothing; the eighth action
on a level ends the attempt (a step bar running out). RESET semantics are arcengine's own, untouched.

This file is also copied into a throwaway environment_files tree as ``lad1.py`` (arc_agi derives
the class name ``Lad1`` from the game id), so it imports only arcengine.
"""
from arcengine import ARCBaseGame, GameAction, Level, Sprite


def _level():
    return Level(sprites=[Sprite(pixels=[[8]], name="p", x=0, y=0)], grid_size=(8, 8), name="L")


class Lad1(ARCBaseGame):
    def __init__(self, seed: int = 0) -> None:
        super().__init__("lad1", [_level(), _level(), _level()], available_actions=[1, 2], seed=seed)

    def on_set_level(self, level) -> None:
        self.progress = 0

    def step(self) -> None:
        if self.action.id == GameAction.ACTION1:
            self.progress += 1
        if self.progress == 3:
            self.next_level()
        elif self._action_count >= 8:
            self.lose()
        self.complete_action()
