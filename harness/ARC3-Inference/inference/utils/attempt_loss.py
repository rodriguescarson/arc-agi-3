"""Spotting an attempt restart the engine does not report (pure, stdlib only).

A game over is reported (state GAME_OVER) and the harness resets the level itself. Some games
lose an attempt without ending the game: ls20 has three lives, and when the step bar runs out
it puts the player back on the start cell, refills the bar and takes a pip off the life
counter, with the state still NOT_FINISHED. The engine hands back no life or attempt field,
so the only evidence is the board, and a snippet that planned a batch against the old board
keeps running it on the new one.

A restart looks like three things at once, none needing game knowledge:

* the board area (everything outside the HUD border) is exactly what the attempt started with;
* the HUD border has snapped back toward its starting state, at least ``ratio`` times closer
  than it was a moment ago: the step bar refilled (the lives pips differ from the start by a
  few cells, a spent bar by dozens);
* before that, the HUD had only moved AWAY from its start for ``min_run`` actions in a row,
  and had got at least ``min_spent`` cells away: a budget being spent one unit at a time.

The last two are what keep ordinary play out. Walking UP then DOWN brings the board area back
to its start, but a bar only shrinks inside an attempt, so the HUD moves further from its start
and never snaps back. Games whose border holds state rather than a budget (a selection, a
cursor, a toggle) revert whole boards legitimately, and their HUD wanders up and down, so the
run never builds; clicks on vc33 and lf52 and moves on ar25 did exactly that in real play until
the run was required. UNDO restores the earlier HUD with the board and is excluded by the
caller. A refill pickup changes the board area (the pickup is gone), so it fails the first
condition. A game with no HUD in the border gives no second signal and is never flagged.

``slack`` forgives small dips when counting the run. ls20 draws the glyph the player currently
holds in the HUD, so stepping on a changer moves the HUD distance by a few cells either way
while the bar keeps shrinking; without the slack 5% of real losses were missed.

Standalone on purpose: the solver imports it, and so does the test suite, which cannot import
the solver. No ``from __future__`` import and no non-stdlib import, like level_memory.py.
"""


def border_distance(grid_a, grid_b, border):
    """Number of cells that differ inside the border frame (the HUD area)."""
    rows = len(grid_a)
    cols = len(grid_a[0]) if rows else 0
    total = 0
    for r in range(rows):
        row_a, row_b = grid_a[r], grid_b[r]
        if r < border or r >= rows - border:
            total += sum(1 for x, y in zip(row_a, row_b, strict=False) if x != y)
        else:
            total += sum(1 for x, y in zip(row_a[:border], row_b[:border], strict=False) if x != y)
            total += sum(1 for x, y in zip(row_a[cols - border:], row_b[cols - border:], strict=False) if x != y)
    return total


def board_area_equal(grid_a, grid_b, border):
    """True when every cell outside the border frame is identical."""
    rows = len(grid_a)
    cols = len(grid_a[0]) if rows else 0
    for r in range(border, rows - border):
        if tuple(grid_a[r][border:cols - border]) != tuple(grid_b[r][border:cols - border]):
            return False
    return True


def _usable(border, *grids):
    """Same-shaped, non-empty grids that the border frame leaves a board area in."""
    if border <= 0 or not all(grids):
        return False
    rows, cols = len(grids[0]), len(grids[0][0])
    if any(len(g) != rows or len(g[0]) != cols for g in grids):
        return False
    return rows > 2 * border and cols > 2 * border


class AttemptTracker:
    """Per-game state for ``observe``: the start board of the current attempt, how far the HUD
    has moved from it, and for how many actions in a row it has only moved away.

    ``border`` is the HUD width, the same notion as ARC3_NOOP_GUARD_BORDER. The rest are the
    thresholds named in the module docstring: ``ratio`` (how many times closer to its start the
    HUD must snap), ``min_run`` (consecutive non-recovering actions before that), ``min_spent``
    (least HUD cells away from the start) and ``slack`` (a dip this small is not a recovery).
    The defaults found every one of 198 real ls20 losses in 250k replayed actions of the
    unmodified harness, 831 more under random play, and flagged nothing in the other 24 games.
    """

    def __init__(self, border=4, ratio=8, min_run=16, min_spent=32, slack=4):
        self.border = border
        self.ratio = ratio
        self.min_run = min_run
        self.min_spent = min_spent
        self.slack = slack
        self.start = None
        self.hud = 0
        self.run = 0

    def begin(self, grid):
        """A new attempt starts on this board: after a RESET, a level load or a restart."""
        self.start = grid
        self.hud = 0
        self.run = 0

    def observe(self, previous_grid, new_grid, undo=False):
        """Account for one executed action; True when it restarted the attempt.

        Fails closed: unusable grids, a shape change or a border of 0 never report a restart.
        """
        if self.start is None:
            self.begin(previous_grid)
        if not _usable(self.border, self.start, previous_grid, new_grid):
            self.begin(new_grid)
            return False
        spent = self.hud
        run = self.run
        self.hud = border_distance(new_grid, self.start, self.border)
        # a budget is only ever spent inside an attempt; anything that wins HUD cells back
        # (an undo, a toggle, a refill pickup) starts the count again
        self.run = run + 1 if self.hud + self.slack >= spent else 0
        if undo or run < self.min_run or spent < self.min_spent:
            return False
        if self.hud >= spent or self.hud * self.ratio > spent:
            return False
        if not board_area_equal(new_grid, self.start, self.border):
            return False
        self.begin(new_grid)
        return True
