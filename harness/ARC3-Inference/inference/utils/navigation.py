"""Shortest-path movement for the piece the agent controls (pure, sandbox-injectable).

The model can already move a piece one key at a time, but every turn it spends steering costs
wall clock, and every detour costs actions, which the score squares.  This module learns the
controls from moves already played on the current level, plans a shortest path with BFS and
executes it one verified step at a time:

* the controlled piece is the same-colour, same-shape component that translated rigidly most
  consistently under UP/DOWN/LEFT/RIGHT;
* a key's effect is its most common displacement; an unobserved key is inferred as the
  opposite of its partner and marked as inferred;
* a destination is open when every cell of the piece lands on its own pixels, on a colour it
  has already moved onto, or on the target; positions where a key changed nothing, or where
  a move ended the attempt, are avoided;
* execution stops at the target, at the first step that does not land where predicted, at a
  harness refusal, or when the level or attempt ends.

It needs no undo, which only 4 of the 25 public games offer.

This file is injected verbatim into the sandbox bootstrap (see python_tool_sandbox.py), so it
must not import anything outside the standard library and must not carry a
``from __future__`` import: spliced mid-file, that line is a SyntaxError that kills every
sandbox call (it did, on 2026-10-17).
"""

import collections

NAV_KEYS = ("UP", "DOWN", "LEFT", "RIGHT")
_NAV_ALIASES = {"ACTION1": "UP", "ACTION2": "DOWN", "ACTION3": "LEFT", "ACTION4": "RIGHT"}
_NAV_OPPOSITE = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
_NAV_STOP_FLAGS = ("level_completed", "game_over", "run_complete", "done")


def nav_key(action_text):
    """UP/DOWN/LEFT/RIGHT for a history action string (engine or model names), else None."""
    text = str(action_text or "").strip().upper()
    head = text.split("(")[0].split()[0] if text else ""
    head = _NAV_ALIASES.get(head, head)
    return head if head in NAV_KEYS else None


def _nav_grid(frame):
    if frame is None:
        return None
    grid = getattr(frame, "_grid", None)
    if grid is None:
        grid = getattr(frame, "grid", None)
    return grid


def _nav_level(frame):
    try:
        return int(getattr(frame, "level", 0) or 0)
    except (TypeError, ValueError):
        return 0


def nav_components(grid, cells_of_interest=None, max_size=400):
    """4-connected same-colour components as (colour, sorted cell tuple).

    With ``cells_of_interest``, only components containing one of those cells are returned.
    Components larger than ``max_size`` (floors, walls, backgrounds) are skipped.
    """
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    seen = set()
    out = []
    starts = cells_of_interest if cells_of_interest is not None else (
        (r, c) for r in range(rows) for c in range(cols))
    for start in starts:
        if start in seen:
            continue
        r0, c0 = start
        if not (0 <= r0 < rows and 0 <= c0 < cols):
            continue
        colour = grid[r0][c0]
        stack = [start]
        seen.add(start)
        cells = []
        too_big = False
        while stack:
            r, c = stack.pop()
            cells.append((r, c))
            if len(cells) > max_size:
                too_big = True
            for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in seen \
                        and grid[nr][nc] == colour:
                    seen.add((nr, nc))
                    stack.append((nr, nc))
        if not too_big:
            out.append((colour, tuple(sorted(cells))))
    return out


def _nav_shape(cells):
    r0 = min(r for r, _ in cells)
    c0 = min(c for _, c in cells)
    return tuple(sorted((r - r0, c - c0) for r, c in cells)), (r0, c0)


def nav_moves(before, after, max_size=400):
    """Components that translated rigidly between two same-shaped grids.

    Returns (colour, shape, (dr, dc), origin_before, origin_after) tuples, matching each
    changed component in ``before`` with the nearest same-colour, same-shape component in
    ``after`` at a different origin.
    """
    if not before or not after or len(before) != len(after) or len(before[0]) != len(after[0]):
        return []
    changed = [(r, c) for r, (ra, rb) in enumerate(zip(before, after, strict=True)) if ra != rb
               for c, (va, vb) in enumerate(zip(ra, rb, strict=True)) if va != vb]
    if not changed:
        return []
    after_index = {}
    for colour, cells in nav_components(after, changed, max_size):
        shape, origin = _nav_shape(cells)
        after_index.setdefault((colour, shape), []).append(origin)
    moves = []
    for colour, cells in nav_components(before, changed, max_size):
        shape, origin = _nav_shape(cells)
        targets = [o for o in after_index.get((colour, shape), []) if o != origin]
        if not targets:
            continue
        best = min(targets, key=lambda o: abs(o[0] - origin[0]) + abs(o[1] - origin[1]))
        moves.append((colour, shape, (best[0] - origin[0], best[1] - origin[1]), origin, best))
    return moves


def learn_controls(transitions, level=None, max_size=400):
    """What UP/DOWN/LEFT/RIGHT do to the controlled piece on ``level``.

    Returns a dict with ``colour``, ``shape``, ``controls`` {key: (dr, dc)}, ``inferred``
    (keys guessed from their opposite), ``passable`` (colours the piece has moved onto),
    ``blocked`` {(origin, key)}, ``deadly`` {origin}, ``last_origin``, or None when no
    rigid move has been observed yet.
    """
    votes = {}
    steps = []
    for t in transitions or []:
        key = nav_key(getattr(t, "action", ""))
        if key is None:
            continue
        bf = getattr(t, "before_frame", None)
        af = getattr(t, "after_frame", None)
        before, after = _nav_grid(bf), _nav_grid(af)
        if before is None or after is None:
            continue
        if level is not None and _nav_level(bf) != level:
            continue
        result = getattr(t, "result", None) or {}
        moves = nav_moves(before, after, max_size)
        steps.append((key, before, after, result, moves, _nav_level(af)))
        for colour, shape, d, _o1, _o2 in moves:
            votes.setdefault((colour, shape), {}).setdefault(key, []).append(d)
    if not votes:
        return None
    sprite = max(votes, key=lambda k: (len(votes[k]), sum(len(v) for v in votes[k].values()),
                                       -len(k[1])))
    colour, shape = sprite
    controls = {}
    for key, ds in votes[sprite].items():
        controls[key] = collections.Counter(ds).most_common(1)[0][0]
    inferred = []
    for key in NAV_KEYS:
        partner = _NAV_OPPOSITE[key]
        if key not in controls and partner in controls:
            dr, dc = controls[partner]
            controls[key] = (-dr, -dc)
            inferred.append(key)
    passable = set()
    blocked = set()
    deadly = set()
    last_origin = None
    for key, before, after, result, moves, after_level in steps:
        mine = [m for m in moves if m[0] == colour and m[1] == shape]
        if mine:
            _, _, d, o1, o2 = mine[0]
            last_origin = o2
            old = {(o1[0] + r, o1[1] + c) for r, c in shape}
            for r, c in shape:
                cell = (o2[0] + r, o2[1] + c)
                if cell not in old:
                    passable.add(before[cell[0]][cell[1]])
            continue
        origins = [_nav_shape(cells)[1] for col, cells in nav_components(before, None, max_size)
                   if col == colour and _nav_shape(cells)[0] == shape]
        if len(origins) != 1:
            continue
        origin = origins[0]
        if result.get("game_over"):
            if key in controls:
                dr, dc = controls[key]
                deadly.add((origin[0] + dr, origin[1] + dc))
        elif level is None or after_level == level:
            still = [_nav_shape(cells)[1] for col, cells in nav_components(after, None, max_size)
                     if col == colour and _nav_shape(cells)[0] == shape]
            if origin in still:
                blocked.add((origin, key))
    return {"colour": colour, "shape": shape, "controls": controls, "inferred": inferred,
            "passable": passable, "blocked": blocked, "deadly": deadly,
            "last_origin": last_origin}


def locate_piece(grid, model, max_size=400):
    """Origin (row, col) of the controlled piece in ``grid``, or None."""
    origins = [_nav_shape(cells)[1] for col, cells in nav_components(grid, None, max_size)
               if col == model["colour"] and _nav_shape(cells)[0] == model["shape"]]
    if not origins:
        return None
    anchor = model.get("last_origin")
    if anchor is None or len(origins) == 1:
        return origins[0]
    return min(origins, key=lambda o: abs(o[0] - anchor[0]) + abs(o[1] - anchor[1]))


def _nav_target_cells(grid, target, own):
    if isinstance(target, int) and not isinstance(target, bool):
        return {(r, c) for r, row in enumerate(grid) for c, v in enumerate(row)
                if v == target and (r, c) not in own}
    if isinstance(target, (list, tuple, set)) and target and isinstance(next(iter(target)), (list, tuple)):
        return {(int(r), int(c)) for r, c in target}
    if isinstance(target, (list, tuple)) and len(target) == 2:
        return {(int(target[0]), int(target[1]))}
    raise ValueError("target must be a (row, col) cell, a list of cells, or a colour number")


def plan_path(grid, model, start, target, adjacent=False, max_nodes=20000):
    """BFS over piece origins. Returns the key list (possibly empty), or None if unreachable."""
    rows = len(grid)
    cols = len(grid[0]) if rows else 0
    shape = model["shape"]
    own = {(start[0] + r, start[1] + c) for r, c in shape}
    goal_cells = _nav_target_cells(grid, target, own)
    if not goal_cells:
        return None
    if adjacent:
        goal_cells = {(r + dr, c + dc) for r, c in goal_cells
                      for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))} | goal_cells
    passable = model["passable"]

    def reached(origin):
        return any((origin[0] + r, origin[1] + c) in goal_cells for r, c in shape)

    def open_at(origin):
        for r, c in shape:
            rr, cc = origin[0] + r, origin[1] + c
            if not (0 <= rr < rows and 0 <= cc < cols):
                return False
            if (rr, cc) in own or (rr, cc) in goal_cells or grid[rr][cc] in passable:
                continue
            return False
        return True

    if reached(start):
        return []
    parent = {start: None}
    queue = collections.deque([start])
    while queue and len(parent) < max_nodes:
        here = queue.popleft()
        for key in NAV_KEYS:
            d = model["controls"].get(key)
            if d is None or d == (0, 0) or (here, key) in model["blocked"]:
                continue
            nxt = (here[0] + d[0], here[1] + d[1])
            if nxt in parent or nxt in model["deadly"] or not open_at(nxt):
                continue
            parent[nxt] = (here, key)
            if reached(nxt):
                path = []
                node = nxt
                while parent[node] is not None:
                    node, key_taken = parent[node]
                    path.append(key_taken)
                return path[::-1]
            queue.append(nxt)
    return None


def describe_movement(frame, transitions):
    """Summary of the learned controls for the current level (no actions spent)."""
    grid = _nav_grid(frame)
    model = learn_controls(transitions, _nav_level(frame))
    if model is None or grid is None:
        return {"status": "no_moves_observed",
                "note": "press UP/DOWN/LEFT/RIGHT at least once on this level first"}
    return {"status": "ok", "colour": model["colour"], "piece_cells": len(model["shape"]),
            "at": locate_piece(grid, model),
            "controls": {k: list(v) for k, v in sorted(model["controls"].items())},
            "inferred": model["inferred"], "passable_colours": sorted(model["passable"]),
            "blocked_moves": len(model["blocked"]), "deadly_positions": len(model["deadly"])}


_NAV_REFUSALS = ("KnownNoOpActionError", "KnownDeathActionError", "RepeatedActionInStateError",
                 "StaleStateActionError", "TerminalStateActionError")


def run_navigation(target, get_state, act, execute=True, max_steps=40, adjacent=None):
    """Plan to ``target`` and, with ``execute``, walk there one verified step at a time.

    ``get_state()`` returns (current_frame, transitions); ``act(key)`` performs one action and
    returns its result dict.  Returns a dict with ``status`` (reached, planned, no_path,
    no_moves_observed, piece_not_found, diverged, refused, level_completed, game_over,
    max_steps), ``steps`` (keys executed), ``planned`` (keys in the plan) and ``at``.
    """
    frame, transitions = get_state()
    grid = _nav_grid(frame)
    level = _nav_level(frame)
    model = learn_controls(transitions, level)
    if model is None or grid is None:
        return {"status": "no_moves_observed", "steps": [], "planned": 0, "at": None,
                "note": "press UP/DOWN/LEFT/RIGHT at least once on this level first"}
    start = locate_piece(grid, model)
    if start is None:
        return {"status": "piece_not_found", "steps": [], "planned": 0, "at": None}
    modes = [adjacent] if adjacent is not None else [False, True]
    path = None
    used_adjacent = False
    for mode in modes:
        path = plan_path(grid, model, start, target, adjacent=mode)
        if path is not None:
            used_adjacent = mode
            break
    controls = {k: list(v) for k, v in sorted(model["controls"].items())}
    if path is None:
        return {"status": "no_path", "steps": [], "planned": 0, "at": list(start),
                "controls": controls, "inferred": model["inferred"]}
    report = {"status": "planned", "steps": [], "planned": len(path), "path": path,
              "at": list(start), "controls": controls, "inferred": model["inferred"],
              "adjacent": used_adjacent}
    if not execute:
        return report
    if not path:
        report["status"] = "reached"
        return report
    here = start
    for key in path[:max_steps]:
        expected = (here[0] + model["controls"][key][0], here[1] + model["controls"][key][1])
        try:
            result = act(key) or {}
        except BaseException as exc:  # the harness refusals derive from BaseException
            if type(exc).__name__ not in _NAV_REFUSALS:
                raise
            report.update(status="refused", note=f"{type(exc).__name__}: {exc}")
            return report
        report["steps"].append(key)
        for flag in _NAV_STOP_FLAGS:
            if result.get(flag):
                report["status"] = "level_completed" if flag in ("level_completed", "run_complete", "done") \
                    else "game_over"
                return report
        frame, _ = get_state()
        now = locate_piece(_nav_grid(frame), dict(model, last_origin=expected))
        report["at"] = list(now) if now else None
        if now != expected:
            report.update(status="diverged",
                          note=f"{key} was predicted to reach {list(expected)}; replan from here")
            return report
        here = now
    report["status"] = "reached" if len(path) <= max_steps else "max_steps"
    return report
