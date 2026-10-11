"""Per-level memory derived from the action history (pure, sandbox-injectable).

The harness keeps every action and frame of a game in ``history``; this module turns that
into something the model can read in one call: for each level it has completed, the
action sequence of the attempt that completed it, how many attempts (resets) it took, and
how many actions each attempt spent.  It uses only ``entry.action``, ``entry.frame.level``
and ``entry.result`` so it works on both the host-side ``HistoryEntry`` dataclass and the
sandbox's ``HistoryEntryView``.

This file is injected verbatim into the sandbox bootstrap (see python_tool_sandbox.py), so
it must not import anything outside the standard library.
"""
from __future__ import annotations

RESET_NAMES = {"RESET"}


def _level_of(entry) -> int:
    frame = getattr(entry, "frame", None)
    try:
        return int(getattr(frame, "level", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _action_display(entry) -> str:
    return str(getattr(entry, "action", "") or "").strip()


def compute_solved_levels(history, max_actions_kept: int = 60) -> list:
    """Summarise completed levels from a chronological history.

    ``history[0]`` is the seeded initial frame (empty action).  For every later entry the
    level *before* the action is the previous entry's frame level, and a level is completed
    when the frame level increases (or ``result['level_completed']`` is true).

    Returns a list ordered by level, each item a dict with keys
    ``level``, ``winning_actions`` (the last attempt, RESET excluded, at most
    ``max_actions_kept`` entries kept from the end), ``n_actions`` (actions in that attempt),
    ``attempts`` (1 + number of RESETs on that level), ``total_actions`` (all actions spent
    on that level including failed attempts).
    """
    entries = list(history or [])
    if not entries:
        return []
    per_level: dict = {}
    prev_level = _level_of(entries[0]) or 1
    for entry in entries[1:]:
        action = _action_display(entry)
        if not action:
            prev_level = _level_of(entry) or prev_level
            continue
        before = prev_level or 1
        after = _level_of(entry) or before
        result = getattr(entry, "result", None)
        result = result if isinstance(result, dict) else {}
        info = per_level.setdefault(
            before,
            {"level": before, "attempts": 1, "total_actions": 0, "current": [], "winning_actions": None, "n_actions": 0},
        )
        is_reset = action.upper().split("(")[0] in RESET_NAMES
        if is_reset:
            if info["current"]:
                info["attempts"] += 1
            info["current"] = []
            info["total_actions"] += 1
        else:
            info["current"].append(action)
            info["total_actions"] += 1
        completed = after > before or bool(result.get("level_completed"))
        if completed and not is_reset:
            info["winning_actions"] = list(info["current"])
            info["n_actions"] = len(info["current"])
            info["current"] = []
        prev_level = after if after >= before else before
    out = []
    for level in sorted(per_level):
        info = per_level[level]
        if info["winning_actions"] is None:
            continue
        actions = info["winning_actions"]
        kept = actions[-max_actions_kept:] if max_actions_kept and len(actions) > max_actions_kept else actions
        out.append(
            {
                "level": level,
                "winning_actions": kept,
                "n_actions": info["n_actions"],
                "attempts": info["attempts"],
                "total_actions": info["total_actions"],
                "truncated": len(kept) != len(actions),
            }
        )
    return out


def format_solved_levels(summary: list, max_per_level: int = 30) -> str:
    """One compact line per level for prompts: 'L1: 12 actions in 1 attempt: UP, UP, LEFT, ...'."""
    lines = []
    for item in summary:
        actions = item.get("winning_actions") or []
        shown = actions[-max_per_level:]
        prefix = "..., " if len(shown) < len(actions) else ""
        lines.append(
            f"L{item['level']}: {item['n_actions']} actions in {item['attempts']} attempt(s) "
            f"({item['total_actions']} spent): {prefix}{', '.join(shown)}"
        )
    return "\n".join(lines)
