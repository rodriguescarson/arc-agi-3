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


def test_a_lost_attempt_with_no_reset_entry_starts_a_new_attempt():
    # ARC3_ATTEMPT_LOSS_*: a life lost mid-level restarts the board without a RESET in the history
    hist = [
        E("", F(1)),
        E("UP", F(1)),
        E("UP", F(1), {"attempt_lost": True}),
        E("LEFT", F(1)),
        E("UP", F(2), {"level_completed": True}),
    ]
    (l1,) = compute_solved_levels(hist)
    assert l1["winning_actions"] == ["LEFT", "UP"]
    assert l1["attempts"] == 2 and l1["total_actions"] == 4


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


# ---- the sandbox splice -------------------------------------------------------------------
# python_tool_sandbox.py inlines this module's source into the child program it runs with
# `python -I -S -c`. On 2026-10-17 a `from __future__` import at the top of this file landed
# at line 893 of that program, every tool call died with a SyntaxError, and the first two GPU
# commits played zero actions. These tests run the real child.

def test_sandbox_bootstrap_compiles():
    from inference.agent.python_tool_sandbox import _SANDBOX_BOOTSTRAP

    compile(_SANDBOX_BOOTSTRAP, "<sandbox>", "exec")


def test_sandbox_roundtrip_exposes_solved_levels():
    from inference.agent.python_tool_sandbox import run_sandboxed_python

    def frame(level, step):
        return {"ascii": "BB\nBB", "step": step, "level": level, "shape": [2, 2], "grid": [[0, 0], [0, 0]]}

    state = {
        "current_frame": frame(2, 3),
        "history": [
            {"action": "", "frame": frame(1, 0)},
            {"action": "UP", "frame": frame(1, 1)},
            {"action": "RIGHT", "frame": frame(2, 2), "result": {"level_completed": True}},
            {"action": "DOWN", "frame": frame(2, 3)},
        ],
        "valid_actions": ["UP", "DOWN", "LEFT", "RIGHT"],
        "death_ledger": {"attempts": []},
        "last_action_call_result": None,
    }
    result = run_sandboxed_python(
        code="print(current_frame.level, valid_actions)\nprint(solved_levels())",
        timeout_seconds=20,
        initial_state=state,
        action_handler=lambda *a, **k: {"ok": True},
    )
    assert not result.get("error"), result
    out = result.get("stdout", "")
    assert out.startswith("2 ['UP', 'DOWN', 'LEFT', 'RIGHT']"), out
    assert "'level': 1" in out and "'winning_actions': ['UP', 'RIGHT']" in out, out
