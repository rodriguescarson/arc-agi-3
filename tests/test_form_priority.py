"""D' slot priority (shiiin9, Apache-2.0) vendored as inference/agent/form_priority.py for v8.

Checks: the vendored code computes the formula its docstring states; install_d() patches our
harness (Franzen's tree) where it should; and on a live _PriorityGate it changes who gets a freed
slot: an advanced game now beats an unstarted one, where Franzen's gate always admits unstarted
games first."""
import math
import os
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for sub in ("harness/ARC3-Inference", "harness/tufa-arc-agi-framework/src"):
    if str(ROOT / sub) not in sys.path:
        sys.path.insert(0, str(ROOT / sub))

import inference.agent.form_priority as fp  # noqa: E402

PRIORITY_KEYS = ("ARC3_PRIORITY_PACE", "ARC3_PRIORITY_REFRESH_QUEUE", "ARC3_PRIORITY_TAIL_FADE",
                 "ARC3_PRIORITY_TAIL_FADE_FRACTION")


def documented(level, a, t, pace, n, phi=1.0):
    """The docstring's equation, written out independently of the vendored code."""
    nc = min(10, max(6, n or 10))
    norm = 55 / (nc * (nc + 1) / 2)
    A = (1 + 0.5 * (level - 1)) * norm * (300 / (300 + a)) ** 2.5
    M = min(4.0, max(0.25, (30_000 / pace) ** 0.4)) if pace > 0 else 1.0
    T = 225_000 * (min(2.0, max(0.5, pace / 30_000)) ** 0.5 if pace > 0 else 1.0)
    C = 0.1 * max(0.1, 1 - a / 115) + 0.9 * max(0.1, 1 - t / T)
    B = (0, 10, 14, 16)[min(max(0, (n or 10) - level), 3)]
    return A * M * C + B * phi


@pytest.mark.parametrize("level,a,t,pace,n,phi", [
    (1, 0, 0, 0, 7, 1.0), (3, 40, 50_000, 0, 7, 1.0), (5, 200, 300_000, 45_000, 7, 0.3),
    (7, 10, 1_000, 12_000, 7, 0.0), (2, 0, 0, 0, None, 1.0), (4, 500, 900_000, 90_000, 12, 0.5),
])
def test_vendored_formula_matches_its_documented_equation(level, a, t, pace, n, phi):
    assert math.isclose(fp.d_value(level, a, t, pace, n, phi), documented(level, a, t, pace, n, phi), rel_tol=1e-12)


def test_pace_tracker_returns_mean_tokens_per_cleared_level():
    pace = fp.FormPace()
    assert pace.cost_multiplier() == 0.0
    pace.record_completion(20_000, 123.0)
    pace.record_completion(40_000)
    assert pace.cost_multiplier() == 30_000


class _StubSession:
    def play(self):
        return "played"


class _StubSolver:
    """inference.framework.solver imports the whole TAAF runtime (imageio, arcengine, ...), which
    the test environment does not install. install_d() only wraps _HarnessGameSession.play, so a
    stand-in carries that; test_real_solver_still_has_the_hooks checks the real file, and the
    v8-cpucheck notebook runs install_d() on the real module on Kaggle."""
    _HarnessGameSession = _StubSession


def test_real_solver_still_has_the_hooks():
    src = (ROOT / "harness/ARC3-Inference/inference/framework/solver.py").read_text()
    assert "class _HarnessGameSession" in src and "    def play(self)" in src
    assert "gate.acquire(_PRIORITY_UNTRIMMED_BASE - self._queue_position())" in src


@pytest.fixture
def harness(monkeypatch):
    """Our real tool_agent (and a stand-in solver), restored after install_d() patches them."""
    import inference.agent.tool_agent as ta
    solver = _StubSolver

    for key in PRIORITY_KEYS:
        monkeypatch.setenv(key, os.environ.get(key, "0"))   # install_d writes these; restore after
    monkeypatch.setenv("ARC3_PRIORITY_TAIL_FADE", "0")
    saved = (ta.priority_value, ta.ProgressPace, ta._PriorityGate.acquire, solver._HarnessGameSession.play)
    yield ta, solver
    ta.priority_value, ta.ProgressPace, ta._PriorityGate.acquire, solver._HarnessGameSession.play = saved


def test_install_patches_our_harness(harness):
    ta, solver = harness
    line = fp.install_d(ta, solver)
    assert line.startswith("#OURS_FORM ok version=d_prime")
    assert ta.priority_value is fp.d_priority and ta.ProgressPace is fp.FormPace
    assert ta._PriorityGate.acquire._ours_d and solver._HarnessGameSession.play._ours_d
    assert _StubSession().play() == "played"                 # the wrapper still calls through
    assert os.environ["ARC3_PRIORITY_PACE"] == "1" and os.environ["ARC3_PRIORITY_TAIL_FADE_FRACTION"] == "0.4"
    fp.install_d(ta, solver)                                 # idempotent: no double wrapping
    assert ta._PriorityGate.acquire.__closure__ is not None


def _admission_order(ta, n_levels=7):
    """One slot, held by the main thread. A: a game on level 5 of 7, nothing spent there yet.
    B: a game that has not started. Release once; whoever is admitted first is recorded."""
    gate = ta._PriorityGate(1)
    now = time.monotonic()
    gate.configure_clock(now, now + 3600)                    # a run with an hour left: no tail fade yet
    gate.acquire(ta._PRIORITY_UNTRIMMED_BASE)                # occupant
    order = []

    def advanced():
        snap = ta.PrioritySnapshot(5, 0, 0.0, 0.0, n_levels)
        with gate._cond:
            gate._enqueue_and_wait(gate._snapshot_priority(snap, time.monotonic()), snap)
        order.append("advanced")

    def unstarted():
        gate.acquire(ta._PRIORITY_UNTRIMMED_BASE - 1)
        order.append("unstarted")

    threads = [threading.Thread(target=advanced), threading.Thread(target=unstarted)]
    for th in threads:
        th.start()
    deadline = time.monotonic() + 5
    while len(gate._waiting) < 2 and time.monotonic() < deadline:
        time.sleep(0.01)
    assert len(gate._waiting) == 2
    gate.release()
    while not order and time.monotonic() < deadline:
        time.sleep(0.01)
    gate.release()
    for th in threads:
        th.join(5)
    return order


def test_franzen_gate_admits_unstarted_games_first(harness, monkeypatch):
    ta, _ = harness
    monkeypatch.setenv("ARC3_PRIORITY_REFRESH_QUEUE", "1")
    assert _admission_order(ta) == ["unstarted", "advanced"]


def test_d_prime_gate_ranks_unstarted_games_by_the_formula(harness):
    ta, solver = harness
    fp.install_d(ta, solver)
    # unstarted: d_value(1,0,0,0,10) (no level count on this thread) = 17.96...;
    # advanced: d_value(5,0,0,0,7) = 19.89..., so it now wins the slot
    assert fp.d_value(5, 0, 0, 0, 7) > fp.d_value(1, 0, 0, 0, None)
    assert _admission_order(ta) == ["advanced", "unstarted"]
    assert fp.FRESH["replaced"] >= 1
