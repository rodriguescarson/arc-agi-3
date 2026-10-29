"""ARC3_RESET_GUARD: a model RESET with nothing to restart is refused, never executed.

arcengine's handle_reset restarts the CURRENT level when at least one non-RESET action has been
taken on it, and performs a FULL game reset when none has: at game start, right after a level-up,
right after any RESET. Hidden RESET (EXPOSE_RESET off) hid the problem; exposing it (or a model
calling it anyway) would wipe a run. The harness mirrors the engine's counter and refuses instead.
"""
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest
from arcengine import ActionInput, GameAction, GameState

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "harness" / "ARC3-Inference"
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from inference.agent.action_names import reset_guard_enabled  # noqa: E402
from inference.utils.reset_guard import REFUSAL, ResetGuard  # noqa: E402
from toy_ladder import Lad1  # noqa: E402

ENGINE_ACTION = {"UP": GameAction.ACTION1, "DOWN": GameAction.ACTION2, "RESET": GameAction.RESET}
LS20_LEVEL_1 = "RIGHT LEFT UP DOWN LEFT LEFT LEFT UP UP UP RIGHT UP RIGHT RIGHT RIGHT UP UP UP LEFT UP UP UP".split()


@pytest.fixture(autouse=True)
def _raw_engine(monkeypatch):
    # GameAPI sets this process-wide after its first game starts; without it the engine wipes
    monkeypatch.delenv("ONLY_RESET_LEVELS", raising=False)
    monkeypatch.delenv("ARC3_RESET_GUARD", raising=False)


# ---- the mirror ------------------------------------------------------------------------------

def test_a_fresh_level_has_nothing_to_restart():
    guard = ResetGuard()
    assert guard.refusal() == REFUSAL


def test_any_executed_action_makes_reset_meaningful_even_a_no_op():
    guard = ResetGuard()
    guard.note_action(is_reset=False, level_changed=False)
    assert guard.refusal() is None


def test_reset_and_level_change_zero_the_count():
    guard = ResetGuard()
    for _ in range(5):
        guard.note_action(is_reset=False, level_changed=False)
    guard.note_action(is_reset=True, level_changed=False)
    assert guard.refusal() == REFUSAL
    guard.note_action(is_reset=False, level_changed=False)
    guard.note_action(is_reset=False, level_changed=True)  # the action that completed the level
    assert guard.refusal() == REFUSAL


def test_the_refusal_says_nothing_was_spent():
    assert "NOT executed" in REFUSAL and "no action was spent" in REFUSAL


def test_switch_is_off_unless_asked(monkeypatch):
    assert reset_guard_enabled() is False
    for value in ("1", "on", "true", "YES"):
        monkeypatch.setenv("ARC3_RESET_GUARD", value)
        assert reset_guard_enabled() is True
    for value in ("0", "off", "", "no"):
        monkeypatch.setenv("ARC3_RESET_GUARD", value)
        assert reset_guard_enabled() is False


# ---- the mirror against the real engine ------------------------------------------------------

def _play(game, guard, op, honour):
    """One step the way the solver does it: the harness resets after a death, a guarded RESET
    that has nothing to restart is not sent. Returns True when the op was executed."""
    if game._state == GameState.GAME_OVER:
        game.perform_action(ActionInput(id=GameAction.RESET), raw=True)
        guard.note_action(is_reset=True, level_changed=False)
    is_reset = op == "RESET"
    if is_reset and honour and guard.refusal():
        return False
    before = game._score
    game.perform_action(ActionInput(id=ENGINE_ACTION[op]), raw=True)
    guard.note_action(is_reset=is_reset, level_changed=game._score != before)
    return True


def test_mirror_equals_the_engines_counter_and_a_guarded_run_never_loses_a_level():
    rng = random.Random(7)
    for _ in range(60):
        game, guard, best = Lad1(), ResetGuard(), 0
        for _ in range(60):
            if game._state == GameState.WIN:
                break
            op = rng.choices(["UP", "DOWN", "RESET"], weights=[5, 3, 3])[0]
            # the invariant: a RESET is allowed exactly when the engine would restart a level
            assert (guard.refusal() is None) == (game._action_count > 0)
            _play(game, guard, op, honour=True)
            assert game._score >= best, "a guarded RESET must never take a completed level away"
            best = game._score


def test_unguarded_the_same_toy_wipes_on_reset_after_level_up():
    game = Lad1()
    for _ in range(3):
        game.perform_action(ActionInput(id=GameAction.ACTION1), raw=True)
    assert game._score == 1
    frame = game.perform_action(ActionInput(id=GameAction.RESET), raw=True)
    assert frame.levels_completed == 0 and frame.full_reset


def _ls20_dir():
    for base in (os.environ.get("ARC3_ENV_DIR"), ROOT / "data" / "kaggle" / "environment_files",
                 ROOT / "data" / "kaggle" / "arc-prize-2026-arc-agi-3" / "environment_files"):
        if base and (Path(base) / "ls20").is_dir():
            return Path(base)
    return None


@pytest.mark.skipif(_ls20_dir() is None, reason="public games not downloaded (set ARC3_ENV_DIR)")
def test_real_ls20_mid_level_reset_restarts_one_level_and_reset_after_level_up_is_refused():
    import arc_agi
    import numpy as np

    arcade = arc_agi.Arcade(environments_dir=str(_ls20_dir()), operation_mode=arc_agi.OperationMode.OFFLINE)
    gid = next(e.game_id for e in arcade.available_environments if e.game_id.startswith("ls20"))
    env = arcade.make(gid, seed=0)
    keys = {"UP": GameAction.ACTION1, "DOWN": GameAction.ACTION2, "LEFT": GameAction.ACTION3, "RIGHT": GameAction.ACTION4}
    guard = ResetGuard()

    def send(action):
        before = env._game._score
        frame = env.step(action)
        guard.note_action(is_reset=action == GameAction.RESET, level_changed=frame.levels_completed != before)
        return frame

    assert guard.refusal() == REFUSAL                       # game start
    for move in LS20_LEVEL_1:
        frame = send(keys[move])
    assert frame.levels_completed == 1
    level_2_start = np.array(frame.frame[-1])
    assert guard.refusal() == REFUSAL                       # right after the level-up

    for move in ("UP", "UP", "LEFT", "DOWN", "RIGHT"):
        frame = send(keys[move])
    assert guard.refusal() is None and not np.array_equal(np.array(frame.frame[-1]), level_2_start)
    frame = send(GameAction.RESET)                          # (1) mid-level: only this level restarts
    assert frame.levels_completed == 1 and not frame.full_reset
    assert np.array_equal(np.array(frame.frame[-1]), level_2_start)
    assert guard.refusal() == REFUSAL                       # a second RESET would restart nothing...
    frame = send(GameAction.RESET)                          # ...and the raw engine makes it a full reset
    assert frame.levels_completed == 0 and frame.full_reset

    for move in LS20_LEVEL_1:                               # (2) RESET straight after a level-up
        frame = send(keys[move])
    assert frame.levels_completed == 1 and guard.refusal() == REFUSAL
    frame = env.step(GameAction.RESET)                      # what the guard stops from being sent
    assert frame.levels_completed == 0 and frame.full_reset


# ---- the wiring in the solver and the sandbox -----------------------------------------------

def test_the_solver_refuses_before_executing_and_never_for_the_harness_own_resets(tmp_path):
    env_dir = tmp_path / "environment_files" / "lad1" / "0000abcd"
    env_dir.mkdir(parents=True)
    (env_dir / "lad1.py").write_text((ROOT / "tests" / "toy_ladder.py").read_text())
    (env_dir / "metadata.json").write_text(json.dumps(
        {"game_id": "lad1-0000abcd", "title": "Lad1", "baseline_actions": [3, 3, 3], "tags": ["keyboard"]}
    ))
    probe = ROOT / "tests" / "reset_guard_session_probe.py"
    done = subprocess.run(
        [sys.executable, str(probe), str(HARNESS), str(ROOT / "harness" / "tufa-arc-agi-framework" / "src"),
         str(tmp_path / "environment_files")],
        capture_output=True, text=True, timeout=180,
    )
    assert done.returncode == 0, done.stderr[-3000:]
    out = json.loads(done.stdout.strip().splitlines()[-1])

    def refused(step):
        return step["stop_reason"] == "reset_refused" and step["executed"] == []

    assert refused(out["start"]) and out["start"]["billed"] == 0
    after_moves, mid_reset = out["mid_level"]
    assert mid_reset["executed"] == ["RESET"] and mid_reset["billed"] == after_moves["billed"] + 1
    assert refused(out["twice"]) and out["twice"]["billed"] == mid_reset["billed"]
    levelled, reset_after = out["after_level_up"]
    assert levelled["levels"] == 1
    assert refused(reset_after) and reset_after["levels"] == 1 and reset_after["billed"] == levelled["billed"]
    assert out["batch_reset_last"]["executed"] == ["UP", "RESET"]
    assert out["batch_reset_twice"]["executed"] == ["UP", "RESET"]
    assert out["batch_reset_twice"]["stop_reason"] == "reset_refused"
    assert out["death"]["state"] == "GAME_OVER"
    restarted, after_death_reset = out["after_auto_reset"]
    assert restarted["state"] == "NOT_FINISHED" and restarted["levels"] == 1
    assert refused(after_death_reset) and after_death_reset["levels"] == 1
    # guard off is the legacy path: the same RESET executes, and on the raw engine it wipes
    assert out["guard_off"]["executed"] == ["RESET"] and out["guard_off"]["levels"] == 0


def test_the_sandbox_raises_the_refusal_inside_the_snippet():
    from inference.agent.python_tool_sandbox import _SANDBOX_BOOTSTRAP, run_sandboxed_python

    compile(_SANDBOX_BOOTSTRAP, "<sandbox>", "exec")
    refusal = {"executed": False, "stop_reason": "reset_refused", "stop_detail": REFUSAL, "valid_actions": []}
    frame = {"ascii": "B", "step": 0, "level": 1, "shape": [1, 1], "grid": [[0]]}
    state = {"current_frame": frame, "history": [{"action": "", "frame": frame}], "valid_actions": ["UP"],
             "death_ledger": {"attempts": []}, "last_action_call_result": None}
    result = run_sandboxed_python(
        code="try:\n    action(['RESET'])\nexcept RuntimeError as exc:\n    print('REFUSED', exc)\n",
        timeout_seconds=20,
        initial_state=state,
        action_handler=lambda *a, **k: {"action_result": refusal, "state": {}},
    )
    assert not result.get("error"), result
    assert result["stdout"].startswith("REFUSED RESET was NOT executed and no action was spent")


# ---- the prompt ------------------------------------------------------------------------------

def _prompt(monkeypatch, expose, guard):
    from inference.agent import tool_agent

    monkeypatch.setenv("ARC3_ACTION_INFO", "1")
    for key, value in (("EXPOSE_RESET", expose), ("ARC3_RESET_GUARD", guard)):
        monkeypatch.setenv(key, value) if value else monkeypatch.delenv(key, raising=False)
    return tool_agent._build_system_prompt(tool_output_tokens=3072)


def test_prompt_wording_only_changes_when_both_switches_are_on(monkeypatch):
    from inference.agent.prompts import RESET_GUARDED_ADDENDUM, RESET_INFO_ADDENDUM

    hidden = _prompt(monkeypatch, None, None)
    assert RESET_INFO_ADDENDUM not in hidden and RESET_GUARDED_ADDENDUM not in hidden
    assert _prompt(monkeypatch, None, "1") == hidden              # nothing to describe: RESET is hidden
    franzen = _prompt(monkeypatch, "on", None)
    assert RESET_INFO_ADDENDUM in franzen and RESET_GUARDED_ADDENDUM not in franzen
    guarded = _prompt(monkeypatch, "on", "1")
    assert RESET_GUARDED_ADDENDUM in guarded and RESET_INFO_ADDENDUM not in guarded
    for must in ("CURRENT level", "costs 1 action", "UNDO", "refused", "first game action in a Python snippet"):
        assert must in RESET_GUARDED_ADDENDUM
