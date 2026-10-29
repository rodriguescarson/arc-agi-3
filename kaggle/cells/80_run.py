# Play.  Adapted from Daniel Franzen's Milestone 2 notebook (Apache-2.0).
# Competition rerun: wait for the Kaggle gateway and play the live competition Arcade.
# Interactive commit: play a few of the competition's bundled public environments offline
# for a bounded time, then write a dummy submission.parquet so the commit succeeds.
print("Starting benchmark...")


def _competition_games():
    import arc_agi
    import taaf.game_api

    spec = taaf.game_api.ArcadeSpec(
        operation_mode=arc_agi.OperationMode.COMPETITION,
        arc_base_url=os.environ["ARC_BASE_URL"],
        environments_dir="",
    )
    arcade = arc_agi.Arcade(
        operation_mode=arc_agi.OperationMode.COMPETITION,
        arc_base_url=spec.arc_base_url,
        environments_dir="",
    )
    game_ids = [env_info.game_id for env_info in arcade.available_environments]
    if not game_ids:
        raise RuntimeError("Competition Arcade exposed zero environments.")
    print(f"competition arcade: {len(game_ids)} games")
    return [taaf.game_api.GameAPI(env_name=game_id, arcade_spec=spec) for game_id in game_ids]


def _offline_games(env_dir: str, only: list | None):
    import arc_agi
    import taaf.game_api

    spec = taaf.game_api.ArcadeSpec(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=env_dir)
    arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir=env_dir)
    game_ids = [env_info.game_id for env_info in arcade.available_environments]
    if not game_ids:
        raise RuntimeError(f"No offline environments found under {env_dir}.")
    if only:
        wanted = {g.split("-")[0] for g in only}
        game_ids = [g for g in game_ids if g.split("-")[0] in wanted]
    print(f"offline games: {game_ids}")
    return [taaf.game_api.GameAPI(env_name=game_id, arcade_spec=spec) for game_id in game_ids]


def _wait_for_gateway(base_url: str, timeout_s: float = 600.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}api/games", timeout=10) as response:
                if response.status < 500:
                    return
        except Exception as exc:
            last_error = repr(exc)
        time.sleep(5)
    raise RuntimeError(f"Kaggle gateway did not become ready: {last_error}")


def _startup_hardening() -> bool:
    return os.environ.get("ARC3_STARTUP_HARDENING", "0").strip().lower() in {"1", "true", "yes", "on"}


def _gateway_wait_seconds() -> float:
    """The gateway and the game list share this budget: 600 s as upstream, an hour with start-up
    hardening (the platform has been slow to bring things up since 2026-10-21)."""
    return 3600.0 if _startup_hardening() else 600.0


def _competition_games_when_ready(deadline: float):
    """arc_agi.Arcade logs and swallows a failed /api/games fetch, so a gateway that answered the
    wait above but then hiccuped surfaces here as "zero environments" and would end the notebook."""
    delay = 5.0
    while True:
        try:
            return _competition_games()
        except Exception as exc:
            if time.monotonic() + delay > deadline:
                raise
            print(f"competition game list not ready ({exc!r}); retrying in {delay:.0f}s", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, 60.0)


(WORKING_DIR / "git_status.txt").write_text((BUNDLE_DIR / "git_status.txt").read_text())
os.environ.setdefault("RECORDINGS_DIR", str(WORKING_DIR / "server_recording"))

soft_end = None
if TRUE_SUBMISSION:
    os.environ.setdefault("ARC_API_KEY", "test-key-123")
    os.environ.setdefault("ARC_BASE_URL", "http://gateway:8001/")
    _gateway_deadline = time.monotonic() + _gateway_wait_seconds()
    _wait_for_gateway(os.environ["ARC_BASE_URL"], _gateway_wait_seconds())
    bm.games = _competition_games_when_ready(_gateway_deadline) if _startup_hardening() else _competition_games()
    if _startup_hardening():
        # The per-game limit counts from game start, so a long gateway wait above would push
        # play past Kaggle's 9 h wall and the scorecard would never close. Keep 4 minutes for
        # teardown and clamp the limit to the notebook's real remaining time.
        _left = 32400.0 - (time.time() - NOTEBOOK_START_TIME) - 240.0
        if _left < bm.solver.max_runtime_s_per_game:
            print(f"clamping max_runtime_s_per_game {bm.solver.max_runtime_s_per_game:.0f}s -> {_left:.0f}s "
                  "(late gateway)", flush=True)
            bm.solver.max_runtime_s_per_game = max(600.0, _left)
else:
    competition_env_files = str(COMPETITION_DIR / "environment_files")
    bm.games = _offline_games(competition_env_files, SMOKE.get("games"))
    total = float(SMOKE.get("total_minutes", 40)) * 60
    soft_end = datetime.fromtimestamp(NOTEBOOK_START_EPOCH) + timedelta(seconds=total)
    print(f"smoke soft end: {soft_end.isoformat()} ({total/60:.0f} min after notebook start)")

await bm.run(soft_end_time=soft_end, runtime_environment=target, minimal_diagnostics=TRUE_SUBMISSION)

if not TRUE_SUBMISSION:
    import pandas as pd

    pd.DataFrame(
        [["1_0", "1", True, 1]],
        columns=["row_id", "game_id", "end_of_game", "score"],
    ).to_parquet(WORKING_DIR / "submission.parquet", index=False)
    def _run_scores(game_runs, live_score, count_actions):
        """One row per played run.  `bm.games` are the templates (their game_run stays None);
        the runs live in `bm.game_runs`, and a smoke run cut at the soft end has no final_score,
        so score the live state the way summary.txt does."""
        return [{"game_id": r.game_id, "score": round(float(live_score(r)), 4), "state": r.state,
                 "levels": r.levels_completed, "actions": count_actions(r)} for r in game_runs]

    scores = []
    try:
        import taaf.diagnostics as _diag
        scores = _run_scores(bm.game_runs, _diag._live_score, _diag._count_actions)
        print("smoke scores:", json.dumps(scores, indent=1))
    except Exception as exc:
        print("could not summarise scores:", exc)
    # Commit telemetry: the scored rerun's logs are never visible, so this commit is the only
    # place to check that a mechanism fired (which model served, tokens per request, speed).
    telemetry = {"variant": VARIANT, "smoke_scores": scores,
                 "served_model": (WORKING_DIR / "served_model.txt").read_text().strip() if (WORKING_DIR / "served_model.txt").exists() else None,
                 "elapsed_s": round(time.time() - NOTEBOOK_START_TIME)}
    try:
        with urlopen(f"http://127.0.0.1:{SERVED_MODEL_PORT}/metrics", timeout=10) as r:
            raw = r.read().decode(errors="replace")
        metrics = {}
        for line in raw.splitlines():
            if line.startswith("sglang:") and " " in line:
                name, _, value = line.rpartition(" ")
                key = name.split("{")[0]
                if key.endswith(("_total", "_sum", "_count")) or "throughput" in key or "accept" in key or "hit_rate" in key:
                    try:
                        metrics[key] = metrics.get(key, 0.0) + float(value)
                    except ValueError:
                        pass
        telemetry["metrics"] = metrics
        gen = next((v for k, v in metrics.items() if "generation_tokens_total" in k), None)
        reqs = next((v for k, v in metrics.items() if k.endswith("num_requests_total") or k.endswith("request_count")), None)
        if gen and reqs:
            telemetry["generated_tokens_per_request"] = round(gen / reqs, 1)
    except Exception as exc:
        telemetry["metrics_error"] = repr(exc)
    (WORKING_DIR / "telemetry.json").write_text(json.dumps(telemetry, indent=1))
    print("telemetry:", json.dumps({k: v for k, v in telemetry.items() if k != "metrics"}, indent=1))
