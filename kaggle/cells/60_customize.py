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

if CPU_SMOKE:
    import taaf.solver_examples

    # The random solver never touches the LLM agent, so prove here that the bundled agent
    # imports on this image and that the drain-memory helpers run (no GPU, no model).
    import inference.agent.tool_agent as _agent
    _note = _agent._pinned_memory_text(
        [{"level": 1, "winning_actions": ["ACTION1"], "n_actions": 1, "attempts": 1, "total_actions": 1}],
        ["def f(x):\n    return x\n"], 4500)
    assert _note.startswith(_agent._PINNED_MEMORY_HEADER) and "def f(x)" in _note
    print("cpu smoke: bundled agent imports; drain-memory note OK;",
          "reasoning-effort knob present:", hasattr(_agent, "_reasoning_effort_default"))

    bm.solver = taaf.solver_examples.SolverRandom(
        label="cpu-smoke-random", max_actions_per_game=int(SMOKE.get("cpu_actions", 60)), seed=0
    )
    bm.n_passes = 1

print("benchmark.solver:", bm.solver)
print("passes:", bm.n_passes, "| smoke:", None if TRUE_SUBMISSION else SMOKE)
