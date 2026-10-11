from arc3.rhae import GameResult, benchmark_score, game_score, level_score


def test_level_score_caps_and_squares():
    assert level_score(10, 20) == 0.25
    assert level_score(10, 10) == 1.0
    assert level_score(10, 5) == 1.0            # competition cap
    assert level_score(10, 5, cap=1.15) == 1.15  # local cap
    assert level_score(10, 0) == 0.0


def test_game_score_is_level_weighted():
    # 5 levels, first 4 solved at exactly the baseline: 10/15 of the weight
    s = game_score(4, [10, 10, 10, 10, 0], [10, 10, 10, 10, 10])
    assert abs(s - 10 / 15) < 1e-9
    # unsolved everything
    assert game_score(0, [], [10, 10]) == 0.0
    # inefficient level 1 only: weight 1/3 * 0.25
    assert abs(game_score(1, [20], [10, 10]) - (1 / 3) * 0.25) < 1e-9


def test_benchmark_mean_in_percent():
    a = GameResult("a", 2, [10, 10], [10, 10])
    b = GameResult("b", 0, [0, 0], [10, 10])
    assert abs(benchmark_score([a, b]) - 50.0) < 1e-9
