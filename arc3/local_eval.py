"""Play the public ARC-AGI-3 games offline with a CPU agent and score them.

    .venv/bin/python -m arc3.local_eval --agent explorer --games ls20,vc33 --max-actions 300
    .venv/bin/python -m arc3.local_eval --agent random --all --out data/runs/random.json

Scores are reported with the competition cap (1.0) and the local cap (1.15) side by side.
Baselines come from the public games' metadata.json (hidden in the real competition).
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from arc3.rhae import COMPETITION_CAP, LOCAL_CAP, GameResult, benchmark_score

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_DIR = ROOT / "data" / "kaggle" / "environment_files"


def make_arcade(env_dir: Path):
    os.environ["ENVIRONMENTS_DIR"] = str(env_dir)
    import arc_agi
    from arc_agi import OperationMode

    return arc_agi.Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=str(env_dir))


def play_game(arcade, game_id: str, agent, max_actions: int, max_seconds: float) -> GameResult:
    from arcengine import GameState

    env = arcade.make(game_id)
    if env is None:
        raise RuntimeError(f"could not create env {game_id}")
    info = env.environment_info
    baselines = list(getattr(info, "baseline_actions", None) or [])
    frame = env.observation_space
    agent.reset(game_id, list(frame.available_actions or []))
    actions_per_level: dict[int, int] = {}
    t0 = time.monotonic()
    total = 0
    resets = 0
    state = frame.state
    while total < max_actions and (time.monotonic() - t0) < max_seconds:
        if state is GameState.WIN:
            break
        action, data = agent.act(frame)
        level = frame.levels_completed
        frame = env.step(action, data=data or {})
        total += 1
        if action.name == "RESET":
            resets += 1
        actions_per_level[level] = actions_per_level.get(level, 0) + 1
        state = frame.state
        if getattr(agent, "gave_up", False):
            break
    n_levels = frame.win_levels or len(baselines)
    per_level = [actions_per_level.get(i, 0) for i in range(n_levels)]
    return GameResult(
        game_id=game_id,
        levels_completed=int(frame.levels_completed),
        actions_per_level=per_level,
        baselines=baselines[:n_levels] if baselines else [],
        total_actions=total,
        resets=resets,
        state=str(frame.state.name if hasattr(frame.state, "name") else frame.state),
        seconds=time.monotonic() - t0,
    )


def run(agent_name: str, games: list[str] | None, max_actions: int, max_seconds: float, seed: int, env_dir: Path, out: Path | None) -> dict:
    from arc3.agents import AGENTS

    arcade = make_arcade(env_dir)
    available = [e.game_id for e in arcade.get_environments()]
    if games:
        wanted = {g.split("-")[0] for g in games}
        selected = [g for g in available if g.split("-")[0] in wanted]
        missing = wanted - {g.split("-")[0] for g in selected}
        if missing:
            raise SystemExit(f"unknown games: {sorted(missing)}")
    else:
        selected = available
    results: list[GameResult] = []
    for game_id in selected:
        agent = AGENTS[agent_name](seed=seed) if agent_name == "random" else AGENTS[agent_name](seed=seed)
        result = play_game(arcade, game_id, agent, max_actions, max_seconds)
        results.append(result)
        print(
            f"{game_id:16} levels {result.levels_completed}/{result.n_levels}  actions {result.total_actions:5d}"
            f"  score {100 * result.score(COMPETITION_CAP):6.2f}  ({result.seconds:.1f}s)",
            flush=True,
        )
    summary = {
        "agent": agent_name,
        "seed": seed,
        "max_actions": max_actions,
        "games": [r.__dict__ for r in results],
        "score_competition_cap": benchmark_score(results, COMPETITION_CAP),
        "score_local_cap": benchmark_score(results, LOCAL_CAP),
        "levels_completed": sum(r.levels_completed for r in results),
        "levels_total": sum(r.n_levels for r in results),
    }
    print(
        f"\n{agent_name}: {summary['levels_completed']}/{summary['levels_total']} levels, "
        f"score {summary['score_competition_cap']:.3f} (cap 1.0) / {summary['score_local_cap']:.3f} (cap 1.15) over {len(results)} games"
    )
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=1, default=str))
        print("wrote", out)
    return summary


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agent", default="explorer", choices=["random", "explorer"])
    ap.add_argument("--games", default="", help="comma-separated short ids, e.g. ls20,vc33")
    ap.add_argument("--all", action="store_true", help="all 25 public games")
    ap.add_argument("--max-actions", type=int, default=300)
    ap.add_argument("--max-seconds", type=float, default=120.0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--env-dir", type=Path, default=DEFAULT_ENV_DIR)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()
    games = [g.strip() for g in args.games.split(",") if g.strip()] if args.games else None
    if not games and not args.all:
        games = ["ls20", "vc33"]
    run(args.agent, games, args.max_actions, args.max_seconds, args.seed, args.env_dir, args.out)


if __name__ == "__main__":
    main()
