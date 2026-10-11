"""CPU agents that speak the local `arc_agi` engine protocol.

An agent is any object with
    reset(game_id: str, available_actions: list[int]) -> None
    act(frame: FrameDataRaw) -> tuple[GameAction, dict | None]
where the dict carries {"x": .., "y": ..} for ACTION6 and is otherwise None.
"""
from .explorer import ExplorerAgent
from .random_agent import RandomAgent

AGENTS = {"random": RandomAgent, "explorer": ExplorerAgent}
