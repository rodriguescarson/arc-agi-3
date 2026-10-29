"""Attempt restarts the engine does not report (ARC3_ATTEMPT_LOSS_STOP / ARC3_ATTEMPT_LOSS_NOTICE).

ls20 has three lives. When the step bar runs out the level restarts with the state still
NOT_FINISHED, so a batch kept playing on the new board and the next opener said "You are still on
the same level." The detector was run against the offline engine: it found all 25 life losses in six
ls20 smoke runs, all 198 in 250,140 actions of real LLM play on the 25 public games (and flagged
nothing in the other 24 games), and 831 more under random play. Those runs need the engine's game
files, so this file checks the same properties on a small stand-in game with ls20's mechanics."""
import copy
import sys
import threading
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "harness" / "ARC3-Inference"))

from inference.utils.attempt_loss import AttemptTracker, board_area_equal, border_distance  # noqa: E402

SIZE, STEPS = 64, 40
DIRS = {"UP": (-1, 0), "DOWN": (1, 0), "LEFT": (0, -1), "RIGHT": (0, 1)}


class LivesGame:
    """ls20 in miniature: a piece moves one cell per key, a bar in the bottom border shrinks by
    one unit per action (a blocked move included), a ring refills it, and three pips count lives.
    An empty bar puts the piece back on its start cell, refills the bar and takes a pip, with the
    game still running; the last pip ends it. Reaching the goal loads the next level."""

    RING = (30, 34)
    CHANGER = (30, 26)
    GOAL = {0: (30, 20), 1: (50, 50)}
    WALL_COL = 40

    def __init__(self):
        self.start_cells = {0: (30, 30), 1: (10, 10)}
        self.level = 0
        self.lives = 3
        self.over = False
        self.restarts = 0
        self.just_won = False
        self.glyph = 0
        self._begin()

    def _begin(self):
        self.pos = self.start_cells[self.level]
        self.steps = STEPS
        self.ring = True

    def reset(self):
        self.lives, self.over, self.glyph = 3, False, 0
        self._begin()

    def press(self, key):
        self.just_won = False
        dr, dc = DIRS[key]
        r, c = self.pos[0] + dr, self.pos[1] + dc
        if 0 < r < SIZE - 1 and 0 < c < SIZE - 1 and c != self.WALL_COL:
            self.pos = (r, c)
        self.steps -= 1
        if self.ring and self.pos == self.RING:
            self.ring, self.steps = False, STEPS
        if self.pos == self.CHANGER:
            self.glyph = (self.glyph + 1) % 3
        if self.pos == self.GOAL[self.level] and self.level + 1 in self.start_cells:
            self.level, self.lives, self.glyph, self.just_won = self.level + 1, 3, 0, True
            self._begin()
            return
        if self.steps < 0:
            self.lives -= 1
            if self.lives == 0:
                self.over = True
            else:
                self.restarts += 1
                self.glyph = 0
                self._begin()

    def grid(self):
        g = [[0] * SIZE for _ in range(SIZE)]
        for r in range(8, 56):
            g[r][self.WALL_COL] = 1
        for cell, color in ((self.CHANGER, 7), (self.GOAL[self.level], 2)):
            g[cell[0]][cell[1]] = color
        if self.ring:
            g[self.RING[0]][self.RING[1]] = 6
        g[self.pos[0]][self.pos[1]] = 3
        for i in range(STEPS):
            for r in (61, 62):
                g[r][13 + i] = 5 if i >= STEPS - max(0, self.steps) else 8
        for k in range(3):
            for r in (61, 62):
                for c in (56 + 3 * k, 57 + 3 * k):
                    g[r][c] = 4 if self.lives > k else 8
        # the glyph the piece holds, drawn bottom-left like ls20's: states 1 and 2 are four cells each
        for k in range(4 if self.glyph else 0):
            g[60][2 + k + (4 if self.glyph == 2 else 0)] = 9
        return tuple(tuple(row) for row in g)


def drive(game, keys, tracker=None, undo_from=None):
    """Press keys the way the solver does: begin() on the board at the start, observe() per action,
    begin() again after a level up. Returns the 1-based indexes the tracker flagged."""
    tracker = tracker or AttemptTracker()
    prev = game.grid()
    if tracker.start is None:
        tracker.begin(prev)
    flagged = []
    for i, key in enumerate(keys, 1):
        game.press(key)
        new = game.grid()
        if game.just_won or game.over:
            tracker.begin(new)
        elif tracker.observe(prev, new):
            flagged.append(i)
        prev = new
        if game.over:
            break
    return flagged


def burn(n):
    return ["UP", "DOWN"] * (n // 2) + ["UP"] * (n % 2)


# ---- the detector -------------------------------------------------------------------------

def test_flags_the_action_that_empties_the_bar_and_only_that():
    game = LivesGame()
    flagged = drive(game, burn(60))  # loss on action 41: bar of 40 units, one per action
    assert flagged == [STEPS + 1]
    assert game.restarts == 1 and game.lives == 2


def test_every_life_lost_is_flagged_though_the_pips_change_the_board_each_time():
    game = LivesGame()
    keys = burn(STEPS + 1) * 2  # two full attempts, the last of which ends in a second restart
    assert drive(game, keys) == [STEPS + 1, 2 * (STEPS + 1)]
    assert game.lives == 1


def test_going_back_and_forth_restores_the_board_but_is_not_a_restart():
    game = LivesGame()
    # the piece is back on its start cell after every second key, and the board area is identical
    assert drive(game, burn(STEPS)) == []
    assert game.restarts == 0


def test_a_ring_that_refills_the_bar_is_not_a_restart_and_the_next_loss_still_is():
    game = LivesGame()
    keys = ["RIGHT"] * 4 + burn(STEPS + 1)  # picks the ring on the fourth key
    assert drive(game, keys) == [4 + STEPS + 1]
    assert game.restarts == 1


def test_a_blocked_move_still_spends_the_bar_and_the_loss_is_still_flagged():
    game = LivesGame()
    game.start_cells[0] = (30, 39)
    game._begin()
    # the wall at column 40 never lets the piece move: the board area is the start board on every action
    assert drive(game, ["RIGHT"] * (STEPS + 1)) == [STEPS + 1]


def test_a_changer_glyph_returning_mid_run_does_not_hide_the_loss():
    # stepping on the changer three times cycles the HUD glyph 0 -> 1 -> 2 -> 0. The third visit (action
    # 36) takes four HUD cells back toward the start while the bar spends two: a net dip of two, five
    # actions before the loss
    keys = burn(28) + ["LEFT"] * 4 + ["RIGHT", "LEFT"] * 2 + ["DOWN", "UP", "DOWN", "UP", "DOWN"]
    assert len(keys) == STEPS + 1
    assert drive(LivesGame(), keys, AttemptTracker(slack=4)) == [STEPS + 1]
    # with no tolerance the dip restarts the count, so the loss goes unseen: this is why slack exists
    assert drive(LivesGame(), keys, AttemptTracker(slack=0)) == []


def test_level_up_moves_the_reference_board_so_a_later_loss_is_judged_against_the_new_level():
    game = LivesGame()
    tracker = AttemptTracker()
    to_goal = ["LEFT"] * 10  # (30,30) -> (30,20)
    assert drive(game, to_goal, tracker) == [] and game.level == 1
    assert drive(game, burn(STEPS + 1), tracker) == [STEPS + 1]


def test_undo_to_the_start_would_look_like_a_restart_and_the_caller_exempts_it():
    game = LivesGame()
    start = game.grid()
    tracker = AttemptTracker()
    tracker.begin(start)
    prev = start
    for key in burn(20):
        game.press(key)
        new = game.grid()
        assert tracker.observe(prev, new) is False
        prev = new
    with_undo, without = copy.deepcopy(tracker), copy.deepcopy(tracker)
    assert without.observe(prev, start) is True  # an undo that restores board AND bar looks exactly like a restart
    assert with_undo.observe(prev, start, undo=True) is False


def test_a_hud_that_wanders_never_builds_the_run():
    # a border that shows state (a selection, a cursor), not a budget: it climbs and falls, so the board
    # reverting to its start with the HUD snapping back to 0 is a puzzle move, not a lost attempt
    def grid(hud, piece):
        g = [[0] * SIZE for _ in range(SIZE)]
        for c in range(hud):
            g[62][c] = 5
        g[30][30 if piece else 31] = 3
        return tuple(tuple(row) for row in g)

    # (hud cells away from the start, piece on its start cell). Each cycle ends with the HUD at 48 and
    # the board back at its start for one move, then everything returns: what a restart looks like,
    # except that the HUD has only been climbing for four actions
    cycle = [(12, False), (24, True), (36, False), (48, True), (0, True)]
    moves = cycle * 4

    def run(tracker):
        tracker.begin(grid(0, True))
        prev, flagged = grid(0, True), []
        for hud, piece in moves:
            new = grid(hud, piece)
            if tracker.observe(prev, new):
                flagged.append(hud)
                tracker.begin(new)
            prev = new
        return flagged

    assert run(AttemptTracker()) == []
    # without the run requirement every one of those collapses would have been read as a lost attempt
    assert run(AttemptTracker(min_run=0)) == [0] * 4


def test_a_game_with_no_hud_gives_no_second_signal_and_is_never_flagged():
    def grid(piece):
        g = [[0] * SIZE for _ in range(SIZE)]
        g[30][30 if piece else 31] = 3
        return tuple(tuple(row) for row in g)

    tracker = AttemptTracker()
    tracker.begin(grid(True))
    prev = grid(True)
    for i in range(60):
        new = grid(i % 2 == 1)
        assert tracker.observe(prev, new) is False
        prev = new


def test_fails_closed_on_what_it_cannot_judge():
    def primed(**kwargs):
        """A tracker that has watched a full attempt burn down, and the two boards around the loss."""
        game = LivesGame()
        tracker = AttemptTracker(**kwargs)
        start = game.grid()
        tracker.begin(start)
        prev = start
        for key in burn(STEPS):
            game.press(key)
            tracker.observe(prev, game.grid())
            prev = game.grid()
        game.press("UP")
        return tracker, prev, game.grid()

    tracker, spent, restart = primed()
    assert tracker.observe(spent, restart) is True  # control: this pair is a restart
    tracker, spent, restart = primed(border=0)
    assert tracker.observe(spent, restart) is False  # no HUD frame, no second signal
    tracker, spent, restart = primed()
    assert tracker.observe(spent, tuple(row[:60] for row in restart)) is False  # a shape change
    tracker, spent, restart = primed()
    assert tracker.observe(spent, ()) is False
    tracker, spent, restart = primed(border=40)
    assert tracker.observe(spent, restart) is False  # a border that swallows the board
    assert board_area_equal(restart, restart, 4) and border_distance(restart, restart, 4) == 0


def test_begin_forgets_the_attempt():
    game = LivesGame()
    tracker = AttemptTracker()
    drive(game, burn(30), tracker)
    assert tracker.run >= 16 and tracker.hud > 0
    tracker.begin(game.grid())
    assert tracker.run == 0 and tracker.hud == 0 and tracker.start == game.grid()


# ---- the host: batch stop, trace, history -------------------------------------------------

@pytest.fixture(scope="module")
def solver_mod():
    """inference.framework.solver needs only the Solver base class of the TAAF package at import;
    TAAF's own imports (imageio, scipy, ...) are not installed in the test environment."""
    names = ("taaf", "taaf.game", "taaf.solver", "inference.framework.solver")
    saved = {name: sys.modules.get(name) for name in names}
    try:
        import taaf.game  # noqa: F401
        import taaf.solver  # noqa: F401
    except Exception:
        for name in [n for n in sys.modules if n == "taaf" or n.startswith("taaf.")]:
            del sys.modules[name]
        taaf, game, solver = (types.ModuleType(n) for n in ("taaf", "taaf.game", "taaf.solver"))
        solver.Solver = type("Solver", (), {})
        game.Game = game.GameState = type("Game", (), {})
        taaf.game, taaf.solver = game, solver
        sys.modules.update({"taaf": taaf, "taaf.game": game, "taaf.solver": solver})
    sys.modules.pop("inference.framework.solver", None)
    import inference.framework.solver as module

    yield module
    for name, value in saved.items():
        if value is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = value


class FakeEngineGame:
    """Just what _HarnessGameSession reads from a TAAF game, driven by LivesGame."""

    number_of_levels = 2

    def __init__(self, lives_game):
        import arcengine

        self._arcengine = arcengine
        self.lg = lives_game
        self.game_run = types.SimpleNamespace(state="playing", history=[])
        self.current_state = self._state()

    def _state(self):
        arcengine = self._arcengine
        raw = types.SimpleNamespace(
            state=arcengine.GameState.GAME_OVER if self.lg.over else arcengine.GameState.NOT_FINISHED
        )
        return types.SimpleNamespace(
            frame=types.SimpleNamespace(data=[list(row) for row in self.lg.grid()]),
            levels_completed=self.lg.level,
            just_won_level=self.lg.just_won,
            won=False,
            raw=raw,
            available_actions=[0, 1, 2, 3, 4],
        )

    def execute_action(self, action, generated_tokens=0, uncached_input_tokens=0):
        name = action.id.name
        if name == "RESET":
            self.lg.reset()
        else:
            self.lg.press({"ACTION1": "UP", "ACTION2": "DOWN", "ACTION3": "LEFT", "ACTION4": "RIGHT"}[name])
        self.game_run.history.append(action)
        self.current_state = self._state()
        return self.current_state


def make_session(solver_mod, tmp_path):
    game = FakeEngineGame(LivesGame())
    session = solver_mod._HarnessGameSession(
        solver=types.SimpleNamespace(
            max_runtime_s_per_game=None, max_actions_per_game=None, max_generated_tokens_per_game=None,
            job_dir=None, label="test", soft_time_remaining_seconds=lambda: None,
        ),
        game=game,
        analyzer=types.SimpleNamespace(generated_tokens=0),
        game_index=0,
        pass_index=0,
        state_path=tmp_path / "state.json",
        transcript_path=tmp_path / "transcript.txt",
        analysis_html_relpath="analysis.html",
        stop_event=threading.Event(),
        viewer_data_path=tmp_path / "viewer.json",
    )
    session.seed_initial_history()
    return session


def batch(n):
    return {"actions": [{"action": name} for name in burn(n)]}


def test_off_by_default_the_batch_plays_on_through_a_lost_attempt(solver_mod, tmp_path, monkeypatch):
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_STOP", False)
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_DETECT", False)
    session = make_session(solver_mod, tmp_path)
    result = session.step_env(batch(60))
    assert result["executed_count"] == 60 and "stop_reason" not in result
    assert "attempt_lost" not in result and "attempt_lost_at" not in result
    assert "ATTEMPT LOST" not in " ".join(result.get("action_trace", []))
    assert session.game.lg.restarts == 1  # the engine restarted; nothing said so
    assert all("attempt_lost" not in (e.result or {}) for e in session.history_entries)


def test_stop_ends_the_batch_at_the_lost_attempt_like_a_terminal_state(solver_mod, tmp_path, monkeypatch):
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_STOP", True)
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_DETECT", True)
    session = make_session(solver_mod, tmp_path)
    result = session.step_env(batch(60))
    assert result["stop_reason"] == "attempt_lost" and result["stopped_early"] is True
    assert result["executed_count"] == STEPS + 1 and result["requested_count"] == 60
    assert result["attempt_lost"] is True and result["attempt_lost_at"] == [STEPS + 1]
    assert len(result["skipped_actions"]) == 60 - (STEPS + 1)
    assert result["action_trace"][STEPS].startswith(f"{STEPS + 1}: UP -> ATTEMPT LOST")
    assert result["gameplay_changed"] is True and result["no_op"] is False
    assert session.game.lg.restarts == 1 and session.game.lg.pos == session.game.lg.start_cells[0]
    lost = session.history_entries[-1]
    assert lost.result["attempt_lost"] is True and lost.result["gameplay_changed"] is True
    assert sum(1 for e in session.history_entries if (e.result or {}).get("attempt_lost")) == 1


def test_stop_in_a_single_action_call_marks_the_loss_and_leaves_the_next_call_alone(solver_mod, tmp_path, monkeypatch):
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_STOP", True)
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_DETECT", True)
    session = make_session(solver_mod, tmp_path)
    for name in burn(STEPS):
        single = session.step_env({"actions": [{"action": name}]})
        assert "attempt_lost" not in single and single.get("stop_reason") is None
    last = session.step_env({"actions": [{"action": "UP"}]})
    assert last["stop_reason"] == "attempt_lost" and last["attempt_lost_at"] == [1]
    assert last["stopped_early"] is False  # nothing was skipped
    # the board is the new attempt's: the next batch runs in full and a second loss needs a full bar again
    follow = session.step_env(batch(10))
    assert follow["executed_count"] == 10 and "stop_reason" not in follow


def test_notice_alone_records_the_loss_but_does_not_stop_the_batch(solver_mod, tmp_path, monkeypatch):
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_DETECT", True)  # NOTICE on, STOP off
    session = make_session(solver_mod, tmp_path)
    result = session.step_env(batch(60))
    assert result["executed_count"] == 60 and result.get("stop_reason") is None
    assert result["attempt_lost_at"] == [STEPS + 1]  # mid-batch: the final action's own payload would not show it
    assert result["action_trace"][STEPS].startswith(f"{STEPS + 1}: UP -> ATTEMPT LOST")


def test_a_game_over_is_still_reported_as_a_game_over_not_an_attempt_loss(solver_mod, tmp_path, monkeypatch):
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_STOP", True)
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_DETECT", True)
    session = make_session(solver_mod, tmp_path)
    lost_at = []
    for _ in range(3):
        result = session.step_env(batch(60))
        lost_at.append(result.get("attempt_lost_at"))
        if result.get("game_over"):
            break
    assert lost_at == [[STEPS + 1], [STEPS + 1], None]
    assert result["game_over"] is True and result["stop_reason"] == "game_over" and "attempt_lost" not in result


def test_reset_and_level_up_move_the_reference_board(solver_mod, tmp_path, monkeypatch):
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_STOP", True)
    monkeypatch.setattr(solver_mod, "ATTEMPT_LOSS_DETECT", True)
    session = make_session(solver_mod, tmp_path)
    up = session.step_env({"actions": [{"action": "LEFT"}] * 10})  # the goal: level 2 begins
    assert up["level_completed"] is True and session.game.lg.level == 1
    result = session.step_env(batch(60))
    assert result["attempt_lost_at"] == [STEPS + 1]
    session._execute_auto_reset()
    assert session.attempt_tracker.start == session.current_frame().grid
    again = session.step_env(batch(60))
    assert again["attempt_lost_at"] == [STEPS + 1]


# ---- the sandbox latch --------------------------------------------------------------------

SNIPPET = (
    "done = 0\n"
    "for key in ['UP'] * 6:\n"
    "    try:\n"
    "        action(key)\n"
    "        done += 1\n"
    "    except Exception:\n"
    "        pass\n"
    "print('ran', done)\n"
)


def _frame():
    return {"ascii": "", "step": 0, "level": 1, "shape": [2, 2], "grid": [[0, 0], [0, 0]]}


def _run_snippet(lose_at):
    from inference.agent.python_tool_sandbox import run_sandboxed_python

    state = {
        "current_frame": _frame(),
        "history": [{"action": "", "frame": _frame()}],
        "valid_actions": ["UP", "DOWN"],
        "death_ledger": {"attempts": []},
        "last_action_call_result": None,
    }
    calls = []

    def handler(actions, stale_after=None):
        calls.append(actions)
        result = {"executed": True, "gameplay_changed": True, "executed_count": 1, "level": 1}
        if len(calls) == lose_at:
            result.update(stop_reason="attempt_lost", attempt_lost=True, attempt_lost_at=[1])
        return {"action_result": result, "state": state}

    outcome = run_sandboxed_python(
        code=SNIPPET, timeout_seconds=20, initial_state=state, action_handler=handler,
    )
    return outcome, calls


def test_the_sandbox_refuses_further_actions_after_an_attempt_is_lost():
    outcome, calls = _run_snippet(lose_at=2)
    assert len(calls) == 2  # the third action() raised before reaching the host
    # TerminalStateActionError is a BaseException: the snippet's own `except Exception` did not swallow it
    assert "TerminalStateActionError" in outcome["error"] and "lost the attempt" in outcome["error"]
    assert "ran" not in outcome.get("stdout", "")


def test_the_sandbox_is_unchanged_when_no_attempt_is_lost():
    outcome, calls = _run_snippet(lose_at=0)
    assert len(calls) == 6 and not outcome.get("error")
    assert "ran 6" in outcome["stdout"]


# ---- the turn message ---------------------------------------------------------------------

@pytest.fixture
def agent():
    import inference.agent.tool_agent as ta

    return ta, ta.ToolAgent(model="m", base_url="http://127.0.0.1:1/v1", provider="vllm", api_key="k")


def _call_result(**extra):
    base = {
        "executed": True, "action_num": 41, "level": 1, "executed_count": 41, "requested_count": 60,
        "executed_actions": burn(41), "gameplay_changed": True, "board_changed": True,
        "valid_actions": ["UP", "DOWN", "LEFT", "RIGHT"],
    }
    base.update(extra)
    return base


def test_summary_carries_the_turn_wide_position_of_the_loss(agent):
    _, tool_agent = agent
    first = _call_result(executed_count=10, executed_actions=burn(10), action_num=10)
    second = _call_result(
        executed_count=41, requested_count=60, stopped_early=True, stop_reason="attempt_lost",
        attempt_lost=True, attempt_lost_at=[41], skipped_actions=["DOWN"] * 19, action_num=51,
    )
    summary = tool_agent._summarize_step_sequence([first, second])
    assert summary["attempt_lost_after"] == 10 + 41
    assert summary["attempt_lost_skipped"] == 19
    quiet = tool_agent._summarize_step_sequence([first])
    assert quiet["attempt_lost_after"] is None and quiet["attempt_lost_skipped"] == 0


def _opener(ta, tool_agent, summary):
    frame = ta.Frame(grid=tuple(tuple([0] * 64) for _ in range(64)), step=41, level=1)
    return tool_agent._build_user_prompt(
        41, valid_actions=["UP", "DOWN"], current_frame=frame, history_entries=[], previous_step_summary=summary,
    )


def test_the_opener_says_the_attempt_was_lost_only_when_the_notice_is_on(agent, monkeypatch):
    ta, tool_agent = agent
    summary = tool_agent._summarize_step_sequence([
        _call_result(
            stopped_early=True, stop_reason="attempt_lost", attempt_lost=True, attempt_lost_at=[41],
            skipped_actions=["DOWN"] * 19,
        )
    ])
    monkeypatch.delenv("ARC3_ATTEMPT_LOSS_NOTICE", raising=False)
    off = _opener(ta, tool_agent, summary)
    assert "Attempt lost" not in off and "You are still on the same level." in off
    monkeypatch.setenv("ARC3_ATTEMPT_LOSS_NOTICE", "1")
    on = _opener(ta, tool_agent, summary)
    line = "Attempt lost after action 41: the level restarted; plan from the new board."
    assert line in on and "The remaining 19 action(s) of that sequence were not executed." in on
    assert on.index("You are still on the same level.") < on.index(line)
    # nothing to say when the sequence kept its attempt
    plain = tool_agent._summarize_step_sequence([_call_result()])
    assert "Attempt lost" not in _opener(ta, tool_agent, plain)


def test_the_host_side_latch_and_the_turn_trace_know_the_new_stop(agent):
    ta, _ = agent
    assert ta._terminal_action_reason({"executed": True, "stop_reason": "attempt_lost"}) == "attempt_lost"
    assert ta._terminal_action_reason({"executed": True, "stop_reason": "no_op_action"}) is None
    assert "lost the attempt" in ta._terminal_action_stop_detail("attempt_lost")
    trace = ta.ToolAgent._turn_action_trace([_call_result(executed_actions=["UP"], attempt_lost=True)])
    assert trace == ["1: UP -> ATTEMPT LOST (the level restarted after this action; the game is not over)"]
