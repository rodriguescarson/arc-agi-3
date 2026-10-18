# Run shape.  Adapted from Daniel Franzen's Milestone 2 notebook (Apache-2.0).
# Competition rerun: identical to upstream unless the variant config overrides it.
# Interactive commit: a short smoke run on a few public games so the commit succeeds in
# well under an hour of GPU quota.  Score-bearing settings live in the variant JSON.
SOLVER = __SOLVER__
# e.g. {"max_runtime_minutes": 532, "concurrency": 120, "analyzer_timeout": 900.0}

bm.solver.analyzer_timeout = float(SOLVER.get("analyzer_timeout", 900.0))
bm.solver.max_actions_per_game = None
bm.solver.save_request_logs = False
bm.game_weights = None

if TRUE_SUBMISSION:
    bm.n_passes = 1
    if USE_PRIORITY_SCHEDULING:
        # every game starts at once; the priority gate admits 10 streams at a time
        bm.solver.concurrency = int(SOLVER.get("concurrency", 120))
        bm.solver.max_runtime_s_per_game = float(SOLVER.get("max_runtime_minutes", 532)) * 60
    else:
        bm.solver.concurrency = int(SOLVER.get("concurrency", 10))
        bm.solver.max_runtime_s_per_game = float(SOLVER.get("max_runtime_minutes", 48)) * 60
else:
    bm.n_passes = int(SMOKE.get("passes", 1))
    smoke_games = SMOKE.get("games") or []
    bm.solver.concurrency = max(1, len(smoke_games) * bm.n_passes) if smoke_games else 10
    bm.solver.max_runtime_s_per_game = float(SMOKE.get("minutes_per_game", 20)) * 60
    bm.solver.save_request_logs = bool(SMOKE.get("save_request_logs", True))
    budget = float(getattr(target, "max_runtime_s", 0.0) or 0.0)
    if budget != 32400.0:
        print(f"note: deploy target budget is {budget!r}, not 32400; continuing with the smoke budget")

# D' slot priority (shiiin9, Apache-2.0; inference/agent/form_priority.py). Variants opt in with
# ARC3_PRIORITY_FORM=d_prime. Installed in the commit and in the competition rerun alike; the
# installer raises if the harness no longer has the names it patches, so a mismatch fails the
# commit instead of silently running Franzen's priority.
PRIORITY_FORM = os.environ.get("ARC3_PRIORITY_FORM", "").strip().lower()
if PRIORITY_FORM == "d_prime":
    import inference.agent.form_priority as _form_priority
    import inference.agent.tool_agent as _fp_tool_agent
    import inference.framework.solver as _fp_solver
    _form_priority.install_d(_fp_tool_agent, _fp_solver)
elif PRIORITY_FORM:
    raise ValueError(f"unknown ARC3_PRIORITY_FORM {PRIORITY_FORM!r}")

if CPU_SMOKE:
    import taaf.solver_examples

    # The random solver never touches the LLM agent, so prove here that the bundled agent
    # imports on this image and that the drain-memory helpers run (no GPU, no model).
    import inference.agent.tool_agent as _agent
    _note = _agent._pinned_memory_text(
        [{"level": 1, "winning_actions": ["ACTION1"], "n_actions": 1, "attempts": 1, "total_actions": 1}],
        ["def f(x):\n    return x\n"], 4500)
    assert _note.startswith(_agent._PINNED_MEMORY_HEADER) and "def f(x)" in _note
    if PRIORITY_FORM == "d_prime":
        # the CPU run never reaches the gate, so prove here that the patched pieces are live
        assert _fp_tool_agent.priority_value is _form_priority.d_priority
        assert _fp_tool_agent.ProgressPace is _form_priority.FormPace
        assert getattr(_fp_tool_agent._PriorityGate.acquire, "_ours_d", False)
        assert getattr(_fp_solver._HarnessGameSession.play, "_ours_d", False)
        print("cpu smoke: D' priority installed:", _form_priority.d_value(1, 0, 0, 0, 7))
    print("cpu smoke: bundled agent imports; drain-memory note OK;",
          "reasoning-effort knob present:", hasattr(_agent, "_reasoning_effort_default"))

    bm.solver = taaf.solver_examples.SolverRandom(
        label="cpu-smoke-random", max_actions_per_game=int(SMOKE.get("cpu_actions", 60)), seed=0
    )
    bm.n_passes = 1

print("benchmark.solver:", bm.solver)
print("passes:", bm.n_passes, "| smoke:", None if TRUE_SUBMISSION else SMOKE)
