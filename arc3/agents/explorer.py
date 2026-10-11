"""A deterministic, model-free explorer.

It is not meant to score: beyond ~5x the human baseline a level is worth nothing, and a blind
search spends that quickly.  It exists so that (1) every game sees at least one real action
even if the model server never comes up, and (2) there is a cheap, reproducible baseline to
compare harness changes against on the public games.

Policy per state (state = hash of the 64x64 grid):
- keyboard actions in a fixed order, skipping ones already observed to change nothing here;
- click targets ranked by "button-likeness": small, rare-coloured connected components first,
  each clicked at most once per state;
- after a game over, RESET; after `max_actions_per_level` actions on one level, give up.
"""
from __future__ import annotations

import hashlib
from collections import deque

import numpy as np
from arcengine import GameAction, GameState

KEY_ORDER = (GameAction.ACTION1, GameAction.ACTION2, GameAction.ACTION3, GameAction.ACTION4, GameAction.ACTION5)


def grid_hash(grid: np.ndarray) -> str:
    return hashlib.blake2b(np.ascontiguousarray(grid, dtype=np.uint8).tobytes(), digest_size=8).hexdigest()


def components(grid: np.ndarray) -> list[dict]:
    """4-connected same-colour components with centre, size and colour."""
    h, w = grid.shape
    seen = np.zeros((h, w), dtype=bool)
    out: list[dict] = []
    for r0 in range(h):
        for c0 in range(w):
            if seen[r0, c0]:
                continue
            colour = int(grid[r0, c0])
            cells = []
            q = deque([(r0, c0)])
            seen[r0, c0] = True
            while q:
                r, c = q.popleft()
                cells.append((r, c))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < h and 0 <= cc < w and not seen[rr, cc] and grid[rr, cc] == colour:
                        seen[rr, cc] = True
                        q.append((rr, cc))
            rs = [p[0] for p in cells]
            cs = [p[1] for p in cells]
            out.append({
                "colour": colour,
                "size": len(cells),
                "row": int(round(sum(rs) / len(rs))),
                "col": int(round(sum(cs) / len(cs))),
                "bbox": (min(rs), min(cs), max(rs), max(cs)),
            })
    return out


def click_candidates(grid: np.ndarray, limit: int = 24) -> list[tuple[int, int]]:
    comps = components(grid)
    if not comps:
        return []
    colour_counts: dict[int, int] = {}
    for comp in comps:
        colour_counts[comp["colour"]] = colour_counts.get(comp["colour"], 0) + comp["size"]
    total = grid.size

    def rank(comp: dict) -> tuple:
        area_share = colour_counts[comp["colour"]] / total
        r0, c0, r1, c1 = comp["bbox"]
        touches_border = r0 == 0 or c0 == 0 or r1 == grid.shape[0] - 1 or c1 == grid.shape[1] - 1
        # small, rare colour, interior first; huge background regions last
        return (touches_border, area_share > 0.5, abs(comp["size"] - 6), area_share)

    ordered = sorted((c for c in comps if 1 <= c["size"] <= 200), key=rank)
    seen = set()
    picks = []
    for comp in ordered:
        key = (comp["row"], comp["col"])
        if key in seen:
            continue
        seen.add(key)
        picks.append(key)
        if len(picks) >= limit:
            break
    return picks


class ExplorerAgent:
    def __init__(self, max_actions_per_level: int = 120, seed: int = 0) -> None:
        self.max_actions_per_level = max_actions_per_level
        self.seed = seed
        self.reset("", [])

    def reset(self, game_id: str, available_actions: list[int]) -> None:
        self.game_id = game_id
        self.available = [GameAction.from_id(a) for a in available_actions if a != GameAction.RESET.value]
        self.tried: dict[str, set] = {}
        self.noop: dict[str, set] = {}
        self.level = -1
        self.level_actions = 0
        self.last: tuple[str, object] | None = None
        self.gave_up = False

    def _observe_transition(self, frame) -> None:
        if self.last is None:
            return
        prev_hash, key = self.last
        grid = np.asarray(frame.frame[-1])
        if grid_hash(grid) == prev_hash:
            self.noop.setdefault(prev_hash, set()).add(key)
        self.last = None

    def act(self, frame):
        if frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            self.last = None
            return GameAction.RESET, None
        if frame.levels_completed != self.level:
            self.level = frame.levels_completed
            self.level_actions = 0
            self.gave_up = False
        self._observe_transition(frame)
        grid = np.asarray(frame.frame[-1])
        state = grid_hash(grid)
        tried = self.tried.setdefault(state, set())
        noop = self.noop.get(state, set())
        actions = [GameAction.from_id(a) for a in frame.available_actions if a != GameAction.RESET.value] or self.available
        if self.level_actions >= self.max_actions_per_level:
            self.gave_up = True
        self.level_actions += 1

        for action in KEY_ORDER:
            if action in actions and action.name not in tried and action.name not in noop:
                tried.add(action.name)
                self.last = (state, action.name)
                return action, None
        if GameAction.ACTION6 in actions:
            for row, col in click_candidates(grid):
                key = ("click", row, col)
                if key not in tried and key not in noop:
                    tried.add(key)
                    self.last = (state, key)
                    return GameAction.ACTION6, {"x": col, "y": row}
        # everything tried in this state: cycle keys in order so the walk continues
        keys = [a for a in KEY_ORDER if a in actions]
        if keys:
            action = keys[self.level_actions % len(keys)]
            self.last = (state, action.name)
            return action, None
        rnd = (self.level_actions * 7919 + self.seed) % 4096
        self.last = (state, ("click", rnd // 64, rnd % 64))
        return GameAction.ACTION6, {"x": rnd % 64, "y": rnd // 64}
