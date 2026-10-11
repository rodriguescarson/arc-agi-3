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


(WORKING_DIR / "git_status.txt").write_text((BUNDLE_DIR / "git_status.txt").read_text())
os.environ.setdefault("RECORDINGS_DIR", str(WORKING_DIR / "server_recording"))

soft_end = None
if TRUE_SUBMISSION:
    os.environ.setdefault("ARC_API_KEY", "test-key-123")
    os.environ.setdefault("ARC_BASE_URL", "http://gateway:8001/")
    _wait_for_gateway(os.environ["ARC_BASE_URL"])
    bm.games = _competition_games()
else:
    competition_env_files = "/kaggle/input/competitions/arc-prize-2026-arc-agi-3/environment_files"
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
    try:
        scores = {g.game_run.game_id: g.game_run.final_score for g in bm.games if g.game_run is not None}
        print("smoke scores:", json.dumps(scores, indent=1))
    except Exception as exc:
        print("could not summarise scores:", exc)
