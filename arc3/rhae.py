"""ARC-AGI-3 score (relative human action efficiency).

Per level: (human_baseline / agent_actions)^2 capped at `cap` (competition 1.0; the local
arc_agi scorecard and TAAF use 1.15).  Levels are weighted by their 1-based index.  A game's
score is the weighted mean over all of its levels (unsolved levels count 0 but keep their
weight), so the game is also capped by the share of weight that was actually solved.  The
benchmark score is the plain mean over games, in percent.
"""
from __future__ import annotations

from dataclasses import dataclass, field

COMPETITION_CAP = 1.0
LOCAL_CAP = 1.15


def level_score(baseline: int, actions: int, cap: float = COMPETITION_CAP) -> float:
    """Score in [0, cap] for one *completed* level. 0 if no actions were spent."""
    if actions <= 0 or baseline <= 0:
        return 0.0
    return min(cap, (baseline / actions) ** 2)


def game_score(
    levels_completed: int,
    actions_per_level: list[int],
    baselines: list[int],
    cap: float = COMPETITION_CAP,
) -> float:
    """Fraction in [0, cap] for one game (level-weighted mean)."""
    n = len(baselines)
    if n == 0:
        return 0.0
    total = 0.0
    weights = 0
    for idx in range(n):
        weight = idx + 1
        weights += weight
        if idx < levels_completed:
            actions = actions_per_level[idx] if idx < len(actions_per_level) else 0
            total += weight * level_score(baselines[idx], actions, cap)
    return total / weights


@dataclass
class GameResult:
    game_id: str
    levels_completed: int
    actions_per_level: list[int]
    baselines: list[int]
    total_actions: int = 0
    resets: int = 0
    state: str = ""
    seconds: float = 0.0
    note: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def n_levels(self) -> int:
        return len(self.baselines)

    def score(self, cap: float = COMPETITION_CAP) -> float:
        return game_score(self.levels_completed, self.actions_per_level, self.baselines, cap)


def benchmark_score(results: list[GameResult], cap: float = COMPETITION_CAP) -> float:
    """Mean over games, in percent (the leaderboard number)."""
    if not results:
        return 0.0
    return 100.0 * sum(r.score(cap) for r in results) / len(results)
