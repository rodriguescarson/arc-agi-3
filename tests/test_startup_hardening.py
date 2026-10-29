"""Start-up hardening, behind ARC3_STARTUP_HARDENING (default off).

Since ~2026-10-21 the Kaggle platform has been slow and flaky at the start of a run, and a run is
killed when no game has moved for 15 minutes. Until the model server answers, the only moves are
the warmup RESETs, so a gateway error in one of them (or in a game's opening RESET, or while the
notebook waits for the gateway) must not end a game or the run. These tests cover the four places:

  a. the warmup RESET, the keepalive RESETs and the health poll (inference/framework/solver.py)
  b. each game's opening RESET (taaf/game_api.py, with taaf/benchmark.py skipping a game that
     still will not open)
  c. waiting for the gateway and the game list (kaggle/cells/80_run.py)
  d. ARC3_MAX_ANALYZER_FAILURES, which needs no code: v10 sets it high.

Everything is off by default, and the "off" cases below pin the upstream behaviour."""
import __future__

import ast
import asyncio
import importlib
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Callable
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOLVER = ROOT / "harness/ARC3-Inference/inference/framework/solver.py"
GAME_API = ROOT / "harness/tufa-arc-agi-framework/src/taaf/game_api.py"
CELL_80 = ROOT / "kaggle/cells/80_run.py"


class Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def _extract(path: Path, names: list[str], scope: dict):
    """Compile just the named top-level functions: the modules import the whole TAAF runtime."""
    tree = ast.parse(path.read_text())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert [n.name for n in nodes] == names
    code = compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec",
                   flags=__future__.annotations.compiler_flag)
    exec(code, scope)
    return [scope[n] for n in names]


# ---- a. keepalive (the pure loop) ---------------------------------------------------------------

def _keepalive():
    return _extract(SOLVER, ["_keepalive_until_healthy"], {"time": time, "Callable": Callable})[0]


def _failing_until(clock, ok_from, log):
    def reset():
        if clock.t < ok_from:
            log.append(("fail", clock.t))
            raise ConnectionError("gateway 502")
        log.append(("ok", clock.t))
    return reset


def test_a_failed_keepalive_reset_is_retried_soon_and_the_run_never_goes_15_minutes_without_a_move():
    keepalive, clock, log, errors = _keepalive(), Clock(), [], []
    ready_at = 17 * 60
    issued = keepalive(_failing_until(clock, 400, log), lambda: clock.t >= ready_at, lambda: False,
                       interval=300, max_seconds=3 * 3600, poll=5, clock=clock.now, sleep=clock.sleep,
                       tolerant=True, on_error=lambda exc, n: errors.append((type(exc).__name__, n)))
    assert [k for k, _ in log] == ["fail"] * 4 + ["ok"] * 2 and issued == 2
    # after the failure at 300 s the retries come after 10, 20, 40 s, not a full interval later
    assert [t for _, t in log][:5] == [300, 310, 330, 370, 430]
    assert errors == [("ConnectionError", 1), ("ConnectionError", 2), ("ConnectionError", 3), ("ConnectionError", 4)]
    moves = [0] + [t for k, t in log if k == "ok"] + [ready_at]    # the caller's first RESET is at 0
    assert max(b - a for a, b in zip(moves, moves[1:], strict=False)) < 15 * 60


def test_a_retry_delay_is_capped_and_a_permanent_outage_is_bounded_and_never_raises():
    keepalive, clock, log = _keepalive(), Clock(), []
    n = keepalive(_failing_until(clock, float("inf"), log), lambda: False, lambda: False,
                  interval=300, max_seconds=3 * 3600, poll=5, clock=clock.now, sleep=clock.sleep,
                  tolerant=True)
    times = [t for _, t in log]
    assert n == 0 and clock.t <= 3 * 3600 + 5                      # ends at max_seconds, nothing raised
    assert max(b - a for a, b in zip(times, times[1:], strict=False)) <= 60    # never backs off past the cap
    assert len(times) < 250                                          # and does not spin


def test_a_retry_never_waits_longer_than_the_interval():
    keepalive, clock, log = _keepalive(), Clock(), []
    keepalive(_failing_until(clock, float("inf"), log), lambda: False, lambda: False,
              interval=20, max_seconds=400, poll=5, clock=clock.now, sleep=clock.sleep, tolerant=True,
              retry_base=10.0, retry_cap=60.0)
    times = [t for _, t in log]
    assert max(b - a for a, b in zip(times, times[1:], strict=False)) <= 20


def test_a_due_first_reset_is_issued_at_once_when_the_callers_own_failed():
    keepalive, clock, log = _keepalive(), Clock(), []
    keepalive(_failing_until(clock, 0, log), lambda: clock.t >= 100, lambda: False, interval=300,
              max_seconds=3600, poll=5, clock=clock.now, sleep=clock.sleep, tolerant=True, due_now=True)
    assert log[0] == ("ok", 0)


def test_a_health_poll_that_raises_counts_as_not_ready_when_tolerant():
    keepalive, clock = _keepalive(), Clock()
    polls = []

    def healthy():
        polls.append(clock.t)
        if clock.t < 20:
            raise OSError("health endpoint hung up")
        return True

    assert keepalive(lambda: None, healthy, lambda: False, interval=300, max_seconds=3600, poll=5,
                     clock=clock.now, sleep=clock.sleep, tolerant=True) == 0
    assert polls == [0, 5, 10, 15, 20]


def test_a_tolerant_loop_still_stops_when_the_run_stops():
    keepalive, clock, log = _keepalive(), Clock(), []
    keepalive(_failing_until(clock, float("inf"), log), lambda: False, lambda: clock.t >= 700,
              interval=300, max_seconds=3600, poll=5, clock=clock.now, sleep=clock.sleep, tolerant=True)
    assert clock.t == 700


def test_a_off_the_keepalive_still_raises_as_before():
    keepalive, clock = _keepalive(), Clock()
    with pytest.raises(ZeroDivisionError):
        keepalive(lambda: 1 / 0, lambda: False, lambda: False, interval=300, max_seconds=3600, poll=5,
                  clock=clock.now, sleep=clock.sleep)
    with pytest.raises(OSError, match="down"):
        keepalive(lambda: None, mock.Mock(side_effect=OSError("down")), lambda: False, interval=300,
                  max_seconds=3600, clock=clock.now, sleep=clock.sleep)
    with pytest.raises(ZeroDivisionError):                          # due_now without tolerance
        keepalive(lambda: 1 / 0, lambda: False, lambda: False, interval=300, max_seconds=3600,
                  clock=clock.now, sleep=clock.sleep, due_now=True)


# ---- b. a game's opening RESET: the pure retry helper -------------------------------------------

def _retry():
    return _extract(GAME_API, ["_startup_hardening", "_start_retry_seconds", "_retry_transient"],
                    {"os": __import__("os"), "time": time})[1:]


def _flaky(failures, exc=None):
    calls = []

    def attempt():
        calls.append(1)
        if len(calls) <= failures:
            raise exc or ConnectionError("502")
        return "game"
    return attempt, calls


def test_b_retry_waits_with_doubling_backoff_up_to_the_cap_and_returns_the_result():
    _, retry = _retry()
    clock, (attempt, calls) = Clock(), _flaky(7)
    assert retry(attempt, seconds=600, what="x", clock=clock.now, sleep=clock.sleep) == "game"
    assert len(calls) == 8 and clock.t == 2 + 4 + 8 + 16 + 30 + 30 + 30      # base 2 s, capped at 30 s


def test_b_retry_gives_up_inside_its_budget_with_the_last_exception():
    _, retry = _retry()
    clock, (attempt, calls) = Clock(), _flaky(10 ** 6, exc=RuntimeError("gateway down"))
    with pytest.raises(RuntimeError, match="gateway down"):
        retry(attempt, seconds=100, what="x", clock=clock.now, sleep=clock.sleep)
    assert clock.t <= 100 and len(calls) < 10                         # bounded, no spin


def test_b_zero_seconds_is_one_try_with_no_sleep_so_the_unhardened_path_is_unchanged():
    _, retry = _retry()
    clock, (attempt, calls) = Clock(), _flaky(1)
    with pytest.raises(ConnectionError):
        retry(attempt, seconds=0.0, what="x", clock=clock.now, sleep=clock.sleep)
    assert len(calls) == 1 and clock.t == 0
    assert retry(lambda: None, seconds=0.0, what="x", clock=clock.now, sleep=clock.sleep) is None


def test_b_the_budget_is_zero_unless_the_switch_is_on(monkeypatch):
    budget, _ = _retry()
    for var in ("ARC3_STARTUP_HARDENING", "ARC3_START_RETRY_SECONDS"):
        monkeypatch.delenv(var, raising=False)
    assert budget() == 0.0
    monkeypatch.setenv("ARC3_START_RETRY_SECONDS", "45")             # a budget alone does not turn it on
    assert budget() == 0.0
    for off in ("0", "", "no", "false"):
        monkeypatch.setenv("ARC3_STARTUP_HARDENING", off)
        assert budget() == 0.0
    monkeypatch.setenv("ARC3_STARTUP_HARDENING", "1")
    assert budget() == 45.0
    monkeypatch.delenv("ARC3_START_RETRY_SECONDS")
    assert budget() == 300.0
    for junk, expected in (("abc", 300.0), ("-5", 0.0)):
        monkeypatch.setenv("ARC3_START_RETRY_SECONDS", junk)
        assert budget() == expected


# ---- c. the notebook waits for the gateway and the game list ------------------------------------

def _cell(clock, urlopen, games=None, hardening=None):
    env = {} if hardening is None else {"ARC3_STARTUP_HARDENING": hardening}
    scope = {"os": SimpleNamespace(environ=env), "time": SimpleNamespace(monotonic=clock.now, sleep=clock.sleep),
             "urlopen": urlopen, "_competition_games": games}
    fns = _extract(CELL_80, ["_wait_for_gateway", "_startup_hardening", "_gateway_wait_seconds",
                             "_competition_games_when_ready"], scope)
    return dict(zip(["wait", "hardening", "seconds", "games"], fns, strict=True))


class _Up:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _gateway_up_at(clock, t):
    def urlopen(url, timeout):
        assert url == "http://gateway:8001/api/games"
        if clock.t < t:
            raise ConnectionRefusedError("gateway not up")
        return _Up()
    return urlopen


def test_c_the_gateway_is_waited_for_up_to_an_hour_with_the_switch_and_ten_minutes_without():
    clock = Clock()
    cell = _cell(clock, _gateway_up_at(clock, 40 * 60), hardening="1")
    assert cell["seconds"]() == 3600.0
    cell["wait"]("http://gateway:8001/", cell["seconds"]())          # up after 40 minutes: found
    assert 40 * 60 <= clock.t < 40 * 60 + 10

    clock = Clock()
    off = _cell(clock, _gateway_up_at(clock, 40 * 60))
    assert off["seconds"]() == 600.0
    with pytest.raises(RuntimeError, match="did not become ready"):
        off["wait"]("http://gateway:8001/", off["seconds"]())        # the upstream limit, unchanged
    assert clock.t >= 600


def test_c_a_game_list_that_comes_back_empty_is_retried_until_the_budget_is_spent():
    clock, attempts = Clock(), []

    def games():
        attempts.append(clock.t)
        if len(attempts) <= 3:
            raise RuntimeError("Competition Arcade exposed zero environments.")
        return ["g1", "g2"]

    cell = _cell(clock, None, games=games, hardening="1")
    assert cell["games"](3600.0) == ["g1", "g2"]
    assert attempts == [0, 5, 15, 35]                                 # 5, 10, 20 s apart

    clock, attempts = Clock(), []

    def never():
        attempts.append(clock.t)
        raise RuntimeError("Competition Arcade exposed zero environments.")

    cell = _cell(clock, None, games=never, hardening="1")
    with pytest.raises(RuntimeError, match="zero environments"):
        cell["games"](3600.0)
    assert clock.t <= 3600 and attempts[-1] > 3000                    # kept trying almost to the end
    assert max(b - a for a, b in zip(attempts, attempts[1:], strict=False)) <= 60


def test_c_the_cell_only_takes_the_retrying_path_with_the_switch_on():
    src = CELL_80.read_text()
    assert ("bm.games = _competition_games_when_ready(_gateway_deadline) if _startup_hardening() "
            "else _competition_games()") in src
    assert '_wait_for_gateway(os.environ["ARC_BASE_URL"], _gateway_wait_seconds())' in src
    sys.path.insert(0, str(ROOT / "kaggle"))
    import build_notebook

    cfg = __import__("json").loads((ROOT / "kaggle/variants/v1f-multithread-load.json").read_text())
    build_notebook.check_cells(build_notebook.render_cells(cfg))     # the cell still compiles
    assert "ARC3_STARTUP_HARDENING" not in cfg["setup_env"]          # off in v1f


# ---- d. ARC3_MAX_ANALYZER_FAILURES --------------------------------------------------------------

def test_d_the_failure_cap_is_an_env_switch_that_nothing_else_reads(monkeypatch):
    env_number = _extract(SOLVER, ["_env_number"], {"os": __import__("os")})[0]
    monkeypatch.delenv("ARC3_MAX_ANALYZER_FAILURES", raising=False)
    assert env_number("ARC3_MAX_ANALYZER_FAILURES", 10, int) == 10
    monkeypatch.setenv("ARC3_MAX_ANALYZER_FAILURES", "1000")
    assert env_number("ARC3_MAX_ANALYZER_FAILURES", 10, int) == 1000
    monkeypatch.setenv("ARC3_MAX_ANALYZER_FAILURES", "lots")        # a typo cannot take the run down
    assert env_number("ARC3_MAX_ANALYZER_FAILURES", 10, int) == 10

    users = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "harness").rglob("*.py")
                   if "MAX_CONSECUTIVE_ANALYZER_FAILURES" in p.read_text()
                   or "ARC3_MAX_ANALYZER_FAILURES" in p.read_text())
    assert users == ["harness/ARC3-Inference/inference/framework/solver.py"]
    src = SOLVER.read_text()
    assert src.count("MAX_CONSECUTIVE_ANALYZER_FAILURES") == 3     # the definition and one comparison
    # the retry loop is still ended by the time budget, the stop event and the token limit
    assert "if self.should_stop():\n                        break\n                    time.sleep(ANALYZER_RETRY_BACKOFF_SECONDS)" in src


# ---- the real modules: GameAPI, Benchmark and the warmup in _play_inner -------------------------

@pytest.fixture(scope="module")
def tm():
    """taaf and the solver, imported for real. imageio and scipy are only used by taaf.diagnostics'
    plotting and are not installed here, so they are stubbed for the import if they are missing;
    everything this fixture added to sys.modules is removed again afterwards."""
    before = set(sys.modules)
    path = list(sys.path)
    stubbed = []
    for name in ("imageio", "imageio.v3", "scipy", "scipy.stats"):
        try:
            importlib.import_module(name)
        except ImportError:
            sys.modules[name] = mock.MagicMock()
            stubbed.append(name)
    for sub in ("harness/tufa-arc-agi-framework/src", "harness/ARC3-Inference"):
        sys.path.insert(0, str(ROOT / sub))
    try:
        ns = SimpleNamespace(
            ga=importlib.import_module("taaf.game_api"),
            bench=importlib.import_module("taaf.benchmark"),
            game=importlib.import_module("taaf.game"),
            taaf_solver=importlib.import_module("taaf.solver"),
            solver=importlib.import_module("inference.framework.solver"),
        )
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"the TAAF runtime cannot be imported here: {exc!r}")
    try:
        yield ns
    finally:
        sys.path[:] = path
        for name in set(sys.modules) - before:
            sys.modules.pop(name, None)
        for name in stubbed:
            sys.modules.pop(name, None)


def _frame(tm):
    import numpy as np

    return SimpleNamespace(levels_completed=0, win_levels=3, frame=[np.zeros((64, 64), dtype=np.int8)],
                           available_actions=[0, 1], state=None, guid="g")


class _Arcade:
    """arc_agi.Arcade as far as GameAPI sees it. Each `make` pops the next scripted outcome:
    "ok", "none" (arc_agi swallowed the error), "noframe" (a wrapper whose RESET failed), or an
    exception to raise."""

    def __init__(self, tm, makes, card_failures=0):
        self.tm, self.makes, self.card_failures = tm, list(makes), card_failures
        self.make_calls = self.card_calls = 0
        self.closed = []

    def create_scorecard(self):
        self.card_calls += 1
        if self.card_calls <= self.card_failures:
            raise ConnectionError("scorecard 503")
        return "card-1"

    def close_scorecard(self, card_id):
        self.closed.append(card_id)

    def make(self, game_id, scorecard_id=None):
        self.make_calls += 1
        outcome = self.makes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        if outcome == "none":
            return None
        info = SimpleNamespace(game_id="ls20-abc", baseline_actions=[10, 10, 10])
        return SimpleNamespace(environment_info=info,
                               observation_space=_frame(self.tm) if outcome == "ok" else None)


def _open(tm, monkeypatch, arcade, *, hardening, mode=None, retry="300"):
    """GameAPI.start_game against `arcade`, with a fake clock so the backoff costs nothing."""
    clock = Clock()
    monkeypatch.setattr(tm.ga, "time", SimpleNamespace(monotonic=clock.now, sleep=clock.sleep))
    monkeypatch.setenv("ONLY_RESET_LEVELS", "x")                    # start_game sets it; keep it test-local
    monkeypatch.setenv("ARC3_START_RETRY_SECONDS", retry)
    if hardening:
        monkeypatch.setenv("ARC3_STARTUP_HARDENING", "1")
    else:
        monkeypatch.delenv("ARC3_STARTUP_HARDENING", raising=False)
    spec = tm.ga.ArcadeSpec() if mode is None else tm.ga.ArcadeSpec(operation_mode=mode)
    session = tm.game.RunSession()
    session.get_or_make(spec, lambda: arcade)
    game = tm.ga.GameAPI(env_name="ls20", arcade_spec=spec)
    return game, session, clock


def test_b_off_a_failed_opening_reset_fails_the_game_at_once(tm, monkeypatch):
    arcade = _Arcade(tm, ["noframe", "ok"])
    game, session, clock = _open(tm, monkeypatch, arcade, hardening=False)
    with pytest.raises(RuntimeError, match="observation_space is None after make"):
        game.start_game(session)
    assert arcade.make_calls == 1 and clock.t == 0

    arcade = _Arcade(tm, ["none", "ok"])
    game, session, clock = _open(tm, monkeypatch, arcade, hardening=False)
    with pytest.raises(RuntimeError, match="returned None"):
        game.start_game(session)
    assert arcade.make_calls == 1 and clock.t == 0


def test_b_on_a_failed_opening_reset_is_retried_until_the_game_opens(tm, monkeypatch):
    arcade = _Arcade(tm, ["noframe", "none", ConnectionError("502"), "ok"])
    game, session, clock = _open(tm, monkeypatch, arcade, hardening=True)
    state = game.start_game(session)
    assert arcade.make_calls == 4 and clock.t == 2 + 4 + 8
    assert game.game_id == "ls20-abc" and game.number_of_levels == 3 and state.raw.win_levels == 3
    assert game.game_run is not None and game.game_run.state == "playing"


def test_b_on_a_game_that_never_opens_fails_after_the_budget_not_forever(tm, monkeypatch):
    arcade = _Arcade(tm, ["noframe"] * 100)
    game, session, clock = _open(tm, monkeypatch, arcade, hardening=True, retry="120")
    with pytest.raises(RuntimeError, match="did not open the game"):
        game.start_game(session)
    assert clock.t <= 120 and arcade.make_calls < 15


def test_b_on_the_scorecard_open_is_retried_too(tm, monkeypatch):
    arcade = _Arcade(tm, ["ok"], card_failures=2)
    game, session, clock = _open(tm, monkeypatch, arcade, hardening=True)
    game.start_game(session)
    assert arcade.card_calls == 3 and clock.t == 2 + 4
    arcade = _Arcade(tm, ["ok"], card_failures=2)                    # and off: one try
    game, session, clock = _open(tm, monkeypatch, arcade, hardening=False)
    with pytest.raises(ConnectionError):
        game.start_game(session)
    assert arcade.card_calls == 1


def test_b_competition_mode_retries_only_the_first_scorecard_open(tm, monkeypatch):
    import arc_agi

    arcade = _Arcade(tm, ["ok"] + ["noframe"] * 10, card_failures=1)
    mode = arc_agi.OperationMode.COMPETITION
    first, session, clock = _open(tm, monkeypatch, arcade, hardening=True, mode=mode, retry="20")
    first.start_game(session)
    assert arcade.card_calls == 2 and clock.t == 2                    # the gateway call is retried
    second = tm.ga.GameAPI(env_name="ls21", arcade_spec=first.arcade_spec)
    with pytest.raises(RuntimeError, match="did not open the game"):  # a game that cannot open ...
        second.start_game(session)
    assert arcade.closed == []                                        # ... leaves the first game's card open
    scorecard = first._competition_scorecard
    assert scorecard.active_runs == 1 and not scorecard.closed


def test_b_in_competition_mode_a_first_game_that_cannot_open_leaves_the_scorecard_for_the_others(tm, monkeypatch):
    import arc_agi

    mode = arc_agi.OperationMode.COMPETITION
    arcade = _Arcade(tm, ["noframe"] * 4 + ["ok"])
    first, session, clock = _open(tm, monkeypatch, arcade, hardening=True, mode=mode, retry="20")
    with pytest.raises(RuntimeError, match="did not open the game"):
        first.start_game(session)
    scorecard = first._competition_scorecard
    assert not scorecard.closed and scorecard.active_runs == 0 and arcade.closed == []
    second = tm.ga.GameAPI(env_name="ls21", arcade_spec=first.arcade_spec)
    second.start_game(session)                                        # opens on the same, still open card
    assert scorecard.active_runs == 1 and arcade.card_calls == 1

    # off, upstream behaviour: the failed first game closes the card and every later game fails
    arcade = _Arcade(tm, ["noframe", "ok"])
    first, session, clock = _open(tm, monkeypatch, arcade, hardening=False, mode=mode)
    with pytest.raises(RuntimeError, match="observation_space is None after make"):
        first.start_game(session)
    assert first._competition_scorecard.closed and arcade.closed == ["card-1"]
    second = tm.ga.GameAPI(env_name="ls21", arcade_spec=first.arcade_spec)
    with pytest.raises(RuntimeError, match="already closed"):
        second.start_game(session)
    assert clock.t == 0


class _Games:
    """A Game and Solver pair for Benchmark.run: `failing` maps an env name to the exception its
    start_game raises, `played` records what the solver was handed."""

    def __init__(self, tm, failing):
        self.failing, self.played = failing, []
        import arcengine
        import numpy as np

        outer = self

        @dataclass
        class FakeGame(tm.game.Game):
            env_name: str = field(kw_only=True, default="")

            def _start_game(self, session):
                if self.env_name in outer.failing:
                    raise outer.failing[self.env_name]
                self.game_id, self.number_of_levels, self.base_actions_per_level = self.env_name, 1, [5]
                raw = SimpleNamespace(levels_completed=0, win_levels=1, state=arcengine.GameState.NOT_FINISHED,
                                      frame=[np.zeros((64, 64), dtype=np.int8)], available_actions=[0, 1])
                return tm.game.GameState(raw=raw)

            def _execute_action(self, action):
                raise AssertionError("not played")

        @dataclass
        class FakeSolver(tm.taaf_solver.Solver):
            async def _run_games(self, games):
                outer.played.extend(g.game_id for g in games)
                for g in games:
                    g.finish_game()

        self.FakeGame, self.FakeSolver = FakeGame, FakeSolver

    def run(self, tm, names):
        bm = tm.bench.Benchmark(label="t", games=[self.FakeGame(env_name=n) for n in names],
                                solver=self.FakeSolver(label="s"))
        with mock.patch.object(sys.modules["taaf.diagnostics"], "run_summary_text", return_value=""):
            asyncio.run(bm.run(minimal_diagnostics=True))
        return bm


def test_b_off_one_game_that_will_not_open_ends_the_run_as_before(tm, monkeypatch, capsys):
    monkeypatch.delenv("ARC3_STARTUP_HARDENING", raising=False)
    games = _Games(tm, {"b": RuntimeError("env 'b' observation_space is None after make()")})
    with pytest.raises(RuntimeError, match="observation_space"):
        games.run(tm, ["a", "b", "c"])
    assert games.played == []


def test_b_on_one_game_that_will_not_open_is_skipped_and_the_rest_play(tm, monkeypatch, capsys):
    monkeypatch.setenv("ARC3_STARTUP_HARDENING", "1")
    games = _Games(tm, {"b": RuntimeError("gateway 502"), "e": RuntimeError("gateway 502"),
                        "f": RuntimeError("gateway 502")})
    bm = games.run(tm, ["a", "b", "c", "d", "e", "f", "g"])      # two failures in a row never happen here
    assert games.played == ["a", "c", "d", "g"] and [r.game_id for r in bm.game_runs] == games.played
    out = capsys.readouterr().out
    assert "could not start 'b'" in out and "could not start 'f'" in out


def test_b_on_the_run_still_stops_when_games_keep_failing_to_open(tm, monkeypatch):
    monkeypatch.setenv("ARC3_STARTUP_HARDENING", "1")
    down = {n: RuntimeError("gateway down") for n in "bcd"}
    games = _Games(tm, down)
    with pytest.raises(RuntimeError, match="gateway down"):          # the third one in a row
        games.run(tm, ["a", "b", "c", "d", "e"])
    assert games.played == []
    games = _Games(tm, {"b": down["b"], "c": down["c"]})
    bm = games.run(tm, ["a", "b", "c", "d"])                         # two in a row is survivable
    assert games.played == ["a", "d"] and len(bm.game_runs) == 2


def test_b_on_a_run_with_no_game_that_opens_is_an_error_and_a_failed_check_is_not_skipped(tm, monkeypatch):
    monkeypatch.setenv("ARC3_STARTUP_HARDENING", "1")
    with pytest.raises(RuntimeError, match="no game could be started"):
        _Games(tm, {"a": RuntimeError("gateway down")}).run(tm, ["a"])
    games = _Games(tm, {"b": AssertionError("number_of_levels")})   # start_game's own check: card left open
    with pytest.raises(AssertionError):
        games.run(tm, ["a", "b", "c"])


# ---- a. the warmup game in _HarnessGameSession._play_inner --------------------------------------

def _warmup_session(tm, monkeypatch, tmp_path, *, hardening, fail_window, healthy_at):
    """A session reduced to what the warmup branch of _play_inner touches. Returns the session,
    the clock and the log of RESET outcomes."""
    s, clock, log = tm.solver, Clock(), []
    monkeypatch.setattr(s, "STARTUP_HARDENING", hardening)
    monkeypatch.setattr(s, "WARMUP_KEEPALIVE_SECONDS", 300.0)
    monkeypatch.setattr(s, "WARMUP_HEALTH_URL", "http://127.0.0.1:8001/health")
    monkeypatch.setattr(s, "WARMUP_KEEPALIVE_MAX_SECONDS", 3 * 3600.0)
    monkeypatch.setitem(s._keepalive_until_healthy.__kwdefaults__, "clock", clock.now)
    monkeypatch.setitem(s._keepalive_until_healthy.__kwdefaults__, "sleep", clock.sleep)
    done = []

    def health(url, timeout=5.0):
        if clock.t >= healthy_at:
            done.append(clock.t)
            return True
        return False

    monkeypatch.setattr(s, "_health_ok", health)
    session = object.__new__(s._HarnessGameSession)
    run = SimpleNamespace(game_id="ls20", final_score=None, state="playing", solver_note=None)
    session.game = SimpleNamespace(game_run=run)
    session.solver = SimpleNamespace(_claim_warmup_slot=lambda: True)
    session.analyzer = SimpleNamespace(total_tokens=0)
    session.state_path = tmp_path / "state.json"
    session._finish_if_needed = lambda: None
    session._write_analysis_html = lambda: None
    session.write_viewer_payload = lambda: None
    session.should_stop = lambda: bool(done)                         # play ends once the server is up

    def reset():
        if fail_window[0] <= clock.t < fail_window[1]:
            log.append(("fail", clock.t))
            raise ConnectionError("gateway 502")
        log.append(("ok", clock.t))

    session._execute_auto_reset = reset
    return session, clock, log, run


def test_a_off_a_failed_warmup_reset_ends_the_game_as_before(tm, monkeypatch, tmp_path):
    session, _, log, _ = _warmup_session(tm, monkeypatch, tmp_path, hardening=False,
                                         fail_window=(0, 60), healthy_at=1000)
    with pytest.raises(ConnectionError):
        session._play_inner()
    assert log == [("fail", 0)]                                       # no retry, no keepalive

    session, _, log, _ = _warmup_session(tm, monkeypatch, tmp_path, hardening=False,
                                         fail_window=(200, 10 ** 9), healthy_at=1000)
    with pytest.raises(ConnectionError):                              # first RESET fine, keepalive's fails
        session._play_inner()
    assert log == [("ok", 0), ("fail", 300)]

    session, _, log, run = _warmup_session(tm, monkeypatch, tmp_path, hardening=True,
                                           fail_window=(200, 400), healthy_at=1000)
    session._play_inner()                                             # the same outage, hardened
    assert [t for k, t in log if k == "fail"] == [300, 310, 330, 370] and run.state == "playing"


def test_a_on_a_failed_warmup_reset_is_retried_at_once_and_the_game_keeps_going(tm, monkeypatch, tmp_path):
    session, clock, log, run = _warmup_session(tm, monkeypatch, tmp_path, hardening=True,
                                               fail_window=(0, 5), healthy_at=1000)
    session._play_inner()                                             # does not raise
    assert log[:3] == [("fail", 0), ("fail", 0), ("ok", 10)]          # the keepalive's first try, then 10 s on
    oks = [t for k, t in log if k == "ok"]
    assert oks == [10, 310, 610, 910]
    assert max(b - a for a, b in zip([0] + oks, oks + [1000], strict=False)) < 15 * 60
    assert run.state == "playing" and run.solver_note == "tokens=0"   # not marked crashed


def test_a_on_a_gateway_that_fails_until_the_model_is_up_does_not_crash_the_game(tm, monkeypatch, tmp_path):
    session, clock, log, run = _warmup_session(tm, monkeypatch, tmp_path, hardening=True,
                                               fail_window=(0, 10 ** 9), healthy_at=2400)
    session._play_inner()
    assert run.state == "playing" and clock.t >= 2400
    assert all(k == "fail" for k, _ in log) and len(log) > 20        # it kept trying the whole time
    times = [t for _, t in log]
    assert max(b - a for a, b in zip(times, times[1:], strict=False)) <= 60


def test_a_the_health_poll_swallows_errors_and_times_out(tm):
    assert tm.solver._health_ok("http://127.0.0.1:1/health", timeout=0.2) is False
    assert tm.solver._health_ok("not a url") is False
