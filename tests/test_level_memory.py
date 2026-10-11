import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness" / "ARC3-Inference"))

from inference.utils.level_memory import compute_solved_levels, format_solved_levels  # noqa: E402


@dataclass
class F:
    level: int


@dataclass
class E:
    action: str
    frame: F
    result: dict = field(default_factory=dict)


def _history():
    # seeded frame on level 1; die once (RESET), then solve level 1 in 3 actions, then 2 on level 2
    return [
        E("", F(1)),
        E("UP", F(1)),
        E("UP", F(1), {"game_over": True}),
        E("RESET", F(1), {"automatic": True}),
        E("LEFT", F(1)),
        E("UP", F(1)),
        E("UP", F(2), {"level_completed": True}),
        E("MOUSE(row=3, col=4)", F(2)),
        E("SPACE", F(3), {"level_completed": True}),
        E("DOWN", F(3)),  # level 3 in progress, not completed
    ]


def test_solved_levels_tracks_attempts_and_winning_sequence():
    out = compute_solved_levels(_history())
    assert [o["level"] for o in out] == [1, 2]
    l1, l2 = out
    assert l1["winning_actions"] == ["LEFT", "UP", "UP"]
    assert l1["n_actions"] == 3
    assert l1["attempts"] == 2
    assert l1["total_actions"] == 6  # 2 failed + RESET + 3 winning
    assert l2["winning_actions"] == ["MOUSE(row=3, col=4)", "SPACE"]
    assert l2["attempts"] == 1


def test_truncation_keeps_the_tail():
    hist = [E("", F(1))] + [E("UP", F(1)) for _ in range(100)] + [E("SPACE", F(2), {"level_completed": True})]
    out = compute_solved_levels(hist, max_actions_kept=10)
    assert out[0]["n_actions"] == 101
    assert len(out[0]["winning_actions"]) == 10
    assert out[0]["winning_actions"][-1] == "SPACE"
    assert out[0]["truncated"] is True


def test_format_is_one_line_per_level():
    text = format_solved_levels(compute_solved_levels(_history()))
    assert text.splitlines()[0].startswith("L1: 3 actions in 2 attempt(s) (6 spent): LEFT, UP, UP")
    assert len(text.splitlines()) == 2


def test_empty_history():
    assert compute_solved_levels([]) == []
    assert compute_solved_levels([E("", F(1))]) == []
