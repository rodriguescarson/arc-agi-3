"""The startup keepalive in inference/framework/solver.py.

The competition rerun ends a submission when no game has moved for 15 minutes; since mid-October
the model server can take longer than that to load, and two draws that had scored ~29.5 scored
0.00. The warmup game now RESETs every few minutes until the analyzer's /health answers."""
import __future__

import ast
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / "harness/ARC3-Inference/inference/framework/solver.py"


def _load():
    # solver.py imports the whole TAAF runtime; compile only the pure helper
    tree = ast.parse(SOLVER.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_keepalive_until_healthy")
    scope = {"time": time, "Callable": Callable}
    code = compile(ast.Module(body=[node], type_ignores=[]), str(SOLVER), "exec",
                   flags=__future__.annotations.compiler_flag)
    exec(code, scope)
    return scope["_keepalive_until_healthy"]


class Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def test_resets_every_interval_until_the_server_is_healthy():
    keepalive, clock, resets = _load(), Clock(), []
    ready_at = 17 * 60                                    # server answers after 17 minutes
    issued = keepalive(lambda: resets.append(clock.t), lambda: clock.t >= ready_at, lambda: False,
                       interval=300, max_seconds=3 * 3600, poll=5, clock=clock.now, sleep=clock.sleep)
    assert issued == 3 and resets == [300, 600, 900]     # no 15-minute gap without a move
    gaps = [b - a for a, b in zip([0] + resets, resets + [ready_at], strict=True)]
    assert max(gaps) < 15 * 60


def test_no_reset_when_the_server_is_already_up():
    keepalive, clock = _load(), Clock()
    assert keepalive(lambda: 1 / 0, lambda: True, lambda: False, interval=300, max_seconds=60,
                     clock=clock.now, sleep=clock.sleep) == 0


def test_stops_when_the_run_stops_or_the_cap_is_reached():
    keepalive, clock = _load(), Clock()
    assert keepalive(lambda: None, lambda: False, lambda: clock.t >= 400, interval=300,
                     max_seconds=3600, poll=5, clock=clock.now, sleep=clock.sleep) == 1
    clock2 = Clock()
    n = keepalive(lambda: None, lambda: False, lambda: False, interval=300, max_seconds=3600,
                  poll=5, clock=clock2.now, sleep=clock2.sleep)
    assert n == 11 and clock2.t <= 3605                  # gives up after max_seconds


def test_the_notebook_turns_it_on_for_every_variant():
    import json
    import sys

    sys.path.insert(0, str(ROOT / "kaggle"))
    import build_notebook

    for path in sorted((ROOT / "kaggle" / "variants").glob("*.json")):
        env = dict(build_notebook.render_cells(json.loads(path.read_text())))["00_env.py"]
        assert 'os.environ["ARC3_WARMUP_KEEPALIVE_SECONDS"] = "300"' in env, path.name
        assert 'os.environ["ARC3_WARMUP_HEALTH_URL"] = "http://127.0.0.1:8001/health"' in env, path.name


def test_first_request_grace_outlasts_slow_loading():
    """A game abandons itself after 10 failed requests once its first-request grace is spent; with
    loads of 40+ minutes, 900 s would let the first games die before the server answers."""
    import json
    import sys

    sys.path.insert(0, str(ROOT / "kaggle"))
    import build_notebook

    for path in sorted((ROOT / "kaggle" / "variants").glob("*.json")):
        env = dict(build_notebook.render_cells(json.loads(path.read_text())))["00_env.py"]
        assert 'os.environ["ARC3_HTTP_RETRY_INITIAL_SECONDS"] = "5400"' in env, path.name

