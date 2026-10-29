"""Drive the REAL solver step_env against the toy game; run by test_reset_guard.py in a subprocess.

taaf imports plotting and stats packages the repo's venv does not have, so absent ones are stubbed
here, in a process of their own, rather than in the pytest session. Prints one JSON object.

usage: reset_guard_session_probe.py <harness dir> <tfaa src dir> <environment_files dir>
"""
import importlib.abc
import importlib.machinery
import json
import os
import sys
import tempfile
import threading
import types
from pathlib import Path
from unittest import mock

harness, taaf_src, env_dir = sys.argv[1:4]
sys.path[:0] = [harness, taaf_src]


class _Stub(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    roots = {"imageio", "scipy", "matplotlib", "PIL"}

    def find_spec(self, name, path, target=None):
        if name.split(".")[0] in self.roots:
            return importlib.machinery.ModuleSpec(name, self, is_package=True)

    def create_module(self, spec):
        module = mock.MagicMock(name=spec.name)
        module.__path__, module.__spec__, module.__name__ = [], spec, spec.name
        return module

    def exec_module(self, module):
        pass


for root in sorted(_Stub.roots):
    try:
        __import__(root)
        _Stub.roots.discard(root)
    except ImportError:
        pass
sys.meta_path.append(_Stub())

import arc_agi  # noqa: E402
import inference.framework.solver as solver_mod  # noqa: E402
import taaf.game  # noqa: E402
import taaf.game_api  # noqa: E402


def make_session():
    spec = taaf.game_api.ArcadeSpec(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=env_dir)
    game = taaf.game_api.GameAPI(env_name="lad1-0000abcd", arcade_spec=spec)
    game.start_game(taaf.game.RunSession())
    tmp = Path(tempfile.mkdtemp(prefix="resetguard_"))
    session = solver_mod._HarnessGameSession(
        solver=types.SimpleNamespace(
            max_runtime_s_per_game=None, max_actions_per_game=None, max_generated_tokens_per_game=None,
            soft_time_remaining_seconds=lambda: None, job_dir=None,
        ),
        game=game, analyzer=types.SimpleNamespace(generated_tokens=0), game_index=0, pass_index=0,
        state_path=tmp / "state.json", transcript_path=tmp / "t.txt", analysis_html_relpath="a.html",
        stop_event=threading.Event(), viewer_data_path=tmp / "viewer.json",
    )
    session.seed_initial_history()
    # GameAPI sets this process-wide so the engine never wipes; the raw engine is the dangerous one
    os.environ.pop("ONLY_RESET_LEVELS", None)
    return game, session


def step(session, *names):
    result = session.step_env({"actions": [{"action": name} for name in names]})
    state = session.game.current_state.raw
    return {
        "executed": result.get("executed_actions", []),
        "stop_reason": result.get("stop_reason"),
        "levels": state.levels_completed,
        "state": state.state.name,
        "billed": session.action_count,
        "detail": result.get("stop_detail"),
    }


out = {}
os.environ["ARC3_RESET_GUARD"] = "1"
game, s = make_session()
out["start"] = step(s, "RESET")
out["mid_level"] = [step(s, "UP", "DOWN"), step(s, "RESET")]
out["twice"] = step(s, "RESET")
out["after_level_up"] = [step(s, "UP", "UP", "UP"), step(s, "RESET")]
out["batch_reset_last"] = step(s, "UP", "RESET")
out["batch_reset_twice"] = step(s, "UP", "RESET", "RESET")
for _ in range(8):  # the step bar runs out: GAME_OVER, then the harness's own RESET
    last = step(s, "DOWN")
out["death"] = last
s._execute_auto_reset()
out["after_auto_reset"] = [
    {"levels": game.current_state.raw.levels_completed, "state": game.current_state.raw.state.name},
    step(s, "RESET"),
]

os.environ["ARC3_RESET_GUARD"] = "0"
game, s = make_session()
step(s, "UP", "UP", "UP")
out["guard_off"] = step(s, "RESET")
print(json.dumps(out))
