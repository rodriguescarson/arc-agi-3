from pathlib import Path

import pytest

ENV_DIR = Path(__file__).resolve().parents[1] / "data" / "kaggle" / "environment_files"

pytestmark = pytest.mark.skipif(not ENV_DIR.exists(), reason="competition environment_files not downloaded")


def test_random_agent_plays_ls20():
    from arc3.local_eval import run

    summary = run("random", ["ls20"], max_actions=60, max_seconds=30, seed=0, env_dir=ENV_DIR, out=None)
    game = summary["games"][0]
    assert game["game_id"].startswith("ls20")
    assert game["total_actions"] == 60
    assert len(game["baselines"]) == 7
    assert 0.0 <= summary["score_competition_cap"] <= 100.0


def test_explorer_agent_plays_two_games():
    from arc3.local_eval import run

    summary = run("explorer", ["ls20", "vc33"], max_actions=80, max_seconds=30, seed=0, env_dir=ENV_DIR, out=None)
    assert len(summary["games"]) == 2
    for game in summary["games"]:
        assert game["total_actions"] <= 80


def test_explorer_click_candidates_prefer_small_interior_objects():
    import numpy as np

    from arc3.agents.explorer import click_candidates

    grid = np.zeros((64, 64), dtype=int)
    grid[30:33, 30:33] = 5     # a 3x3 button in the middle
    grid[0, :] = 7             # a HUD bar on the border
    picks = click_candidates(grid)
    assert picks[0] == (31, 31)
