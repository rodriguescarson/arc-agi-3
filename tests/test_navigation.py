import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness" / "ARC3-Inference"))

from inference.utils.navigation import (  # noqa: E402
    describe_movement,
    learn_controls,
    nav_key,
    nav_moves,
    plan_path,
    run_navigation,
)

FLOOR, WALL, PIECE, GOAL, LAVA = 0, 1, 3, 4, 2
DELTA = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}


class Board:
    """A 12x12 room: a 2x2 piece that moves one cell per key, a wall with one gap, a goal."""

    def __init__(self, step=1):
        self.step = step
        self.base = [[WALL if r in (0, 11) or c in (0, 11) else FLOOR for c in range(12)] for r in range(12)]
        for r in range(1, 11):
            if r not in (7, 8):
                self.base[r][6] = WALL  # wall down column 6, two-row gap at rows 7-8
        self.base[2][9] = GOAL
        self.pos = (2, 2)
        self.level = 1

    def grid(self):
        g = [row[:] for row in self.base]
        for r in range(2):
            for c in range(2):
                g[self.pos[0] + r][self.pos[1] + c] = PIECE
        return g

    def press(self, key):
        dr, dc = DELTA[key]
        nxt = (self.pos[0] + dr * self.step, self.pos[1] + dc * self.step)
        cells = [(nxt[0] + r, nxt[1] + c) for r in range(2) for c in range(2)]
        if all(self.base[r][c] in (FLOOR, GOAL) for r, c in cells):
            self.pos = nxt
        return {"level_completed": any(self.base[r][c] == GOAL for r, c in cells)}


@dataclass
class Frame:
    grid: list
    level: int = 1


@dataclass
class T:
    action: str
    before_frame: Frame
    after_frame: Frame
    result: dict = field(default_factory=dict)


def _play(board, keys):
    ts = []
    for key in keys:
        before = Frame(board.grid(), board.level)
        res = board.press(key)
        ts.append(T(key, before, Frame(board.grid(), board.level), res))
    return ts


def test_nav_key_accepts_engine_and_model_names():
    assert nav_key("ACTION1") == "UP" and nav_key("right") == "RIGHT"
    assert nav_key("MOUSE(row=3, col=4)") is None and nav_key("SPACE") is None and nav_key("") is None


def test_rigid_move_is_detected():
    b = Board()
    before = b.grid()
    b.press("DOWN")
    moves = nav_moves(before, b.grid())
    assert [(m[0], m[2], m[3], m[4]) for m in moves] == [(PIECE, (1, 0), (2, 2), (3, 2))]


def test_learns_controls_and_infers_the_opposite_key():
    b = Board()
    ts = _play(b, ["DOWN", "RIGHT"])
    model = learn_controls(ts, level=1)
    assert model["colour"] == PIECE and len(model["shape"]) == 4
    assert model["controls"] == {"DOWN": (1, 0), "RIGHT": (0, 1), "UP": (-1, 0), "LEFT": (0, -1)}
    assert sorted(model["inferred"]) == ["LEFT", "UP"]
    assert FLOOR in model["passable"] and WALL not in model["passable"]


def test_plan_goes_through_the_gap_not_the_wall():
    b = Board()
    ts = _play(b, ["DOWN", "RIGHT"])
    model = learn_controls(ts, level=1)
    path = plan_path(b.grid(), model, (3, 3), GOAL)
    assert path is not None
    # must get down to the gap rows (7-8) before crossing column 6
    pos = (3, 3)
    for key in path:
        pos = (pos[0] + DELTA[key][0], pos[1] + DELTA[key][1])
        assert b.base[pos[0]][pos[1]] != WALL
    assert any(b.base[pos[0] + r][pos[1] + c] == GOAL for r in range(2) for c in range(2))


def test_run_navigation_reaches_the_goal_with_verified_steps():
    b = Board()
    ts = _play(b, ["DOWN", "RIGHT"])

    def get_state():
        return Frame(b.grid(), b.level), ts

    def act(key):
        before = Frame(b.grid(), b.level)
        res = b.press(key)
        ts.append(T(key, before, Frame(b.grid(), b.level), res))
        return res

    out = run_navigation(GOAL, get_state, act)
    assert out["status"] == "level_completed", out
    assert out["steps"] == out["path"] and out["planned"] == len(out["steps"])


def test_divergence_stops_and_reports():
    b = Board(step=2)  # the board moves two cells, but the model only saw one-cell moves
    ts = _play(Board(), ["DOWN", "RIGHT"])

    def get_state():
        return Frame(b.grid(), b.level), ts

    out = run_navigation((9, 9), get_state, lambda key: b.press(key))
    assert out["status"] == "diverged" and len(out["steps"]) == 1, out


def test_blocked_move_is_learned_and_avoided():
    b = Board()
    ts = _play(b, ["DOWN", "RIGHT", "RIGHT", "RIGHT"])  # third RIGHT hits the wall at column 6
    model = learn_controls(ts, level=1)
    assert ((3, 4), "RIGHT") in model["blocked"]


def test_refusal_is_reported_not_raised():
    class KnownNoOpActionError(BaseException):
        pass

    b = Board()
    ts = _play(b, ["DOWN", "RIGHT"])

    def act(key):
        raise KnownNoOpActionError("already proven inert")

    out = run_navigation(GOAL, lambda: (Frame(b.grid()), ts), act)
    assert out["status"] == "refused" and "KnownNoOpActionError" in out["note"]


def test_nothing_learned_without_moves():
    b = Board()
    out = run_navigation(GOAL, lambda: (Frame(b.grid()), []), lambda key: {})
    assert out["status"] == "no_moves_observed"
    assert describe_movement(Frame(b.grid()), [])["status"] == "no_moves_observed"


def test_plan_only_spends_no_action():
    b = Board()
    ts = _play(b, ["DOWN", "RIGHT"])
    calls = []
    out = run_navigation(GOAL, lambda: (Frame(b.grid()), ts), calls.append, execute=False)
    assert out["status"] == "planned" and out["planned"] > 0 and calls == []


# ---- the sandbox splice: run the real child program ---------------------------------------

def test_sandbox_exposes_navigate_to():
    from inference.agent.python_tool_sandbox import _SANDBOX_BOOTSTRAP, run_sandboxed_python

    compile(_SANDBOX_BOOTSTRAP, "<sandbox>", "exec")
    b = Board()
    g0 = b.grid()
    b.press("DOWN")
    g1 = b.grid()
    b.press("RIGHT")
    g2 = b.grid()

    def frame(grid, step):
        return {"ascii": "", "step": step, "level": 1, "shape": [12, 12], "grid": grid}

    state = {
        "current_frame": frame(g2, 2),
        "history": [
            {"action": "", "frame": frame(g0, 0)},
            {"action": "DOWN", "frame": frame(g1, 1)},
            {"action": "RIGHT", "frame": frame(g2, 2)},
        ],
        "valid_actions": ["UP", "DOWN", "LEFT", "RIGHT"],
        "death_ledger": {"attempts": []},
        "last_action_call_result": None,
    }
    result = run_sandboxed_python(
        code="m = movement_model(); print(m['status'], m['at'], m['controls']['RIGHT'])\n"
             "p = navigate_to(4, execute=False); print(p['status'], p['planned'] > 0)",
        timeout_seconds=20,
        initial_state=state,
        action_handler=lambda *a, **k: {"ok": True},
    )
    assert not result.get("error"), result
    out = result.get("stdout", "")
    assert "ok (3, 3) [0, 1]" in out and "planned True" in out, out
